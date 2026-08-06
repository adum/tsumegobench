#!/usr/bin/env python3
"""Run Tsumego Bench with the non-interactive Codex CLI."""

from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
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
        status = problem.get("status", "pending")
        if status not in {"pending", "completed"}:
            raise ValueError(f"Invalid review status for {file}.")

        valid = problem.get("valid")
        realistic = problem.get("realistic")
        difficulty = problem.get("estimatedDifficulty")
        quality = problem.get("quality")
        reviewed_at = problem.get("reviewedAt")
        if status == "pending":
            valid = realistic = difficulty = quality = reviewed_at = None
        else:
            if not isinstance(valid, bool) or not isinstance(realistic, bool):
                raise ValueError(f"Completed review for {file} needs both checkbox decisions.")
            if isinstance(quality, bool) or not isinstance(quality, int) or not 1 <= quality <= 5:
                raise ValueError(f"Completed review for {file} needs a 1-5 quality rating.")
            if valid:
                if difficulty not in DIFFICULTY_BANDS:
                    raise ValueError(f"A valid problem needs an estimated difficulty for {file}.")
            else:
                difficulty = None
            reviewed_at = reviewed_at if isinstance(reviewed_at, str) and reviewed_at else timestamp

        normalized_problems.append(
            {
                "file": file,
                "status": status,
                "valid": valid,
                "realistic": realistic,
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


def unique_run_id(model: str, requested: str | None) -> str:
    if requested:
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{2,100}", requested):
            raise ValueError(
                "--run-id must be 3–101 characters using letters, numbers, dots, underscores, or hyphens."
            )
        if (RUNS_ROOT / requested).exists():
            raise ValueError(f"Run directory already exists: runs/{requested}")
        return requested

    prefix = f"{datetime.now(timezone.utc):%Y-%m-%dT%H%M%SZ}-openai-{slugify(model)}-codex"
    candidate = prefix
    suffix = 2
    while (RUNS_ROOT / candidate).exists():
        candidate = f"{prefix}-{suffix:02d}"
        suffix += 1
    return candidate


def copy_inputs(run_dir: Path, problem_count: int) -> list[dict[str, str]]:
    inputs = run_dir / "inputs"
    examples = inputs / "examples"
    examples.mkdir(parents=True)

    copies = {
        PROJECT_ROOT / "docs" / "model-prompt.md": inputs / "model-prompt.md",
        PROJECT_ROOT / "docs" / "authoring-guide.md": inputs / "authoring-guide.md",
        PROJECT_ROOT / "docs" / "benchmark-spec.md": inputs / "benchmark-spec.md",
        PROJECT_ROOT / "examples" / "manifest.json": inputs / "reference-manifest.json",
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
    task = f"""# Tsumego Bench execution task

This is a controlled benchmark run. Work only inside the current run directory.

1. Read `inputs/model-prompt.md` in full and follow it exactly.
2. Use `inputs/authoring-guide.md`, `inputs/reference-manifest.json`, and all SGFs in `inputs/examples/` as the supplied reference material.
3. Create exactly {problem_count} final candidate SGF files using these names and target difficulties:
{target_lines}
4. Each output file must contain only one complete SGF collection—no Markdown fences or explanatory prose.
5. Do not modify anything under `inputs/`, `logs/`, or `evaluation/`, and do not modify `run.json`.
6. Do not access the web or any network service. Duplicate checks are performed by the benchmark after you exit.
7. Do not run the benchmark evaluator yourself. Finish all {problem_count} files, verify them locally as far as you can, then exit.

Do not ask the operator questions and do not wait for repair feedback.
"""
    (inputs / "task.md").write_text(task, encoding="utf-8")

    records: list[dict[str, str]] = []
    for file in sorted(path for path in inputs.rglob("*") if path.is_file()):
        records.append(
            {
                "path": file.relative_to(run_dir).as_posix(),
                "sha256": sha256_file(file),
            }
        )
    return records


def codex_version(executable: str) -> str | None:
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
        value = (result.stdout or result.stderr).strip()
        return value or None
    except (OSError, subprocess.TimeoutExpired):
        return None


def parse_codex_events(stdout: str) -> dict[str, Any]:
    thread_id: str | None = None
    usage: dict[str, Any] | None = None
    parse_errors = 0
    event_count = 0
    failure_message: str | None = None

    def message_from(value: Any) -> str | None:
        if isinstance(value, str):
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError:
                return value.strip() or None
            return message_from(decoded)
        if isinstance(value, dict):
            error = value.get("error")
            if error is not None:
                nested = message_from(error)
                if nested:
                    return nested
            message = value.get("message")
            if message is not None:
                return message_from(message)
        return None

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
            failure_message = message_from(event) or failure_message
    return {
        "threadId": thread_id,
        "usage": usage,
        "eventCount": event_count,
        "unparsedLineCount": parse_errors,
        "failureMessage": failure_message,
    }


def is_model_selection_failure(message: str | None, raw_output: str = "") -> bool:
    evidence = f"{message or ''}\n{raw_output}".lower()
    patterns = (
        "model is not supported",
        "not supported when using codex",
        "model_not_found",
        "invalid model",
        "model does not exist",
        "model not found",
        "model is unavailable",
        "unsupported model",
        "does not exist or you do not have access to it",
        "you do not have access to this model",
    )
    return any(pattern in evidence for pattern in patterns)


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
    input_files = copy_inputs(run_dir, args.count)
    output_names = expected_output_names(args.count)
    model_prompt = run_dir / "inputs" / "model-prompt.md"
    reference_manifest = run_dir / "inputs" / "reference-manifest.json"
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
            "provider": "openai",
            "name": args.model,
            "reasoningEffort": args.reasoning_effort,
        },
        "harness": {
            "name": "codex-cli",
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
        },
        "condition": {
            "attempt": args.attempt,
            "problemCount": args.count,
            "toolsEnabled": True,
            "webEnabled": False,
            "networkEnabled": False,
            "duplicateToolEnabled": False,
            "remoteDuplicateEvaluation": not args.local_only,
            "notes": args.notes or "",
        },
        "artifacts": {
            "task": "inputs/task.md",
            "stdout": "logs/codex-events.jsonl",
            "stderr": "logs/codex-stderr.txt",
            "finalMessage": "logs/final-message.txt",
            "outputs": [f"outputs/{name}" for name in output_names],
            "automatedEvaluation": "evaluation/automated.json",
            "humanEvaluation": "evaluation/human.json",
            "humanReviews": "evaluation/reviews.json",
            "results": "evaluation/results.json",
        },
    }


def run_command(args: argparse.Namespace) -> int:
    RUNS_ROOT.mkdir(exist_ok=True)
    try:
        run_id = unique_run_id(args.model, args.run_id)
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

    executable = args.codex or os.environ.get("CODEX_CLI") or command_name("codex")
    manifest["harness"]["version"] = codex_version(executable)
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
    manifest["harness"]["command"] = portable_command(command, run_dir)
    manifest["status"] = "running"
    write_json(manifest_path, manifest)

    print(f"Starting benchmark run {run_id}")
    print(f"Running {args.model} with Codex CLI…")
    task = (run_dir / "inputs" / "task.md").read_text(encoding="utf-8")
    started = time.monotonic()
    stdout = ""
    stderr = ""
    exit_code: int | None = None
    timed_out = False
    try:
        completed = subprocess.run(
            command,
            cwd=run_dir,
            input=task,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=args.timeout,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        exit_code = completed.returncode
    except subprocess.TimeoutExpired as error:
        timed_out = True
        stdout = error.stdout or ""
        stderr = error.stderr or ""
        exit_code = 124
    except OSError as error:
        stderr = f"Could not launch Codex CLI: {error}\n"
        exit_code = 127

    duration = round(time.monotonic() - started, 3)
    (run_dir / "logs" / "codex-events.jsonl").write_text(stdout, encoding="utf-8")
    (run_dir / "logs" / "codex-stderr.txt").write_text(stderr, encoding="utf-8")
    events = parse_codex_events(stdout)
    manifest["harness"].update(
        {
            "exitCode": exit_code,
            "durationSeconds": duration,
            **events,
        }
    )
    manifest["status"] = "harness_failed" if exit_code else "evaluating"
    if timed_out:
        manifest["condition"]["notes"] = (
            f"{manifest['condition']['notes']} Harness timed out after {args.timeout} seconds."
        ).strip()
    write_json(manifest_path, manifest)

    failure_message = manifest.get("harness", {}).get("failureMessage")
    if exit_code and is_model_selection_failure(failure_message, f"{stdout}\n{stderr}"):
        discard_new_run(run_dir)
        detail = failure_message or f"Codex CLI exited with status {exit_code}."
        print(f"Model {args.model!r} was rejected by Codex: {detail}", file=sys.stderr)
        print(
            "No run was saved, and evaluation was not started. Check the model ID and try again.",
            file=sys.stderr,
        )
        return 2

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
        detail = manifest.get("harness", {}).get("failureMessage")
        suffix = f": {detail}" if detail else "."
        print(
            f"Codex CLI exited with status {exit_code}; the partial run was preserved{suffix}",
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
        print("Review changes are saved into the run as you submit each problem.")
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

    run = subparsers.add_parser("run", help="Run an OpenAI model through Codex CLI.")
    run.add_argument("--model", required=True, help="Exact OpenAI model identifier for Codex.")
    run.add_argument("--reasoning-effort", help="Optional Codex model reasoning effort.")
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
        "--timeout",
        type=int,
        default=3600,
        help="Maximum Codex execution time in seconds (default: 3600).",
    )
    run.add_argument(
        "--local-only",
        action="store_true",
        help="Skip GoProblems API checks during post-run evaluation.",
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
    count = getattr(args, "count", DEFAULT_PROBLEM_COUNT)
    if not MINIMUM_PROBLEM_COUNT <= count <= MAXIMUM_PROBLEM_COUNT:
        parser.error(
            f"--count must be between {MINIMUM_PROBLEM_COUNT} and {MAXIMUM_PROBLEM_COUNT}"
        )
    port = getattr(args, "port", None)
    if port is not None and not 1 <= port <= 65535:
        parser.error("--port must be between 1 and 65535")
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
