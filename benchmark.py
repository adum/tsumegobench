#!/usr/bin/env python3
"""Run Tsumego Bench with a supported non-interactive model CLI."""

from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import math
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
RUNS_ROOT = PROJECT_ROOT / "runs"
DEFAULT_PROBLEM_COUNT = 10
MINIMUM_PROBLEM_COUNT = 5
MAXIMUM_PROBLEM_COUNT = 50
DEFAULT_RUN_TIMEOUT_SECONDS = 12 * 60 * 60
DEFAULT_MAX_HARNESS_ATTEMPTS = 5
DEFAULT_RETRY_BASE_DELAY_SECONDS = 15
DEFAULT_RETRY_MAX_DELAY_SECONDS = 120
DEFAULT_DUPLICATE_QUERIES_PER_PROBLEM = 5
MINIMUM_CLAUDE_VERSION = (2, 1, 169)
MINIMUM_OPENCODE_VERSION = (1, 1, 1)
DIFFICULTY_BANDS = (
    "20-30 kyu",
    "10-19 kyu",
    "5-9 kyu",
    "1-4 kyu",
    "about 1 dan",
)
MINIMUM_NODE_MAJOR = 22
_TYPESCRIPT_NODE: str | None = None
REVIEW_STORE_NAME = "reviews.json"
TERMINAL_RUN_STATUSES = {"completed", "harness_failed", "evaluation_failed"}


def expected_output_names(count: int) -> list[str]:
    return [f"problem-{index:02d}.sgf" for index in range(1, count + 1)]


def difficulty_targets(count: int) -> list[str]:
    return [
        DIFFICULTY_BANDS[
            min(len(DIFFICULTY_BANDS) - 1, index * len(DIFFICULTY_BANDS) // count)
        ]
        for index in range(count)
    ]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(file: Path) -> str:
    digest = hashlib.sha256()
    with file.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:48] or "model"


def git_commit() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def write_json(file: Path, value: Any) -> None:
    file.parent.mkdir(parents=True, exist_ok=True)
    temporary = file.with_suffix(f"{file.suffix}.tmp")
    temporary.write_text(f"{json.dumps(value, indent=2, ensure_ascii=False)}\n", encoding="utf-8")
    temporary.replace(file)


def captured_text(value: str | bytes | None) -> str:
    """Normalize subprocess output, including TimeoutExpired's byte payloads."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def format_timeout(seconds: int) -> str:
    if seconds % 3600 == 0:
        hours = seconds // 3600
        return f"{hours} {'hour' if hours == 1 else 'hours'} ({seconds:,} seconds)"
    if seconds % 60 == 0:
        minutes = seconds // 60
        return f"{minutes} {'minute' if minutes == 1 else 'minutes'} ({seconds:,} seconds)"
    return f"{seconds:,} {'second' if seconds == 1 else 'seconds'}"


def format_elapsed(seconds: float) -> str:
    seconds = max(0, seconds)
    if seconds < 60:
        rounded = round(seconds, 1)
        value = f"{rounded:.1f}".rstrip("0").rstrip(".")
        return f"{value} {'second' if rounded == 1 else 'seconds'}"
    total_seconds = int(round(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, remaining_seconds = divmod(remainder, 60)
    parts = []
    if hours:
        parts.append(f"{hours} {'hour' if hours == 1 else 'hours'}")
    if minutes:
        parts.append(f"{minutes} {'minute' if minutes == 1 else 'minutes'}")
    if remaining_seconds:
        parts.append(
            f"{remaining_seconds} {'second' if remaining_seconds == 1 else 'seconds'}"
        )
    return " ".join(parts) or "0 seconds"


def retry_delay_seconds(completed_attempt: int, base_delay: int, maximum_delay: int) -> int:
    return min(maximum_delay, base_delay * (2 ** max(0, completed_attempt - 1)))


def retry_schedule(max_attempts: int, base_delay: int, maximum_delay: int) -> list[int]:
    return [
        retry_delay_seconds(attempt, base_delay, maximum_delay)
        for attempt in range(1, max_attempts)
    ]


def read_json(file: Path) -> dict[str, Any]:
    return json.loads(file.read_text(encoding="utf-8"))


def review_store_path(run_dir: Path) -> Path:
    return run_dir / "evaluation" / REVIEW_STORE_NAME


def empty_review_store(run_id: str) -> dict[str, Any]:
    return {
        "$schema": "../../../schemas/human-reviews.schema.json",
        "schemaVersion": 1,
        "runId": run_id,
        "updatedAt": None,
        "reviews": [],
    }


def read_review_store(run_dir: Path, run_id: str) -> dict[str, Any]:
    path = review_store_path(run_dir)
    if not path.exists():
        return empty_review_store(run_id)
    store = read_json(path)
    if store.get("runId") != run_id or not isinstance(store.get("reviews"), list):
        raise ValueError(f"Invalid human review store under {path}")
    return store


def reviewable_run(value: str | None = None, runs_root: Path | None = None) -> Path:
    root = (runs_root or RUNS_ROOT).resolve()
    if value:
        supplied = Path(value)
        if supplied.is_absolute():
            candidate = supplied.resolve()
        elif supplied.parts and supplied.parts[0] == "runs":
            candidate = (PROJECT_ROOT / supplied).resolve()
        else:
            candidate = (root / supplied).resolve()
        if candidate.parent != root:
            raise ValueError("The review run must be a direct child of the runs directory.")
        candidates = [candidate]
    else:
        candidates = [entry.resolve() for entry in root.iterdir() if entry.is_dir()] if root.exists() else []

    completed: list[tuple[str, Path]] = []
    for candidate in candidates:
        manifest_path = candidate / "run.json"
        automated_path = candidate / "evaluation" / "automated.json"
        if not manifest_path.exists() or not automated_path.exists():
            continue
        try:
            manifest = read_json(manifest_path)
        except (OSError, json.JSONDecodeError):
            continue
        if manifest.get("status") not in TERMINAL_RUN_STATUSES or not manifest.get("completedAt"):
            continue
        completed.append((str(manifest["completedAt"]), candidate))

    if not completed:
        if value:
            raise ValueError(f"Run {value!r} has not completed evaluation and cannot be reviewed yet.")
        raise ValueError("No completed benchmark run is available for human review.")
    completed.sort(key=lambda item: item[0], reverse=True)
    return completed[0][1]


def review_problem_files(run_dir: Path) -> list[str]:
    automated = read_json(run_dir / "evaluation" / "automated.json")
    problems = automated.get("problems")
    if not isinstance(problems, list):
        raise ValueError("The automated evaluation has no problem list.")
    files = [problem.get("file") for problem in problems if isinstance(problem, dict)]
    if not files or any(not isinstance(file, str) for file in files):
        raise ValueError("The automated evaluation contains an invalid problem list.")
    return files


def normalize_review(review: Any, expected_files: list[str], now: str | None = None) -> dict[str, Any]:
    if not isinstance(review, dict):
        raise ValueError("Review payload must be an object.")
    review_id = review.get("reviewId")
    reviewer_name = review.get("reviewerName")
    if not isinstance(review_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{8,80}", review_id):
        raise ValueError("reviewId must be 8-80 letters, numbers, underscores, or hyphens.")
    if not isinstance(reviewer_name, str) or not reviewer_name.strip() or len(reviewer_name.strip()) > 100:
        raise ValueError("Reviewer name must be between 1 and 100 characters.")
    problems = review.get("problems")
    if not isinstance(problems, list) or len(problems) != len(expected_files):
        raise ValueError("The review must contain exactly one record for every generated problem.")

    normalized_problems: list[dict[str, Any]] = []
    seen: set[str] = set()
    timestamp = now or utc_now()
    for problem in problems:
        if not isinstance(problem, dict) or problem.get("file") not in expected_files:
            raise ValueError("The review contains an unknown problem file.")
        file = str(problem["file"])
        if file in seen:
            raise ValueError(f"The review contains {file} more than once.")
        seen.add(file)
        valid = problem.get("valid")
        realistic = problem.get("realistic")
        duplicate = problem.get("duplicate")
        well_pathed = problem.get("wellPathed")
        difficulty = problem.get("estimatedDifficulty")
        quality = problem.get("quality")
        reviewed_at = problem.get("reviewedAt")
        if valid is not None and not isinstance(valid, bool):
            raise ValueError(f"Invalid validity value for {file}.")
        if realistic is not None and not isinstance(realistic, bool):
            raise ValueError(f"Invalid realism value for {file}.")
        if duplicate is not None and not isinstance(duplicate, bool):
            raise ValueError(f"Invalid duplicate value for {file}.")
        if well_pathed is not None and not isinstance(well_pathed, bool):
            raise ValueError(f"Invalid well-pathed value for {file}.")
        if quality is not None and (
            isinstance(quality, bool) or not isinstance(quality, int) or not 1 <= quality <= 5
        ):
            raise ValueError(f"Quality for {file} must be between 1 and 5.")
        if difficulty is not None and difficulty not in DIFFICULTY_BANDS:
            raise ValueError(f"Invalid estimated difficulty for {file}.")
        if valid is not True:
            difficulty = None

        complete = any(
            (
                isinstance(valid, bool),
                isinstance(realistic, bool),
                isinstance(duplicate, bool),
                isinstance(well_pathed, bool),
                difficulty in DIFFICULTY_BANDS,
                quality is not None,
            )
        )
        status = "completed" if complete else "pending"
        if complete:
            reviewed_at = reviewed_at if isinstance(reviewed_at, str) and reviewed_at else timestamp
        else:
            reviewed_at = None

        normalized_problems.append(
            {
                "file": file,
                "status": status,
                "valid": valid,
                "realistic": realistic,
                "duplicate": duplicate,
                "wellPathed": well_pathed,
                "estimatedDifficulty": difficulty,
                "quality": quality,
                "reviewedAt": reviewed_at,
            }
        )

    if seen != set(expected_files):
        raise ValueError("The review is missing one or more generated problems.")
    normalized_problems.sort(key=lambda problem: expected_files.index(problem["file"]))
    created_at = review.get("createdAt")
    return {
        "reviewId": review_id,
        "reviewerName": reviewer_name.strip(),
        "createdAt": created_at if isinstance(created_at, str) and created_at else timestamp,
        "updatedAt": timestamp,
        "problems": normalized_problems,
    }


def update_review_results(run_dir: Path, store: dict[str, Any]) -> None:
    results_path = run_dir / "evaluation" / "results.json"
    if not results_path.exists():
        return
    results = read_json(results_path)
    reviews = store.get("reviews", [])
    summaries = []
    for review in reviews:
        completed = [problem for problem in review["problems"] if problem["status"] == "completed"]
        summaries.append(
            {
                "reviewId": review["reviewId"],
                "reviewerName": review["reviewerName"],
                "updatedAt": review["updatedAt"],
                "completed": len(completed),
                "total": len(review["problems"]),
            }
        )
    results["humanReviews"] = {
        "reviewCount": len(reviews),
        "completedProblemReviews": sum(summary["completed"] for summary in summaries),
        "reviewers": summaries,
    }
    for problem in results.get("problems", []):
        file = problem.get("file")
        problem["reviews"] = [
            {
                "reviewId": review["reviewId"],
                "reviewerName": review["reviewerName"],
                **next(record for record in review["problems"] if record["file"] == file),
            }
            for review in reviews
            if any(record["file"] == file and record["status"] == "completed" for record in review["problems"])
        ]
    write_json(results_path, results)


def save_review(run_dir: Path, run_id: str, review: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    timestamp = utc_now()
    expected_files = review_problem_files(run_dir)
    normalized = normalize_review(review, expected_files, timestamp)
    store = read_review_store(run_dir, run_id)
    existing = next(
        (record for record in store["reviews"] if record.get("reviewId") == normalized["reviewId"]),
        None,
    )
    if existing:
        normalized["createdAt"] = existing.get("createdAt") or normalized["createdAt"]
        store["reviews"] = [
            normalized if record.get("reviewId") == normalized["reviewId"] else record
            for record in store["reviews"]
        ]
    else:
        store["reviews"].append(normalized)
    store["updatedAt"] = timestamp
    write_json(review_store_path(run_dir), store)
    update_review_results(run_dir, store)
    return store, normalized


def command_name(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    if os.name == "nt" and not name.lower().endswith((".exe", ".cmd", ".bat")):
        found = shutil.which(f"{name}.cmd")
        if found:
            return found
    return name


def is_wsl() -> bool:
    return sys.platform.startswith("linux") and bool(
        os.environ.get("WSL_INTEROP") or os.environ.get("WSL_DISTRO_NAME")
    )


def node_major(executable: str) -> int | None:
    try:
        result = subprocess.run(
            [executable, "--version"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    match = re.search(r"v?(\d+)", result.stdout or result.stderr)
    return int(match.group(1)) if match else None


def wsl_path(value: str, flag: str) -> str | None:
    try:
        result = subprocess.run(
            ["wslpath", flag, value],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    converted = result.stdout.strip()
    return converted if result.returncode == 0 and converted else None


def windows_home_from_wsl() -> Path | None:
    try:
        result = subprocess.run(
            ["cmd.exe", "/d", "/c", "echo", "%USERPROFILE%"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    windows_home = result.stdout.strip()
    converted = wsl_path(windows_home, "-u") if windows_home else None
    return Path(converted) if converted else None


def dependency_platform() -> str:
    packages = PROJECT_ROOT / "node_modules" / "@esbuild"
    native = "windows" if os.name == "nt" else "linux" if sys.platform.startswith("linux") else "darwin"
    prefixes = {
        "windows": "win32-",
        "linux": "linux-",
        "darwin": "darwin-",
    }
    if packages.exists() and any(packages.glob(f"{prefixes[native]}*")):
        return native
    if is_wsl() and packages.exists() and any(packages.glob("win32-*")):
        return "windows"
    return native


def windows_node_candidates() -> list[str]:
    candidates: list[str] = []
    if os.name == "nt":
        home = Path.home()
        candidates.extend(
            [
                str(
                    home
                    / ".cache"
                    / "codex-runtimes"
                    / "codex-primary-runtime"
                    / "dependencies"
                    / "node"
                    / "bin"
                    / "node.exe"
                ),
                command_name("node"),
            ]
        )
        return candidates

    if not is_wsl():
        return candidates
    home = windows_home_from_wsl()
    if home:
        candidates.append(
            str(
                home
                / ".cache"
                / "codex-runtimes"
                / "codex-primary-runtime"
                / "dependencies"
                / "node"
                / "bin"
                / "node.exe"
            )
        )
    found = shutil.which("node.exe")
    if found:
        candidates.append(found)
    try:
        result = subprocess.run(
            ["where.exe", "node.exe"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        for line in result.stdout.splitlines():
            converted = wsl_path(line.strip(), "-u")
            if converted:
                candidates.append(converted)
    except (OSError, subprocess.TimeoutExpired):
        pass
    return candidates


def typescript_node() -> str:
    global _TYPESCRIPT_NODE
    if _TYPESCRIPT_NODE:
        return _TYPESCRIPT_NODE

    target = dependency_platform()
    requested = os.environ.get("TSUMEGO_NODE")
    candidates = [requested] if requested else []
    if target == "windows":
        candidates.extend(windows_node_candidates())
    else:
        found = shutil.which("node")
        if found:
            candidates.append(found)

    checked: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in checked:
            continue
        checked.add(candidate)
        if target == "windows" and not candidate.lower().endswith(".exe"):
            continue
        if target != "windows" and candidate.lower().endswith(".exe"):
            continue
        major = node_major(candidate)
        if major is not None and major >= MINIMUM_NODE_MAJOR:
            _TYPESCRIPT_NODE = candidate
            return candidate

    raise RuntimeError(
        f"Could not find Node.js {MINIMUM_NODE_MAJOR}+ for the {target} dependencies in node_modules. "
        "Run npm ci in this environment or set TSUMEGO_NODE to a compatible Node executable."
    )


def runtime_path(path: Path, executable: str) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        pass
    if is_wsl() and executable.lower().endswith(".exe"):
        converted = wsl_path(str(resolved), "-w")
        if converted:
            return converted
    return str(resolved)


def run_typescript(script: str, arguments: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        executable = typescript_node()
    except RuntimeError as error:
        return subprocess.CompletedProcess(["node", script], 127, "", f"{error}\n")
    return subprocess.run(
        [executable, "--import", "tsx", script, *arguments],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def duplicate_query_limit(args: argparse.Namespace) -> int:
    configured = getattr(args, "duplicate_query_limit", None)
    return configured if configured is not None else args.count * DEFAULT_DUPLICATE_QUERIES_PER_PROBLEM


def start_originality_broker(run_dir: Path, query_limit: int) -> dict[str, Any]:
    executable = typescript_node()
    trusted_directory = tempfile.TemporaryDirectory(prefix="tsumego-originality-audit-")
    trusted_path = Path(trusted_directory.name)
    stdout_path = run_dir / "logs" / "originality-broker-stdout.txt"
    stderr_path = run_dir / "logs" / "originality-broker-stderr.txt"
    stdout_handle = stdout_path.open("w", encoding="utf-8")
    stderr_handle = stderr_path.open("w", encoding="utf-8")
    command = [
        executable,
        "--import",
        "tsx",
        "scripts/originality-broker.ts",
        "--run-dir",
        runtime_path(run_dir, executable),
        "--query-limit",
        str(query_limit),
        "--audit-dir",
        runtime_path(trusted_path, executable),
    ]
    try:
        process = subprocess.Popen(
            command,
            cwd=PROJECT_ROOT,
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        stdout_handle.close()
        stderr_handle.close()
        trusted_directory.cleanup()
        raise

    ready_path = run_dir / "originality" / "ready.json"
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if ready_path.exists():
            return {
                "process": process,
                "stdoutHandle": stdout_handle,
                "stderrHandle": stderr_handle,
                "trustedDirectory": trusted_directory,
                "trustedPath": trusted_path,
            }
        exit_code = process.poll()
        if exit_code is not None:
            stdout_handle.close()
            stderr_handle.close()
            trusted_directory.cleanup()
            detail = stderr_path.read_text(encoding="utf-8").strip()
            raise RuntimeError(
                f"The originality broker exited with status {exit_code}"
                f"{f': {detail}' if detail else '.'}"
            )
        time.sleep(0.1)

    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
    stdout_handle.close()
    stderr_handle.close()
    trusted_directory.cleanup()
    raise RuntimeError("The originality broker did not become ready within 30 seconds.")


def stop_originality_broker(run_dir: Path, broker: dict[str, Any]) -> int | None:
    process = broker["process"]
    (run_dir / "originality" / "stop").write_text("stop\n", encoding="utf-8")
    try:
        exit_code = process.wait(timeout=60)
    except subprocess.TimeoutExpired:
        process.terminate()
        try:
            exit_code = process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            exit_code = process.wait(timeout=5)
    finally:
        broker["stdoutHandle"].close()
        broker["stderrHandle"].close()
        trusted_path = broker["trustedPath"]
        trusted_summary = trusted_path / "summary.json"
        trusted_audit = trusted_path / "audit.jsonl"
        if trusted_summary.exists():
            shutil.copy2(trusted_summary, run_dir / "originality" / "summary.json")
        if trusted_audit.exists():
            shutil.copy2(trusted_audit, run_dir / "logs" / "originality-tool.jsonl")
        broker["trustedDirectory"].cleanup()
        (run_dir / "originality" / "stop").unlink(missing_ok=True)
        (run_dir / "originality" / "ready.json").unlink(missing_ok=True)
    return exit_code


def portable_command(command: list[str], run_dir: Path) -> list[str]:
    recorded: list[str] = []
    for index, argument in enumerate(command):
        value = argument.replace(str(run_dir), "<run-dir>").replace(
            str(PROJECT_ROOT), "<project-root>"
        )
        if index == 0 and Path(value).is_absolute():
            value = Path(value).name
        recorded.append(value)
    return recorded


def opencode_model_parts(model: str) -> tuple[str, str]:
    provider, separator, model_name = model.partition("/")
    if (
        not separator
        or not provider
        or not model_name
        or any(character.isspace() for character in model)
    ):
        raise ValueError(
            "--model for OpenCode must use the exact provider/model format, "
            "such as openai/gpt-5.2."
        )
    return provider.lower(), model_name


def harness_provider(harness: str, model: str) -> str:
    if harness == "opencode":
        return opencode_model_parts(model)[0]
    return {
        "codex": "openai",
        "claude": "anthropic",
        "grok": "xai",
    }[harness]


def harness_manifest_name(harness: str) -> str:
    return {
        "codex": "codex-cli",
        "claude": "claude-cli",
        "grok": "grok-cli",
        "opencode": "opencode-cli",
    }[harness]


def harness_label(harness: str) -> str:
    return {
        "codex": "Codex CLI",
        "claude": "Claude CLI",
        "grok": "Grok CLI",
        "opencode": "OpenCode CLI",
    }[harness]


def unique_run_id(model: str, requested: str | None, harness: str = "codex") -> str:
    provider = harness_provider(harness, model)
    model_name = opencode_model_parts(model)[1] if harness == "opencode" else model
    if requested:
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{2,100}", requested):
            raise ValueError(
                "--run-id must be 3–101 characters using letters, numbers, dots, underscores, or hyphens."
            )
        if (RUNS_ROOT / requested).exists():
            raise ValueError(f"Run directory already exists: runs/{requested}")
        return requested

    prefix = (
        f"{datetime.now(timezone.utc):%Y-%m-%dT%H%M%SZ}-"
        f"{provider}-{slugify(model_name)}-{harness}"
    )
    candidate = prefix
    suffix = 2
    while (RUNS_ROOT / candidate).exists():
        candidate = f"{prefix}-{suffix:02d}"
        suffix += 1
    return candidate


def opencode_config() -> dict[str, Any]:
    return {
        "$schema": "https://opencode.ai/config.json",
        "share": "disabled",
        "autoupdate": False,
        "formatter": False,
        "instructions": [],
        "plugin": [],
        "mcp": {},
        "permission": {
            "*": "deny",
            "read": "allow",
            "edit": "allow",
            "glob": "allow",
            "grep": "allow",
            "list": "allow",
        },
    }


def copy_inputs(
    run_dir: Path,
    problem_count: int,
    harness: str = "codex",
    duplicate_tool_enabled: bool = True,
    query_limit: int | None = None,
) -> list[dict[str, str]]:
    inputs = run_dir / "inputs"
    examples = inputs / "examples"
    examples.mkdir(parents=True)

    copies = {
        PROJECT_ROOT / "docs" / "model-prompt.md": inputs / "model-prompt.md",
        PROJECT_ROOT / "docs" / "authoring-guide.md": inputs / "authoring-guide.md",
        PROJECT_ROOT / "docs" / "benchmark-spec.md": inputs / "benchmark-spec.md",
        PROJECT_ROOT / "docs" / "originality-tool.md": inputs / "originality-tool.md",
        PROJECT_ROOT / "examples" / "manifest.json": inputs / "reference-manifest.json",
        PROJECT_ROOT / "schemas" / "originality-request.schema.json": inputs
        / "originality-request.schema.json",
        PROJECT_ROOT / "schemas" / "originality-response.schema.json": inputs
        / "originality-response.schema.json",
        PROJECT_ROOT / "schemas" / "originality-summary.schema.json": inputs
        / "originality-summary.schema.json",
    }
    for source, destination in copies.items():
        shutil.copy2(source, destination)
    for source in sorted((PROJECT_ROOT / "examples" / "canonical-life-and-death").glob("*.sgf")):
        shutil.copy2(source, examples / source.name)

    output_names = expected_output_names(problem_count)
    target_lines = "\n".join(
        f"   - `outputs/{name}` - target difficulty: {target}"
        for name, target in zip(output_names, difficulty_targets(problem_count), strict=True)
    )
    effective_query_limit = query_limit or problem_count * DEFAULT_DUPLICATE_QUERIES_PER_PROBLEM
    if duplicate_tool_enabled:
        originality_steps = f"""6. Read `inputs/originality-tool.md`. The originality query budget is {effective_query_limit} requests ({DEFAULT_DUPLICATE_QUERIES_PER_PROBLEM} per requested problem). Built-in common setups can return `duplicate` from the initial stones alone; otherwise, a request without at least one `C[RIGHT]` endpoint returns `invalid`. Either outcome still consumes one query.
7. Use the originality tool while authoring, then query every exact final output again after all {problem_count} files exist. Only a final `clear` result is acceptable. Do not edit a file after its final clear result.
8. Do not access the web or any other network service. The file-based originality tool is the only permitted external lookup.
9. Do not run the benchmark evaluator yourself. Finish all {problem_count} files, verify them, then exit."""
    else:
        originality_steps = f"""6. This is a local-only diagnostic run, so the live originality tool is disabled and the run cannot satisfy the remote originality gate. Do not create originality requests or wait for results.
7. Do not access the web or any network service.
8. Do not run the benchmark evaluator yourself. Finish all {problem_count} files, verify them locally as far as you can, then exit."""
    task = f"""# Tsumego Bench execution task

This is a controlled benchmark run. Work only inside the current run directory.

1. Read `inputs/model-prompt.md` in full and follow it exactly.
2. Use `inputs/authoring-guide.md`, `inputs/reference-manifest.json`, and all SGFs in `inputs/examples/` as the supplied reference material.
3. Create exactly {problem_count} final candidate SGF files using these names and target difficulties:
{target_lines}
4. Each output file must contain only one complete SGF collection—no Markdown fences or explanatory prose.
5. Do not modify anything under `inputs/`, `logs/`, `evaluation/`, or `originality/results/`; do not modify `originality/summary.json` or `run.json`. Under `originality/`, you may only create new request files in `originality/requests/`.
{originality_steps}

Do not ask the operator questions and do not wait for repair feedback.
"""
    (inputs / "task.md").write_text(task, encoding="utf-8")
    if harness == "opencode":
        config_dir = inputs / "opencode-config"
        config_dir.mkdir()
        (config_dir / "opencode.json").write_text(
            json.dumps(opencode_config(), indent=2) + "\n",
            encoding="utf-8",
        )

    records: list[dict[str, str]] = []
    for file in sorted(path for path in inputs.rglob("*") if path.is_file()):
        records.append(
            {
                "path": file.relative_to(run_dir).as_posix(),
                "sha256": sha256_file(file),
            }
        )
    return records


def cli_version(executable: str) -> str | None:
    try:
        result = subprocess.run(
            [executable, "--version"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        if result.returncode:
            return None
        value = (result.stdout or result.stderr).strip()
        return value or None
    except (OSError, subprocess.TimeoutExpired):
        return None


def claude_version_error(version: str) -> str | None:
    match = re.search(r"(?:^|\D)(\d+)\.(\d+)\.(\d+)(?:\D|$)", version)
    if not match:
        return f"Could not determine the Claude CLI version from {version!r}."
    installed = tuple(int(part) for part in match.groups())
    if installed < MINIMUM_CLAUDE_VERSION:
        required = ".".join(str(part) for part in MINIMUM_CLAUDE_VERSION)
        return (
            f"Claude CLI {required} or newer is required for the benchmark's isolated mode; "
            f"found {'.'.join(str(part) for part in installed)}."
        )
    return None


def opencode_version_error(version: str) -> str | None:
    match = re.search(r"(?:^|\D)(\d+)\.(\d+)\.(\d+)(?:\D|$)", version)
    if not match:
        return f"Could not determine the OpenCode CLI version from {version!r}."
    installed = tuple(int(part) for part in match.groups())
    if installed < MINIMUM_OPENCODE_VERSION:
        required = ".".join(str(part) for part in MINIMUM_OPENCODE_VERSION)
        return (
            f"OpenCode CLI {required} or newer is required for the benchmark's "
            f"isolated permission mode; found {'.'.join(str(part) for part in installed)}."
        )
    return None


def event_message(value: Any) -> str | None:
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return value.strip() or None
        return event_message(decoded)
    if isinstance(value, dict):
        for key in ("error", "message", "data", "cause"):
            nested_value = value.get(key)
            if nested_value is None:
                continue
            nested = event_message(nested_value)
            if nested:
                return nested
    return None


def parse_codex_events(stdout: str) -> dict[str, Any]:
    thread_id: str | None = None
    usage: dict[str, Any] | None = None
    parse_errors = 0
    event_count = 0
    failure_message: str | None = None

    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            parse_errors += 1
            continue
        event_count += 1
        if event.get("type") == "thread.started":
            thread_id = event.get("thread_id") or event.get("threadId")
        if event.get("type") == "turn.completed":
            usage = event.get("usage")
        if event.get("type") in {"error", "turn.failed"}:
            failure_message = event_message(event) or failure_message
    return {
        "threadId": thread_id,
        "usage": usage,
        "eventCount": event_count,
        "unparsedLineCount": parse_errors,
        "failureMessage": failure_message,
    }


def parse_claude_events(stdout: str) -> dict[str, Any]:
    session_id: str | None = None
    usage: dict[str, Any] | None = None
    parse_errors = 0
    event_count = 0
    failure_message: str | None = None
    final_message: str | None = None

    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            parse_errors += 1
            continue
        event_count += 1
        session_id = event.get("session_id") or event.get("sessionId") or session_id
        if event.get("type") == "result":
            result = event.get("result")
            if isinstance(result, str):
                final_message = result
            usage_fields = {
                key: event[key]
                for key in (
                    "usage",
                    "modelUsage",
                    "total_cost_usd",
                    "duration_api_ms",
                    "num_turns",
                )
                if event.get(key) is not None
            }
            usage = usage_fields or None
            if event.get("is_error") or event.get("subtype") not in {None, "success"}:
                failure_message = event_message(event) or final_message or failure_message
        elif event.get("type") == "error":
            failure_message = event_message(event) or failure_message

    return {
        "threadId": session_id,
        "usage": usage,
        "eventCount": event_count,
        "unparsedLineCount": parse_errors,
        "failureMessage": failure_message,
        "finalMessage": final_message,
    }


def parse_grok_events(stdout: str) -> dict[str, Any]:
    session_id: str | None = None
    usage: dict[str, Any] | None = None
    parse_errors = 0
    event_count = 0
    failure_message: str | None = None
    current_message_parts: list[str] = []
    final_message: str | None = None

    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            parse_errors += 1
            continue
        event_count += 1
        event_type = event.get("type")
        if event_type == "text" and isinstance(event.get("data"), str):
            current_message_parts.append(event["data"])
        if event_type == "usage" and current_message_parts:
            final_message = "".join(current_message_parts).strip() or final_message
            current_message_parts = []
        if event_type in {"end", "error"}:
            session_id = event.get("sessionId") or event.get("session_id") or session_id
            usage_fields = {
                key: event[key]
                for key in (
                    "usage",
                    "modelUsage",
                    "total_cost_usd",
                    "total_cost_usd_ticks",
                    "cost_is_partial",
                    "usage_is_incomplete",
                    "num_turns",
                    "requestId",
                )
                if event.get(key) is not None
            }
            usage = usage_fields or usage
        if event_type == "error":
            failure_message = event_message(event) or failure_message

    if current_message_parts:
        final_message = "".join(current_message_parts).strip() or final_message
    return {
        "threadId": session_id,
        "usage": usage,
        "eventCount": event_count,
        "unparsedLineCount": parse_errors,
        "failureMessage": failure_message,
        "finalMessage": final_message,
    }


def parse_opencode_events(stdout: str) -> dict[str, Any]:
    session_id: str | None = None
    parse_errors = 0
    event_count = 0
    failure_message: str | None = None
    text_by_message: dict[str, list[str]] = {}
    last_text: str | None = None
    final_message_id: str | None = None
    usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "reasoning_tokens": 0,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
        "cost_usd": 0.0,
        "steps": 0,
    }
    has_usage = False

    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            parse_errors += 1
            continue
        event_count += 1
        session_id = event.get("sessionID") or event.get("session_id") or session_id
        event_type = event.get("type")
        part = event.get("part") if isinstance(event.get("part"), dict) else {}

        if event_type == "text" and isinstance(part.get("text"), str):
            text = part["text"]
            message_id = part.get("messageID") or part.get("messageId") or ""
            text_by_message.setdefault(message_id, []).append(text)
            last_text = text.strip() or last_text

        if event_type == "step_finish":
            has_usage = True
            usage["steps"] += 1
            tokens = part.get("tokens") if isinstance(part.get("tokens"), dict) else {}
            cache = tokens.get("cache") if isinstance(tokens.get("cache"), dict) else {}
            for source, destination in (
                (tokens.get("input"), "input_tokens"),
                (tokens.get("output"), "output_tokens"),
                (tokens.get("reasoning"), "reasoning_tokens"),
                (cache.get("read"), "cache_read_tokens"),
                (cache.get("write"), "cache_write_tokens"),
            ):
                if isinstance(source, (int, float)) and not isinstance(source, bool):
                    usage[destination] += source
            cost = part.get("cost")
            if isinstance(cost, (int, float)) and not isinstance(cost, bool):
                usage["cost_usd"] += cost
            if part.get("reason") == "stop":
                final_message_id = part.get("messageID") or part.get("messageId")

        if event_type == "error":
            failure_message = event_message(event) or failure_message

    final_parts = text_by_message.get(final_message_id or "", [])
    final_message = "".join(final_parts).strip() or last_text
    if has_usage:
        usage["cost_usd"] = round(usage["cost_usd"], 12)
    return {
        "threadId": session_id,
        "usage": usage if has_usage else None,
        "eventCount": event_count,
        "unparsedLineCount": parse_errors,
        "failureMessage": failure_message,
        "finalMessage": final_message,
    }


def is_model_selection_failure(message: str | None, raw_output: str = "") -> bool:
    evidence = f"{message or ''}\n{raw_output}".lower()
    patterns = (
        "model is not supported",
        "not supported when using codex",
        "model_not_found",
        "invalid model",
        "invalid model name",
        "model does not exist",
        "model not found",
        "model is unavailable",
        "unknown model",
        "could not resolve model",
        "unsupported model",
        "does not exist or you do not have access to it",
        "you do not have access to this model",
    )
    return any(pattern in evidence for pattern in patterns)


def is_transient_harness_failure(message: str | None, raw_output: str = "") -> bool:
    evidence = f"{message or ''}\n{raw_output}".lower()
    if is_model_selection_failure(message, raw_output):
        return False
    patterns = (
        "reqwest error",
        "error sending request for url",
        "connection reset",
        "connection closed",
        "connection refused",
        "connection aborted",
        "network is unreachable",
        "network error",
        "transport error",
        "temporary failure in name resolution",
        "name or service not known",
        "dns error",
        "tls handshake",
        "unexpected eof",
        "stream error",
        "error decoding response body",
        "request timeout",
        "request timed out",
        "operation timed out",
        "deadline exceeded",
        "temporarily unavailable",
        "service unavailable",
        "bad gateway",
        "gateway timeout",
        "too many requests",
        "rate limit",
        "overloaded_error",
        "server_error",
        "internal server error",
        "upstream connect error",
    )
    retryable_status = re.search(
        r"(?:http(?: status)?|status(?: code)?|error)[^\n]{0,24}\b(?:408|425|429|500|502|503|504|521|522|523|524|529)\b",
        evidence,
    )
    return bool(retryable_status) or any(pattern in evidence for pattern in patterns)


def compact_failure(message: str | None, stdout: str, stderr: str, exit_code: int) -> str:
    candidates = [message, stderr.strip(), stdout.strip()]
    detail = next((candidate for candidate in candidates if candidate), None)
    if not detail:
        return f"Exited with status {exit_code}."
    compact = re.sub(r"\s+", " ", detail).strip()
    return compact if len(compact) <= 500 else f"{compact[:497]}..."


def run_harness_once(
    args: argparse.Namespace,
    command: list[str],
    run_dir: Path,
    task: str,
    label: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    started = time.monotonic()
    stdout = ""
    stderr = ""
    exit_code: int | None = None
    timed_out = False
    timeout_message: str | None = None
    try:
        completed = subprocess.run(
            command,
            cwd=run_dir,
            input=None if args.harness == "grok" else task,
            env=harness_environment(args, run_dir),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
        stdout = captured_text(completed.stdout)
        stderr = captured_text(completed.stderr)
        exit_code = completed.returncode
    except subprocess.TimeoutExpired as error:
        timed_out = True
        stdout = captured_text(error.stdout)
        stderr = captured_text(error.stderr)
        timeout_message = (
            f"{label} timed out after {format_timeout(max(1, math.ceil(timeout_seconds)))}."
        )
        stderr = f"{stderr.rstrip()}\n{timeout_message}\n" if stderr else f"{timeout_message}\n"
        exit_code = 124
    except OSError as error:
        stderr = f"Could not launch {label}: {error}\n"
        exit_code = 127

    return {
        "stdout": stdout,
        "stderr": stderr,
        "exitCode": exit_code,
        "timedOut": timed_out,
        "timeoutMessage": timeout_message,
        "durationSeconds": round(time.monotonic() - started, 3),
    }


def write_harness_attempt_logs(
    run_dir: Path,
    harness: str,
    attempt_number: int,
    stdout: str,
    stderr: str,
) -> tuple[Path, str, str]:
    attempt_dir = run_dir / "logs" / "attempts" / f"attempt-{attempt_number:02d}"
    attempt_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = attempt_dir / f"{harness}-events.jsonl"
    stderr_path = attempt_dir / f"{harness}-stderr.txt"
    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")
    return (
        attempt_dir,
        stdout_path.relative_to(run_dir).as_posix(),
        stderr_path.relative_to(run_dir).as_posix(),
    )


def archive_retry_outputs(run_dir: Path, attempt_dir: Path) -> str | None:
    outputs_dir = run_dir / "outputs"
    output_items = list(outputs_dir.iterdir())
    if not output_items:
        return None
    archive_dir = attempt_dir / "outputs"
    archive_dir.mkdir()
    for item in output_items:
        shutil.move(str(item), str(archive_dir / item.name))
    return archive_dir.relative_to(run_dir).as_posix()


def discard_new_run(run_dir: Path) -> None:
    target = run_dir.resolve()
    runs_root = RUNS_ROOT.resolve()
    if target.parent != runs_root or not target.is_dir():
        raise RuntimeError(f"Refusing to discard unexpected run path: {target}")
    shutil.rmtree(target)


def run_evaluator(run_dir: Path, local_only: bool) -> subprocess.CompletedProcess[str]:
    try:
        executable = typescript_node()
    except RuntimeError as error:
        result = subprocess.CompletedProcess(["node", "scripts/evaluate-run.ts"], 127, "", f"{error}\n")
        logs = run_dir / "logs"
        (logs / "evaluator-stdout.txt").write_text(result.stdout, encoding="utf-8")
        (logs / "evaluator-stderr.txt").write_text(result.stderr, encoding="utf-8")
        return result
    command = ["--run-dir", runtime_path(run_dir, executable)]
    if local_only:
        command.append("--local-only")
    result = run_typescript("scripts/evaluate-run.ts", command)
    logs = run_dir / "logs"
    (logs / "evaluator-stdout.txt").write_text(result.stdout, encoding="utf-8")
    (logs / "evaluator-stderr.txt").write_text(result.stderr, encoding="utf-8")
    return result


def build_run_index() -> subprocess.CompletedProcess[str]:
    return run_typescript("scripts/index-runs.ts", [])


def available_port(start: int = 3001, attempts: int = 100) -> int:
    for port in range(start, start + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
            candidate.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                candidate.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"Could not find an open local port between {start} and {start + attempts - 1}.")


def make_review_handler(
    run_dir: Path,
    run_id: str,
    token: str,
) -> type[http.server.BaseHTTPRequestHandler]:
    lock = threading.Lock()

    class ReviewHandler(http.server.BaseHTTPRequestHandler):
        server_version = "TsumegoReview/1.0"

        def log_message(self, format: str, *args: Any) -> None:
            return

        def end_headers(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, PUT, OPTIONS")
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def send_json(self, status: int, value: Any) -> None:
            body = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def authorized(self) -> bool:
            return self.headers.get("Authorization") == f"Bearer {token}"

        def do_OPTIONS(self) -> None:
            self.send_response(204)
            self.end_headers()

        def do_GET(self) -> None:
            if not self.authorized():
                self.send_json(401, {"error": "Unauthorized review session."})
                return
            if urllib.parse.urlparse(self.path).path != "/session":
                self.send_json(404, {"error": "Not found."})
                return
            try:
                with lock:
                    store = read_review_store(run_dir, run_id)
                    files = review_problem_files(run_dir)
                self.send_json(
                    200,
                    {
                        "runId": run_id,
                        "problemFiles": files,
                        "difficultyOptions": list(DIFFICULTY_BANDS),
                        "reviews": store["reviews"],
                    },
                )
            except (OSError, ValueError, json.JSONDecodeError) as error:
                self.send_json(500, {"error": str(error)})

        def do_PUT(self) -> None:
            if not self.authorized():
                self.send_json(401, {"error": "Unauthorized review session."})
                return
            path = urllib.parse.urlparse(self.path).path
            match = re.fullmatch(r"/reviews/([A-Za-z0-9_-]{8,80})", path)
            if not match:
                self.send_json(404, {"error": "Not found."})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 1024 * 1024:
                    raise ValueError("Review payload must be between 1 byte and 1 MB.")
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                if payload.get("reviewId") != match.group(1):
                    raise ValueError("The review ID does not match the request path.")
                with lock:
                    store, saved = save_review(run_dir, run_id, payload)
                    indexed = build_run_index()
                warning = None
                if indexed.returncode:
                    warning = indexed.stderr.strip() or "The web run index could not be refreshed."
                self.send_json(200, {"review": saved, "reviews": store["reviews"], "warning": warning})
            except (OSError, ValueError, json.JSONDecodeError) as error:
                self.send_json(400, {"error": str(error)})

    return ReviewHandler


def wait_for_review_site(url: str, process: subprocess.Popen[Any], timeout: float = 45) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status < 500:
                    return True
        except (OSError, urllib.error.URLError):
            time.sleep(0.25)
    return False


def open_review_url(url: str) -> bool:
    try:
        if os.name == "nt":
            os.startfile(url)  # type: ignore[attr-defined]
            return True
        if is_wsl():
            if shutil.which("wslview"):
                return subprocess.Popen(["wslview", url]).poll() is None
            command = [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "Start-Process -FilePath $args[0]",
                url,
            ]
            return subprocess.run(command, check=False).returncode == 0
        return webbrowser.open(url)
    except OSError:
        return False


def prepare_manifest(args: argparse.Namespace, run_id: str, run_dir: Path) -> dict[str, Any]:
    tool_enabled = not args.local_only
    query_limit = duplicate_query_limit(args)
    input_files = copy_inputs(
        run_dir,
        args.count,
        args.harness,
        duplicate_tool_enabled=tool_enabled,
        query_limit=query_limit,
    )
    output_names = expected_output_names(args.count)
    model_prompt = run_dir / "inputs" / "model-prompt.md"
    reference_manifest = run_dir / "inputs" / "reference-manifest.json"
    log_prefix = args.harness
    return {
        "$schema": "../../schemas/run.schema.json",
        "schemaVersion": 1,
        "runId": run_id,
        "status": "prepared",
        "createdAt": utc_now(),
        "completedAt": None,
        "benchmark": {
            "commitSha": git_commit(),
            "promptSha256": sha256_file(model_prompt),
            "referenceManifestSha256": sha256_file(reference_manifest),
            "inputFiles": input_files,
        },
        "model": {
            "provider": harness_provider(args.harness, args.model),
            "name": args.model,
            "reasoningEffort": args.reasoning_effort,
        },
        "harness": {
            "name": harness_manifest_name(args.harness),
            "version": None,
            "mode": "non-interactive",
            "command": [],
            "exitCode": None,
            "durationSeconds": None,
            "threadId": None,
            "usage": None,
            "eventCount": 0,
            "unparsedLineCount": 0,
            "failureMessage": None,
            "retryPolicy": {
                "maxAttempts": args.max_attempts,
                "baseDelaySeconds": args.retry_base_delay,
                "maximumDelaySeconds": args.retry_max_delay,
            },
            "attempts": [],
        },
        "condition": {
            "attempt": args.attempt,
            "problemCount": args.count,
            "toolsEnabled": True,
            "webEnabled": False,
            "networkEnabled": False,
            "duplicateToolEnabled": tool_enabled,
            "duplicateToolVersion": 1,
            "duplicateQueryLimit": query_limit,
            "remoteDuplicateEvaluation": not args.local_only,
            "notes": args.notes or "",
        },
        "artifacts": {
            "task": "inputs/task.md",
            "stdout": f"logs/{log_prefix}-events.jsonl",
            "stderr": f"logs/{log_prefix}-stderr.txt",
            "attempts": "logs/attempts",
            "originalityToolGuide": "inputs/originality-tool.md",
            "originalityToolSummary": "originality/summary.json",
            "originalityToolAudit": "logs/originality-tool.jsonl",
            "finalMessage": "logs/final-message.txt",
            "outputs": [f"outputs/{name}" for name in output_names],
            "automatedEvaluation": "evaluation/automated.json",
            "humanEvaluation": "evaluation/human.json",
            "humanReviews": "evaluation/reviews.json",
            "results": "evaluation/results.json",
        },
    }


def harness_executable(args: argparse.Namespace) -> str:
    if args.harness == "claude":
        return args.claude or os.environ.get("CLAUDE_CLI") or command_name("claude")
    if args.harness == "grok":
        return args.grok or os.environ.get("GROK_CLI") or command_name("grok")
    if args.harness == "opencode":
        return args.opencode or os.environ.get("OPENCODE_CLI") or command_name("opencode")
    return args.codex or os.environ.get("CODEX_CLI") or command_name("codex")


def harness_environment(args: argparse.Namespace, run_dir: Path) -> dict[str, str] | None:
    if args.harness != "opencode":
        return None
    config_file = run_dir / "inputs" / "opencode-config" / "opencode.json"
    environment = os.environ.copy()
    environment.update(
        {
            "OPENCODE_CONFIG": str(config_file),
            "OPENCODE_CONFIG_DIR": str(config_file.parent),
            "OPENCODE_CONFIG_CONTENT": config_file.read_text(encoding="utf-8"),
            "OPENCODE_AUTO_SHARE": "false",
            "OPENCODE_DISABLE_AUTOUPDATE": "true",
            "OPENCODE_DISABLE_PRUNE": "true",
            "OPENCODE_DISABLE_TERMINAL_TITLE": "true",
        }
    )
    return environment


def build_harness_command(
    args: argparse.Namespace,
    run_dir: Path,
    executable: str,
) -> list[str]:
    if args.harness == "claude":
        file_tools = "Read,Write,Edit,Glob,Grep"
        command = [
            executable,
            "--safe-mode",
            "--print",
            "--input-format",
            "text",
            "--output-format",
            "stream-json",
            "--verbose",
            "--no-session-persistence",
            "--no-chrome",
            "--strict-mcp-config",
            "--permission-mode",
            "dontAsk",
            "--tools",
            file_tools,
            "--allowedTools",
            file_tools,
            "--disallowedTools",
            "Bash,PowerShell,WebFetch,WebSearch,mcp__*",
            "--model",
            args.model,
        ]
        if args.reasoning_effort:
            command.extend(["--effort", args.reasoning_effort])
        return command

    if args.harness == "grok":
        command = [
            executable,
            "--no-auto-update",
            "--cwd",
            str(run_dir),
            "--prompt-file",
            str(run_dir / "inputs" / "task.md"),
            "--verbatim",
            "--output-format",
            "streaming-json",
            "--always-approve",
            "--sandbox",
            "strict",
            "--no-plan",
            "--no-subagents",
            "--no-memory",
            "--disable-web-search",
            "--disallowed-tools",
            "run_terminal_cmd,web_search,web_fetch,Agent",
            "--deny",
            "Bash",
            "--deny",
            "WebFetch",
            "--deny",
            "WebSearch",
            "--deny",
            "MCPTool",
            "--model",
            args.model,
        ]
        if args.reasoning_effort:
            command.extend(["--effort", args.reasoning_effort])
        return command

    if args.harness == "opencode":
        command = [
            executable,
            "--pure",
            "run",
            "--format",
            "json",
            "--model",
            args.model,
            "--agent",
            "build",
            "--dir",
            str(run_dir),
            "--title",
            run_dir.name,
            "--auto",
        ]
        if args.reasoning_effort:
            command.extend(["--variant", args.reasoning_effort])
        return command

    command = [
        executable,
        "exec",
        "--json",
        "--ephemeral",
        "--sandbox",
        "workspace-write",
        "--ignore-user-config",
        "--ignore-rules",
        "--skip-git-repo-check",
        "--model",
        args.model,
        "--cd",
        str(run_dir),
        "--output-last-message",
        "logs/final-message.txt",
        "--config",
        'web_search="disabled"',
        "--config",
        "sandbox_workspace_write.network_access=false",
    ]
    if args.reasoning_effort:
        command.extend(
            ["--config", f"model_reasoning_effort={json.dumps(args.reasoning_effort)}"]
        )
    command.append("-")
    return command


def run_command(args: argparse.Namespace) -> int:
    RUNS_ROOT.mkdir(exist_ok=True)
    try:
        harness_provider(args.harness, args.model)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        print("No run was saved, and evaluation was not started.", file=sys.stderr)
        return 2
    executable = harness_executable(args)
    version = cli_version(executable)
    label = harness_label(args.harness)
    if version is None:
        override = {
            "codex": "--codex or CODEX_CLI",
            "claude": "--claude or CLAUDE_CLI",
            "grok": "--grok or GROK_CLI",
            "opencode": "--opencode or OPENCODE_CLI",
        }[args.harness]
        print(
            f"error: could not run {label}. Install or upgrade it and authenticate it, or set {override}.",
            file=sys.stderr,
        )
        print("No run was saved, and evaluation was not started.", file=sys.stderr)
        return 2
    if args.harness == "claude":
        version_error = claude_version_error(version)
        if version_error:
            print(f"error: {version_error}", file=sys.stderr)
            print(
                "Upgrade Claude CLI and try again. No run was saved, and evaluation was not started.",
                file=sys.stderr,
            )
            return 2
    if args.harness == "opencode":
        version_error = opencode_version_error(version)
        if version_error:
            print(f"error: {version_error}", file=sys.stderr)
            print(
                "Upgrade OpenCode CLI and try again. No run was saved, and evaluation was not started.",
                file=sys.stderr,
            )
            return 2

    try:
        run_id = unique_run_id(args.model, args.run_id, args.harness)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    run_dir = RUNS_ROOT / run_id
    (run_dir / "outputs").mkdir(parents=True)
    (run_dir / "logs").mkdir()
    (run_dir / "evaluation").mkdir()
    manifest = prepare_manifest(args, run_id, run_dir)
    manifest_path = run_dir / "run.json"
    write_json(manifest_path, manifest)

    manifest["harness"]["version"] = version
    command = build_harness_command(args, run_dir, executable)
    manifest["harness"]["command"] = portable_command(command, run_dir)
    manifest["status"] = "running"
    write_json(manifest_path, manifest)

    print(f"Starting benchmark run {run_id}")
    print(f"Running {args.model} with {label}…")
    print(f"Reasoning effort: {args.reasoning_effort or 'CLI/model default'}")
    print(f"Execution timeout: {format_timeout(args.timeout)}")
    originality_broker: dict[str, Any] | None = None
    if manifest["condition"]["duplicateToolEnabled"]:
        query_limit = manifest["condition"]["duplicateQueryLimit"]
        print(f"Originality query budget: {query_limit} requests")
        try:
            originality_broker = start_originality_broker(run_dir, query_limit)
        except (OSError, RuntimeError) as error:
            discard_new_run(run_dir)
            print(f"error: could not start the originality tool: {error}", file=sys.stderr)
            print("No model was invoked, and no run was saved.", file=sys.stderr)
            return 2
    else:
        print("Originality query tool: disabled for this local-only diagnostic run")
    retry_delays = retry_schedule(
        args.max_attempts,
        args.retry_base_delay,
        args.retry_max_delay,
    )
    if retry_delays:
        print(
            f"Transient retry policy: up to {args.max_attempts} attempts; "
            f"backoff delays {', '.join(f'{delay}s' for delay in retry_delays)} "
            f"({format_elapsed(sum(retry_delays))} maximum wait)."
        )
    else:
        print("Transient retry policy: disabled (one attempt).")
    task = (run_dir / "inputs" / "task.md").read_text(encoding="utf-8")
    started = time.monotonic()
    stdout = ""
    stderr = ""
    exit_code: int | None = None
    timed_out = False
    timeout_message: str | None = None
    events: dict[str, Any] = {}
    final_message: str | None = None
    attempt_records: list[dict[str, Any]] = []
    total_backoff_seconds = 0
    event_parsers = {
        "codex": parse_codex_events,
        "claude": parse_claude_events,
        "grok": parse_grok_events,
        "opencode": parse_opencode_events,
    }

    for attempt_number in range(1, args.max_attempts + 1):
        remaining_timeout = args.timeout - (time.monotonic() - started)
        if remaining_timeout <= 0:
            break
        attempt_started_at = utc_now()
        result = run_harness_once(
            args,
            command,
            run_dir,
            task,
            label,
            remaining_timeout,
        )
        stdout = result["stdout"]
        stderr = result["stderr"]
        exit_code = result["exitCode"]
        timed_out = result["timedOut"]
        timeout_message = result["timeoutMessage"]
        events = event_parsers[args.harness](stdout)
        if timeout_message and not events.get("failureMessage"):
            events["failureMessage"] = timeout_message
        final_message = events.pop("finalMessage", None)
        failure_message = events.get("failureMessage")
        raw_output = f"{stdout}\n{stderr}"
        model_rejected = bool(
            exit_code and is_model_selection_failure(failure_message, raw_output)
        )
        retryable = bool(
            exit_code
            and not timed_out
            and not model_rejected
            and is_transient_harness_failure(failure_message, raw_output)
        )
        failure_detail = (
            compact_failure(failure_message, stdout, stderr, exit_code)
            if exit_code is not None and exit_code != 0
            else None
        )
        attempt_dir, attempt_stdout, attempt_stderr = write_harness_attempt_logs(
            run_dir,
            args.harness,
            attempt_number,
            stdout,
            stderr,
        )
        output_file_count = sum(
            1
            for file in (run_dir / "outputs").glob("*.sgf")
            if file.is_file()
        )
        attempt_record: dict[str, Any] = {
            "number": attempt_number,
            "startedAt": attempt_started_at,
            "completedAt": utc_now(),
            "exitCode": exit_code,
            "durationSeconds": result["durationSeconds"],
            "timedOut": timed_out,
            "retryable": retryable,
            "failureMessage": failure_detail,
            "outputFileCount": output_file_count,
            "stdout": attempt_stdout,
            "stderr": attempt_stderr,
        }

        can_retry = retryable and attempt_number < args.max_attempts
        if can_retry:
            delay = retry_delay_seconds(
                attempt_number,
                args.retry_base_delay,
                args.retry_max_delay,
            )
            remaining_after_attempt = args.timeout - (time.monotonic() - started)
            if delay < remaining_after_attempt:
                attempt_record["outcome"] = "transient_failure"
                attempt_record["retryDelaySeconds"] = delay
                archived_outputs = archive_retry_outputs(run_dir, attempt_dir)
                if archived_outputs:
                    attempt_record["archivedOutputs"] = archived_outputs
                attempt_records.append(attempt_record)
                manifest["harness"]["attempts"] = attempt_records
                write_json(manifest_path, manifest)
                print(
                    f"Attempt {attempt_number}/{args.max_attempts} failed after "
                    f"{format_elapsed(result['durationSeconds'])} with a transient error: "
                    f"{failure_detail}"
                )
                print(
                    f"Retrying in {format_elapsed(delay)} "
                    f"(attempt {attempt_number + 1}/{args.max_attempts})."
                )
                time.sleep(delay)
                total_backoff_seconds += delay
                continue
            attempt_record["retrySkippedReason"] = (
                "The remaining execution-time budget was too short for the next backoff delay."
            )

        if exit_code == 0:
            attempt_record["outcome"] = "success"
        elif model_rejected:
            attempt_record["outcome"] = "model_rejected"
        elif timed_out:
            attempt_record["outcome"] = "timeout"
        elif retryable:
            attempt_record["outcome"] = "transient_failure"
        else:
            attempt_record["outcome"] = "permanent_failure"
        attempt_records.append(attempt_record)
        manifest["harness"]["attempts"] = attempt_records
        write_json(manifest_path, manifest)
        break

    if originality_broker is not None:
        broker_exit_code = stop_originality_broker(run_dir, originality_broker)
        if broker_exit_code:
            broker_error = (run_dir / "logs" / "originality-broker-stderr.txt").read_text(
                encoding="utf-8"
            ).strip()
            print(
                f"Originality tool exited with status {broker_exit_code}"
                f"{f': {broker_error}' if broker_error else '.'}",
                file=sys.stderr,
            )
        summary_path = run_dir / "originality" / "summary.json"
        if summary_path.exists():
            originality_summary = read_json(summary_path)
            counts = originality_summary.get("results", {})
            print(
                "Originality queries: "
                f"{originality_summary.get('queriesUsed', 0)}/"
                f"{originality_summary.get('queryLimit', 0)}; "
                f"{counts.get('clear', 0)} clear, "
                f"{counts.get('duplicate', 0)} duplicate, "
                f"{counts.get('review', 0)} review, "
                f"{counts.get('invalid', 0) + counts.get('unavailable', 0)} errors."
            )

    duration = round(time.monotonic() - started, 3)
    (run_dir / manifest["artifacts"]["stdout"]).write_text(stdout, encoding="utf-8")
    (run_dir / manifest["artifacts"]["stderr"]).write_text(stderr, encoding="utf-8")
    final_message_path = run_dir / manifest["artifacts"]["finalMessage"]
    if final_message is not None or not final_message_path.exists():
        final_message_path.write_text(final_message or "", encoding="utf-8")
    manifest["harness"].update(
        {
            "exitCode": exit_code,
            "durationSeconds": duration,
            "attempts": attempt_records,
            **events,
        }
    )
    manifest["status"] = "harness_failed" if exit_code else "evaluating"
    if timed_out:
        manifest["condition"]["notes"] = (
            f"{manifest['condition']['notes']} Harness timed out after {format_timeout(args.timeout)}."
        ).strip()
    write_json(manifest_path, manifest)

    failure_message = manifest.get("harness", {}).get("failureMessage")
    if not exit_code and len(attempt_records) > 1:
        print(
            f"{label} succeeded on attempt {len(attempt_records)}/{args.max_attempts} "
            f"after {format_elapsed(duration)} total "
            f"({format_elapsed(total_backoff_seconds)} in backoff)."
        )
    if exit_code and is_model_selection_failure(failure_message, f"{stdout}\n{stderr}"):
        discard_new_run(run_dir)
        detail = failure_message or f"{label} exited with status {exit_code}."
        print(f"Model {args.model!r} was rejected by {label}: {detail}", file=sys.stderr)
        print(
            "No retries were attempted because model-selection failures are permanent. "
            "No run was saved, and evaluation was not started. Check the model ID and try again.",
            file=sys.stderr,
        )
        return 2

    if exit_code:
        print(
            f"{label} did not complete after {len(attempt_records)} "
            f"{'attempt' if len(attempt_records) == 1 else 'attempts'} over "
            f"{format_elapsed(duration)}. Evaluating any partial SGFs before finalizing the run.",
            file=sys.stderr,
        )
    print("Evaluating generated SGFs…")
    evaluator = run_evaluator(run_dir, args.local_only)
    manifest = read_json(manifest_path)
    if evaluator.returncode:
        manifest["status"] = "evaluation_failed"
    elif exit_code:
        manifest["status"] = "harness_failed"
    else:
        manifest["status"] = "completed"
    manifest["completedAt"] = utc_now()
    write_json(manifest_path, manifest)

    indexed = build_run_index()
    if indexed.returncode:
        (run_dir / "logs" / "indexer-stderr.txt").write_text(indexed.stderr, encoding="utf-8")
        print("Run completed, but the web index could not be rebuilt.", file=sys.stderr)
        return 1

    if evaluator.returncode:
        print(evaluator.stderr.strip() or "The evaluator failed.", file=sys.stderr)
        return 1
    if exit_code:
        detail = manifest.get("harness", {}).get("failureMessage") or (
            attempt_records[-1].get("failureMessage") if attempt_records else None
        )
        suffix = f": {detail}" if detail else "."
        print(
            f"{label} exited with status {exit_code} after {len(attempt_records)} "
            f"{'attempt' if len(attempt_records) == 1 else 'attempts'} over "
            f"{format_elapsed(duration)}; the partial run was preserved{suffix}",
            file=sys.stderr,
        )
        used_delays = [
            record["retryDelaySeconds"]
            for record in attempt_records
            if record.get("retryDelaySeconds") is not None
        ]
        if used_delays:
            print(
                "Retry report: exponential backoff waited "
                f"{format_elapsed(sum(used_delays))} total "
                f"({', '.join(format_elapsed(delay) for delay in used_delays)}).",
                file=sys.stderr,
            )
        else:
            final_outcome = attempt_records[-1].get("outcome") if attempt_records else None
            reasons = {
                "timeout": "the harness consumed the execution-time budget",
                "permanent_failure": "the failure was not classified as transient",
                "transient_failure": "no retry attempts or execution-time budget remained",
            }
            print(
                "Retry report: no retry was made because "
                f"{reasons.get(final_outcome, 'the failure was not retryable')}.",
                file=sys.stderr,
            )
        print("Attempt details:", file=sys.stderr)
        for record in attempt_records:
            outcome = record.get("outcome", "unknown").replace("_", " ")
            attempt_detail = record.get("failureMessage") or "Completed successfully."
            print(
                f"  {record['number']}. {outcome}; exit {record.get('exitCode')}; "
                f"{format_elapsed(record.get('durationSeconds', 0))}; "
                f"{record.get('outputFileCount', 0)} SGF files; {attempt_detail}",
                file=sys.stderr,
            )
        return 1

    evaluation = read_json(run_dir / "evaluation" / "automated.json")
    summary = evaluation.get("summary", {})
    expected_count = summary.get("expectedProblems", args.count)
    print(
        f"Run complete: {summary.get('structuralPassed', 0)}/{expected_count} structurally valid, "
        f"{summary.get('automatedGatePassed', 0)}/{expected_count} through automated gates."
    )
    print(f"Review it under runs/{run_id} or in the web UI.")
    return 0


def evaluate_command(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    if not run_dir.is_absolute():
        run_dir = (PROJECT_ROOT / run_dir).resolve()
    if not (run_dir / "run.json").exists():
        print(f"error: no run.json found under {run_dir}", file=sys.stderr)
        return 2
    result = run_evaluator(run_dir, args.local_only)
    if result.returncode:
        print(result.stderr.strip() or "The evaluator failed.", file=sys.stderr)
        return result.returncode
    manifest = read_json(run_dir / "run.json")
    manifest["status"] = (
        "harness_failed" if manifest.get("harness", {}).get("exitCode") else "completed"
    )
    manifest["completedAt"] = manifest.get("completedAt") or utc_now()
    write_json(run_dir / "run.json", manifest)
    indexed = build_run_index()
    if indexed.returncode:
        print(indexed.stderr.strip() or "The web index could not be rebuilt.", file=sys.stderr)
        return indexed.returncode
    print(result.stdout.strip())
    return 0


def index_command(_: argparse.Namespace) -> int:
    result = build_run_index()
    stream = sys.stdout if result.returncode == 0 else sys.stderr
    print((result.stdout or result.stderr).strip(), file=stream)
    return result.returncode


def review_command(args: argparse.Namespace) -> int:
    try:
        run_dir = reviewable_run(args.run_id)
        manifest = read_json(run_dir / "run.json")
        run_id = str(manifest["runId"])
        review_problem_files(run_dir)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    store_path = review_store_path(run_dir)
    if not store_path.exists():
        write_json(store_path, empty_review_store(run_id))
    indexed = build_run_index()
    if indexed.returncode:
        print(indexed.stderr.strip() or "The web run index could not be rebuilt.", file=sys.stderr)
        return indexed.returncode

    try:
        executable = typescript_node()
        web_port = available_port(args.port or 3001, 1 if args.port else 100)
    except (RuntimeError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    token = secrets.token_urlsafe(32)
    handler = make_review_handler(run_dir, run_id, token)
    api_server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    api_port = int(api_server.server_address[1])
    api_thread = threading.Thread(target=api_server.serve_forever, daemon=True)
    api_thread.start()

    command = [
        executable,
        "scripts/run-vinext.mjs",
        "dev",
        "--port",
        str(web_port),
        "--hostname",
        "127.0.0.1",
    ]
    process: subprocess.Popen[Any] | None = None
    try:
        process = subprocess.Popen(command, cwd=PROJECT_ROOT)
        site_root = f"http://127.0.0.1:{web_port}"
        if not wait_for_review_site(f"{site_root}/runs", process):
            return_code = process.poll()
            message = (
                f"The review site exited with status {return_code}."
                if return_code is not None
                else "The review site did not become ready in time."
            )
            print(f"error: {message}", file=sys.stderr)
            return 1

        query = urllib.parse.urlencode(
            {
                "review": "1",
                "run": run_id,
                "reviewApi": f"http://127.0.0.1:{api_port}",
                "token": token,
            }
        )
        review_url = f"{site_root}/runs?{query}"
        print(f"Reviewing {run_id}")
        print(f"Review UI: {review_url}")
        print("Review changes are saved into the run automatically.")
        print("Press Ctrl+C when the review session is finished.")
        if not args.no_open and not open_review_url(review_url):
            print("The browser could not be opened automatically; use the Review UI URL above.")

        while process.poll() is None:
            time.sleep(0.5)
        print(f"The review site exited with status {process.returncode}.", file=sys.stderr)
        return process.returncode or 0
    except KeyboardInterrupt:
        print("\nReview session stopped.")
        return 0
    except OSError as error:
        print(f"error: could not launch the review site: {error}", file=sys.stderr)
        return 1
    finally:
        api_server.shutdown()
        api_server.server_close()
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create, execute, evaluate, and index Tsumego Bench runs."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser(
        "run",
        help="Run a model through Codex CLI, Claude CLI, Grok CLI, or OpenCode CLI.",
    )
    run.add_argument(
        "--harness",
        choices=("codex", "claude", "grok", "opencode"),
        default="codex",
        help="CLI harness to invoke (default: codex).",
    )
    run.add_argument("--model", required=True, help="Exact model identifier for the selected CLI.")
    run.add_argument(
        "--reasoning-effort",
        "--effort",
        dest="reasoning_effort",
        help="Optional model effort level supported by the selected CLI.",
    )
    run.add_argument("--run-id", help="Optional stable run directory name.")
    run.add_argument("--attempt", type=int, default=1, help="Independent attempt number.")
    run.add_argument(
        "--count",
        type=int,
        default=DEFAULT_PROBLEM_COUNT,
        help=(
            f"Number of problems to generate (default: {DEFAULT_PROBLEM_COUNT}; "
            f"{MINIMUM_PROBLEM_COUNT}-{MAXIMUM_PROBLEM_COUNT})."
        ),
    )
    run.add_argument("--notes", help="Condition or invocation notes stored with the run.")
    run.add_argument(
        "--codex",
        help="Codex CLI executable path. Defaults to CODEX_CLI or codex on PATH.",
    )
    run.add_argument(
        "--claude",
        help="Claude CLI executable path. Defaults to CLAUDE_CLI or claude on PATH.",
    )
    run.add_argument(
        "--grok",
        help="Grok CLI executable path. Defaults to GROK_CLI or grok on PATH.",
    )
    run.add_argument(
        "--opencode",
        help="OpenCode CLI executable path. Defaults to OPENCODE_CLI or opencode on PATH.",
    )
    run.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_RUN_TIMEOUT_SECONDS,
        help="Maximum model CLI execution time in seconds (default: 43200 / 12 hours).",
    )
    run.add_argument(
        "--max-attempts",
        type=int,
        default=DEFAULT_MAX_HARNESS_ATTEMPTS,
        help=(
            "Maximum CLI attempts for recognized transient failures "
            f"(default: {DEFAULT_MAX_HARNESS_ATTEMPTS})."
        ),
    )
    run.add_argument(
        "--retry-base-delay",
        type=int,
        default=DEFAULT_RETRY_BASE_DELAY_SECONDS,
        help=(
            "Initial transient-failure backoff in seconds "
            f"(default: {DEFAULT_RETRY_BASE_DELAY_SECONDS})."
        ),
    )
    run.add_argument(
        "--retry-max-delay",
        type=int,
        default=DEFAULT_RETRY_MAX_DELAY_SECONDS,
        help=(
            "Maximum delay between transient retries in seconds "
            f"(default: {DEFAULT_RETRY_MAX_DELAY_SECONDS})."
        ),
    )
    run.add_argument(
        "--duplicate-query-limit",
        type=int,
        help=(
            "Maximum model-facing originality checks. Defaults to five times "
            "the requested problem count."
        ),
    )
    run.add_argument(
        "--local-only",
        action="store_true",
        help="Disable the live originality tool and skip post-run GoProblems API checks.",
    )
    run.set_defaults(handler=run_command)

    evaluate = subparsers.add_parser("evaluate", help="Re-evaluate an existing run.")
    evaluate.add_argument("run_dir", help="Run directory, such as runs/<run-id>.")
    evaluate.add_argument("--local-only", action="store_true")
    evaluate.set_defaults(handler=evaluate_command)

    index = subparsers.add_parser("index", help="Rebuild the web UI run index.")
    index.set_defaults(handler=index_command)

    review = subparsers.add_parser(
        "review",
        help="Open a local human-review session for the newest completed run.",
    )
    review.add_argument(
        "run_id",
        nargs="?",
        help="Optional run ID. Defaults to the most recently completed evaluated run.",
    )
    review.add_argument("--port", type=int, help="Optional local web port.")
    review.add_argument(
        "--no-open",
        action="store_true",
        help="Print the local review URL without opening a browser.",
    )
    review.set_defaults(handler=review_command)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if getattr(args, "attempt", 1) < 1:
        parser.error("--attempt must be at least 1")
    if getattr(args, "timeout", 1) < 1:
        parser.error("--timeout must be at least 1 second")
    if getattr(args, "max_attempts", 1) < 1:
        parser.error("--max-attempts must be at least 1")
    if getattr(args, "retry_base_delay", 0) < 0:
        parser.error("--retry-base-delay cannot be negative")
    if getattr(args, "retry_max_delay", 0) < 0:
        parser.error("--retry-max-delay cannot be negative")
    count = getattr(args, "count", DEFAULT_PROBLEM_COUNT)
    if not MINIMUM_PROBLEM_COUNT <= count <= MAXIMUM_PROBLEM_COUNT:
        parser.error(
            f"--count must be between {MINIMUM_PROBLEM_COUNT} and {MAXIMUM_PROBLEM_COUNT}"
        )
    configured_query_limit = getattr(args, "duplicate_query_limit", None)
    if configured_query_limit is not None and configured_query_limit < count:
        parser.error(
            "--duplicate-query-limit must allow at least one final query per problem"
        )
    port = getattr(args, "port", None)
    if port is not None and not 1 <= port <= 65535:
        parser.error("--port must be between 1 and 65535")
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
