#!/usr/bin/env python3
"""Run Tsumego Bench with a supported non-interactive model CLI."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import http.server
import json
import math
import os
import queue
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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


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
DEFAULT_PROGRESS_INTERVAL_SECONDS = 60
DEFAULT_CLAUDE_MAX_ROUNDS = 20
DEFAULT_CLAUDE_STALE_ROUND_LIMIT = 3
DEFAULT_CLAUDE_SESSION_RESET_GRACE_SECONDS = 60
CLAUDE_OUTPUT_TOKEN_MAX = 128_000
DEFAULT_GROK_MAX_ROUNDS = 20
DEFAULT_GROK_STALE_ROUND_LIMIT = 3
DEFAULT_OPENCODE_MAX_ROUNDS = 20
OPENCODE_OUTPUT_TOKEN_MAX = 65_536
DEFAULT_REVIEW_STARTUP_TIMEOUT_SECONDS = 120
REVIEW_PROBE_REQUEST_TIMEOUT_SECONDS = 10
MINIMUM_CLAUDE_VERSION = (2, 1, 217)
MINIMUM_OPENCODE_VERSION = (1, 1, 1)
GENERATION_DIFFICULTY_BANDS = (
    "20-30 kyu",
    "10-19 kyu",
    "5-9 kyu",
    "1-4 kyu",
    "about 1 dan",
)
DIFFICULTY_BANDS = (
    *GENERATION_DIFFICULTY_BANDS,
    "2-3 dan",
    "4 dan or harder",
)
MINIMUM_NODE_MAJOR = 22
_TYPESCRIPT_NODE: str | None = None
REVIEW_STORE_NAME = "reviews.json"
TERMINAL_RUN_STATUSES = {"completed", "harness_failed", "evaluation_failed"}


def expected_output_names(count: int) -> list[str]:
    return [f"problem-{index:02d}.sgf" for index in range(1, count + 1)]


def difficulty_targets(count: int) -> list[str]:
    return [
        GENERATION_DIFFICULTY_BANDS[
            min(
                len(GENERATION_DIFFICULTY_BANDS) - 1,
                index * len(GENERATION_DIFFICULTY_BANDS) // count,
            )
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


def concatenate_harness_output(chunks: list[str]) -> str:
    combined = ""
    for chunk in chunks:
        if not chunk:
            continue
        if combined and not combined.endswith("\n"):
            combined += "\n"
        combined += chunk
    return combined


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


def generated_sgf_count(run_dir: Path) -> int:
    return sum(
        1
        for file in (run_dir / "outputs").glob("*.sgf")
        if file.is_file()
    )


def missing_expected_sgf_names(run_dir: Path, count: int) -> list[str]:
    outputs = run_dir / "outputs"
    return [
        name
        for name in expected_output_names(count)
        if not (outputs / name).is_file()
    ]


def expected_sgf_count(run_dir: Path, count: int) -> int:
    return count - len(missing_expected_sgf_names(run_dir, count))


def originality_query_progress(run_dir: Path) -> tuple[int | None, int | None]:
    summary_path = run_dir / "originality" / "summary.json"
    try:
        summary = read_json(summary_path) if summary_path.exists() else None
    except (OSError, json.JSONDecodeError):
        return None, None
    if not isinstance(summary, dict):
        return None, None
    queries_used = summary.get("queriesUsed")
    query_limit = summary.get("queryLimit")
    return (
        queries_used if isinstance(queries_used, int) else None,
        query_limit if isinstance(query_limit, int) else None,
    )


def generation_progress_snapshot(run_dir: Path) -> tuple[tuple[tuple[str, int, int], ...], int | None]:
    outputs = run_dir / "outputs"
    files: list[tuple[str, int, int]] = []
    for file in sorted(outputs.glob("*.sgf")):
        try:
            stat = file.stat()
        except OSError:
            continue
        files.append((file.name, stat.st_size, stat.st_mtime_ns))
    queries_used, _ = originality_query_progress(run_dir)
    return tuple(files), queries_used


def claude_stream_message(content: str) -> str:
    return json.dumps(
        {
            "type": "user",
            "message": {"role": "user", "content": content},
            "parent_tool_use_id": None,
        },
        ensure_ascii=False,
    )


def claude_continuation_task(
    run_dir: Path,
    count: int,
    round_number: int,
    max_rounds: int = DEFAULT_CLAUDE_MAX_ROUNDS,
    previous_result: dict[str, Any] | None = None,
    consecutive_stale_rounds: int = 0,
    stale_round_limit: int = DEFAULT_CLAUDE_STALE_ROUND_LIMIT,
) -> str:
    missing = missing_expected_sgf_names(run_dir, count)
    present = [name for name in expected_output_names(count) if name not in missing]
    queries_used, query_limit = originality_query_progress(run_dir)
    query_status = (
        f"{queries_used}/{query_limit} originality queries have been used"
        if queries_used is not None and query_limit is not None
        else "the shared originality-query status is available in `originality/summary.json`"
    )
    boundary_note = ""
    if previous_result and is_claude_output_limit_result(previous_result):
        boundary_note = (
            " Your previous turn reached its output-token boundary; this is a continuation, "
            "not a restart."
        )
    stale_warning = ""
    if (
        stale_round_limit > 0
        and consecutive_stale_rounds >= stale_round_limit - 1
    ):
        stale_warning = (
            "\n\nIMPORTANT - FINAL NO-PROGRESS TURN: The harness has observed "
            f"{consecutive_stale_rounds} consecutive continuation turns without measurable "
            "progress. If this turn does not create or revise an SGF file or advance the "
            "originality-query count, the session will stop at the "
            f"{stale_round_limit}-turn no-progress limit. Make concrete progress during this "
            "turn and persist useful work to the run directory before returning control.\n"
        )

    present_list = ", ".join(f"`{name}`" for name in present) or "none"
    missing_list = ", ".join(f"`{name}`" for name in missing) or "none"
    return f"""# Continue the Tsumego Bench run

This is continuation turn {round_number} of at most {max_rounds} in the same Claude session.{boundary_note} Keep and use all of the analysis and context you have already developed.
{stale_warning}

The benchmark does not assign one problem per turn. Choose the most efficient workflow yourself: you may research, construct, revise, originality-check, or finish any number of problems during this turn. Do not start over and do not discard good work already present.

Current observable run state:
- {len(present)}/{count} expected SGF files are present.
- Present: {present_list}
- Missing: {missing_list}
- {query_status}; the budget is shared across all continuation turns.

Continue following the complete original task in `inputs/task.md`. Inspect existing files before changing them, repair anything you determine is incomplete, write final SGFs as they become ready, and perform the required final originality checks. Return control only after making as much concrete progress as is useful in this turn.
"""


def claude_session_resume_task(base_task: str, run_dir: Path, count: int) -> str:
    missing = missing_expected_sgf_names(run_dir, count)
    present = [name for name in expected_output_names(count) if name not in missing]
    present_list = ", ".join(f"`outputs/{name}`" for name in present) or "none"
    missing_list = ", ".join(f"`outputs/{name}`" for name in missing) or "none"
    return f"""# Resume the Tsumego Bench run after a Claude session-limit reset

The prior Claude session reached its usage limit. This is a fresh in-memory session in the same run directory. Continue the existing benchmark run instead of starting over: inspect and preserve good on-disk work, use `inputs/task.md` as the complete source of truth, and spend the shared originality-query budget carefully.

Current observable run state:
- {len(present)}/{count} expected SGF files are present.
- Present: {present_list}
- Missing: {missing_list}

Complete the benchmark using the original task below.

---

{base_task}
"""


def opencode_round_task(
    base_task: str,
    run_dir: Path,
    count: int,
    round_number: int,
    max_rounds: int = DEFAULT_OPENCODE_MAX_ROUNDS,
) -> str:
    if round_number == 1:
        return base_task

    missing = missing_expected_sgf_names(run_dir, count)
    present_count = count - len(missing)
    missing_list = "\n".join(f"- `outputs/{name}`" for name in missing)
    return f"""# Tsumego Bench continuation round

This is OpenCode generation round {round_number} of at most {max_rounds}. Continue from the current run directory; work from the files already present rather than starting over.

Read `inputs/task.md` again and follow the complete original task. There are currently {present_count}/{count} expected SGF files present. Create and finish these missing files:

{missing_list}

The originality-query budget is shared across every round. Inspect `originality/summary.json` before making more requests. Preserve good existing outputs, repair any existing output you determine is incomplete, and do not merely describe future work. Write the remaining final SGFs now, perform the required final originality checks, and return control only after making as much concrete progress as possible in this round.
"""


def grok_round_task(
    base_task: str,
    run_dir: Path,
    count: int,
    round_number: int,
    max_rounds: int = DEFAULT_GROK_MAX_ROUNDS,
    consecutive_stale_rounds: int = 0,
    stale_round_limit: int = DEFAULT_GROK_STALE_ROUND_LIMIT,
) -> str:
    if round_number == 1:
        return base_task

    missing = missing_expected_sgf_names(run_dir, count)
    present = [name for name in expected_output_names(count) if name not in missing]
    queries_used, query_limit = originality_query_progress(run_dir)
    query_status = (
        f"{queries_used}/{query_limit} originality queries have been used"
        if queries_used is not None and query_limit is not None
        else "the shared originality-query status is available in `originality/summary.json`"
    )
    stale_warning = ""
    if stale_round_limit > 0 and consecutive_stale_rounds >= stale_round_limit - 1:
        stale_warning = (
            "\n\nIMPORTANT - FINAL NO-PROGRESS ROUND: The harness has observed "
            f"{consecutive_stale_rounds} consecutive Grok rounds without measurable "
            "SGF or originality-query progress. If this round also makes no progress, "
            f"the run will stop at the {stale_round_limit}-round no-progress limit. "
            "Persist concrete progress to the run directory before returning.\n"
        )

    present_list = ", ".join(f"`outputs/{name}`" for name in present) or "none"
    missing_list = ", ".join(f"`outputs/{name}`" for name in missing) or "none"
    return f"""# Continue the Tsumego Bench run

This is Grok continuation round {round_number} of at most {max_rounds} in the same Grok session. Keep and use the analysis and context from the preceding rounds. Continue from the current run directory instead of starting over.
{stale_warning}

The benchmark does not assign one problem per round. Choose the most efficient workflow yourself: you may research, construct, revise, originality-check, or finish any number of problems during this round.

Current observable run state:
- {len(present)}/{count} expected SGF files are present.
- Present: {present_list}
- Missing: {missing_list}
- {query_status}; the budget is shared across all continuation rounds.

Read `inputs/task.md` again when you need the complete source of truth. Inspect and preserve good existing work, repair anything incomplete, write final SGFs as they become ready, and perform the required final originality checks. Do not merely print SGF text in your response: save each finished problem to its required file under `outputs/`. Return control only after making as much concrete progress as is useful in this round.
"""


def benchmark_progress_message(
    run_dir: Path,
    label: str,
    attempt_number: int,
    max_attempts: int,
    expected_count: int,
    elapsed_seconds: float,
) -> str:
    details = [
        f"{format_elapsed(elapsed_seconds)} elapsed",
        f"{generated_sgf_count(run_dir)}/{expected_count} SGFs written",
    ]
    summary_path = run_dir / "originality" / "summary.json"
    try:
        summary = read_json(summary_path) if summary_path.exists() else None
    except (OSError, json.JSONDecodeError):
        # The broker rewrites this file while the reporter may be reading it.
        summary = None
    if isinstance(summary, dict):
        queries_used = summary.get("queriesUsed")
        query_limit = summary.get("queryLimit")
        if isinstance(queries_used, int) and isinstance(query_limit, int):
            details.append(f"{queries_used}/{query_limit} originality queries used")
    return (
        f"Still running {label} (attempt {attempt_number}/{max_attempts}): "
        f"{'; '.join(details)}."
    )


def start_progress_reporter(
    run_dir: Path,
    label: str,
    attempt_number: int,
    max_attempts: int,
    expected_count: int,
    interval_seconds: float = DEFAULT_PROGRESS_INTERVAL_SECONDS,
) -> tuple[threading.Event, threading.Thread]:
    stop_event = threading.Event()
    started = time.monotonic()

    def report() -> None:
        while not stop_event.wait(interval_seconds):
            print(
                benchmark_progress_message(
                    run_dir,
                    label,
                    attempt_number,
                    max_attempts,
                    expected_count,
                    time.monotonic() - started,
                ),
                flush=True,
            )

    thread = threading.Thread(
        target=report,
        name="benchmark-progress-reporter",
        daemon=True,
    )
    thread.start()
    return stop_event, thread


def stop_progress_reporter(reporter: tuple[threading.Event, threading.Thread]) -> None:
    stop_event, thread = reporter
    stop_event.set()
    thread.join()


def retry_delay_seconds(completed_attempt: int, base_delay: int, maximum_delay: int) -> int:
    return min(maximum_delay, base_delay * (2 ** max(0, completed_attempt - 1)))


def retry_schedule(max_attempts: int, base_delay: int, maximum_delay: int) -> list[int]:
    return [
        retry_delay_seconds(attempt, base_delay, maximum_delay)
        for attempt in range(1, max_attempts)
    ]


def is_claude_session_limit_failure(message: str | None, raw_output: str = "") -> bool:
    evidence = f"{message or ''}\n{raw_output}".lower().replace("’", "'")
    return "you've hit your session limit" in evidence and "reset" in evidence


def claude_session_limit_reset_at(
    message: str | None,
    raw_output: str = "",
    *,
    now: datetime | None = None,
) -> datetime | None:
    evidence = f"{message or ''}\n{raw_output}".replace("’", "'")
    if not is_claude_session_limit_failure(message, raw_output):
        return None
    match = re.search(
        r"\bresets?\b[^\r\n]{0,80}?"
        r"(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*"
        r"(?P<meridiem>a\.?m\.?|p\.?m\.?)"
        r"(?:\s*\((?P<timezone>[A-Za-z0-9_+\-/]+)\))?",
        evidence,
        flags=re.IGNORECASE,
    )
    if match is None:
        return None

    hour = int(match.group("hour"))
    minute = int(match.group("minute") or "0")
    if not 1 <= hour <= 12 or not 0 <= minute <= 59:
        return None
    meridiem = match.group("meridiem").lower().replace(".", "")
    hour = hour % 12 + (12 if meridiem == "pm" else 0)

    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    timezone_name = match.group("timezone")
    if timezone_name:
        try:
            reset_timezone = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            # Windows Python does not bundle the IANA timezone database. Claude
            # reports the operator's timezone, so the process-local zone is the
            # safest fallback when the named zone cannot be loaded.
            reset_timezone = datetime.now().astimezone().tzinfo or timezone.utc
    else:
        reset_timezone = datetime.now().astimezone().tzinfo or timezone.utc

    local_reference = reference.astimezone(reset_timezone)
    reset_at = local_reference.replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )
    if reset_at <= local_reference:
        # Claude reports minute precision. A response can arrive just after the
        # displayed reset minute, so retry shortly instead of waiting a full day.
        if local_reference - reset_at <= timedelta(minutes=15):
            reset_at = local_reference
        else:
            reset_at += timedelta(days=1)
    return reset_at + timedelta(seconds=DEFAULT_CLAUDE_SESSION_RESET_GRACE_SECONDS)


def claude_session_limit_pause_seconds(
    reset_at: datetime,
    *,
    now: datetime | None = None,
) -> int:
    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    return max(
        0,
        math.ceil(
            (
                reset_at.astimezone(timezone.utc)
                - reference.astimezone(timezone.utc)
            ).total_seconds()
        ),
    )


def format_claude_session_reset(reset_at: datetime) -> str:
    hour = reset_at.hour % 12 or 12
    meridiem = "AM" if reset_at.hour < 12 else "PM"
    zone = reset_at.tzname() or "local time"
    return (
        f"{hour}:{reset_at.minute:02d} {meridiem} {zone} on "
        f"{reset_at.strftime('%b')} {reset_at.day}, {reset_at.year}"
    )


def wait_for_claude_session_reset(
    run_dir: Path,
    expected_count: int,
    resume_at: datetime,
) -> int:
    started = time.monotonic()
    while True:
        remaining = claude_session_limit_pause_seconds(resume_at)
        if remaining <= 0:
            break
        step = min(DEFAULT_PROGRESS_INTERVAL_SECONDS, remaining)
        time.sleep(step)
        remaining = claude_session_limit_pause_seconds(resume_at)
        if remaining <= 0:
            continue
        details = [
            f"{format_elapsed(remaining)} remaining",
            f"{expected_sgf_count(run_dir, expected_count)}/{expected_count} SGFs preserved",
        ]
        queries_used, query_limit = originality_query_progress(run_dir)
        if queries_used is not None and query_limit is not None:
            details.append(f"{queries_used}/{query_limit} originality queries used")
        print(f"Waiting for Claude session reset: {'; '.join(details)}.", flush=True)
    return max(0, round(time.monotonic() - started))


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


def review_passes_human_gates(problem: dict[str, Any]) -> bool:
    return (
        problem.get("valid") is True
        and problem.get("realistic") is True
        and problem.get("duplicate") is False
        and problem.get("wellPathed") is True
    )


def review_problem_complete(problem: dict[str, Any]) -> bool:
    rejected = (
        problem.get("valid") is False
        or problem.get("realistic") is False
        or problem.get("duplicate") is True
        or problem.get("wellPathed") is False
    )
    return rejected or (
        review_passes_human_gates(problem)
        and problem.get("estimatedDifficulty") in DIFFICULTY_BANDS
    )


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
        normalized_gates = {
            "valid": valid,
            "realistic": realistic,
            "duplicate": duplicate,
            "wellPathed": well_pathed,
            "estimatedDifficulty": difficulty,
        }
        if not review_passes_human_gates(normalized_gates):
            difficulty = None
            quality = None

        normalized_gates["estimatedDifficulty"] = difficulty
        complete = review_problem_complete(normalized_gates)
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
        completed = [problem for problem in review["problems"] if review_problem_complete(problem)]
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
            if any(
                record["file"] == file and review_problem_complete(record)
                for record in review["problems"]
            )
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


def opencode_available_models(executable: str) -> list[str] | None:
    try:
        result = subprocess.run(
            [executable, "--pure", "models"],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode:
        return None

    ansi_escape = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
    models: set[str] = set()
    for raw_line in result.stdout.splitlines():
        line = ansi_escape.sub("", raw_line).strip()
        if line.startswith(("- ", "* ")):
            line = line[2:].strip()
        if line and "/" in line and not any(character.isspace() for character in line):
            models.add(line)
    return sorted(models)


def opencode_model_validation_error(executable: str, model: str) -> str | None:
    available = opencode_available_models(executable)
    if not available or model in available:
        return None

    provider, model_name = opencode_model_parts(model)
    provider_models = [candidate for candidate in available if candidate.startswith(f"{provider}/")]
    suggestions: list[str] = []
    if model_name in available:
        suggestions.append(model_name)
    else:
        suggestions.extend(
            difflib.get_close_matches(model, available, n=3, cutoff=0.45)
        )
    if not suggestions:
        basename = model.rsplit("/", 1)[-1]
        suggestions.extend(
            candidate
            for candidate in available
            if candidate.rsplit("/", 1)[-1] == basename
        )

    lines = [
        f"OpenCode does not list model {model!r}.",
        f"It is parsed as provider {provider!r} and model {model_name!r}.",
    ]
    if suggestions:
        label = "Did you mean" if len(suggestions) == 1 else "Closest available models"
        lines.append(f"{label}: {', '.join(repr(candidate) for candidate in suggestions[:3])}?")
    elif provider_models:
        lines.append(
            f"Provider {provider!r} is available, but that model ID is not in its catalog."
        )
    else:
        lines.append(
            f"Provider {provider!r} is not available in this OpenCode installation or account."
        )
    lines.append("Run `opencode models` to copy an exact provider/model ID.")
    return "\n".join(lines)


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
   These targets are guidance for producing a useful range, not score caps on harder work. Human reviewers determine actual difficulty. In the final score, at most two valid 20-30 kyu problems and at most two valid 10-19 kyu problems receive credit; every valid problem rated 5-9 kyu or harder can receive credit. Problems harder than 1 dan are allowed. Aim to spread the harder problems across multiple levels rather than clustering them all at one difficulty.
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
            f"Claude CLI {required} or newer is required for the benchmark's isolated streaming mode; "
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


def is_claude_output_limit_result(event: dict[str, Any]) -> bool:
    if event.get("type") != "result":
        return False
    evidence = json.dumps(event, ensure_ascii=False).lower()
    patterns = (
        "max_tokens",
        "maximum output token",
        "max output token",
        "output token maximum",
        "output length limit",
    )
    return any(pattern in evidence for pattern in patterns) or (
        "response exceeded" in evidence and "output token" in evidence
    )


def is_grok_output_limit_failure(message: str | None, raw_output: str = "") -> bool:
    evidence = f"{message or ''}\n{raw_output}".lower()
    return (
        "max_tokens_truncation" in evidence
        or "response truncated by max_tokens" in evidence
    )


def merge_numeric_usage(
    target: dict[str, Any],
    source: dict[str, Any],
    preserve_numeric_keys: frozenset[str] = frozenset(),
) -> None:
    for key, value in source.items():
        if isinstance(value, dict):
            nested = target.setdefault(key, {})
            if not isinstance(nested, dict):
                nested = {}
                target[key] = nested
            merge_numeric_usage(nested, value, preserve_numeric_keys)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            if key in preserve_numeric_keys:
                target[key] = value
            else:
                existing = target.get(key, 0)
                target[key] = existing + value if isinstance(existing, (int, float)) else value
        else:
            target[key] = value


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
    usage: dict[str, Any] = {}
    has_usage = False
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
            if isinstance(event.get("usage"), dict):
                merge_numeric_usage(usage.setdefault("usage", {}), event["usage"])
                has_usage = True
            if isinstance(event.get("modelUsage"), dict):
                merge_numeric_usage(
                    usage.setdefault("modelUsage", {}),
                    event["modelUsage"],
                    frozenset({"contextWindow", "maxOutputTokens"}),
                )
                has_usage = True
            for key in ("total_cost_usd", "duration_api_ms", "num_turns"):
                value = event.get(key)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    usage[key] = usage.get(key, 0) + value
                    has_usage = True
            if event.get("is_error") or event.get("subtype") not in {None, "success"}:
                failure_message = event_message(event) or final_message or failure_message
            else:
                # A prior output-length boundary is recoverable in streaming mode.
                # A later successful result determines the session's final status.
                failure_message = None
        elif event.get("type") == "error":
            failure_message = event_message(event) or failure_message

    return {
        "threadId": session_id,
        "usage": usage if has_usage else None,
        "eventCount": event_count,
        "unparsedLineCount": parse_errors,
        "failureMessage": failure_message,
        "finalMessage": final_message,
    }


def parse_grok_events(stdout: str) -> dict[str, Any]:
    session_id: str | None = None
    usage: dict[str, Any] = {}
    has_usage = False
    parse_errors = 0
    event_count = 0
    failure_message: str | None = None
    current_message_parts: list[str] = []
    final_message: str | None = None
    result_subtype: str | None = None

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
            if isinstance(event.get("usage"), dict):
                merge_numeric_usage(usage.setdefault("usage", {}), event["usage"])
                has_usage = True
            if isinstance(event.get("modelUsage"), dict):
                merge_numeric_usage(usage.setdefault("modelUsage", {}), event["modelUsage"])
                has_usage = True
            for key in ("total_cost_usd", "total_cost_usd_ticks", "num_turns"):
                value = event.get(key)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    usage[key] = usage.get(key, 0) + value
                    has_usage = True
            for key in ("cost_is_partial", "usage_is_incomplete", "requestId"):
                if event.get(key) is not None:
                    usage[key] = event[key]
                    has_usage = True
            result_subtype = event.get("stopReason") or result_subtype
        if event_type == "error":
            failure_message = event_message(event) or failure_message
            if is_grok_output_limit_failure(failure_message, json.dumps(event)):
                result_subtype = "max_tokens_truncation"
        elif event_type == "end":
            failure_message = None

    if current_message_parts:
        final_message = "".join(current_message_parts).strip() or final_message
    return {
        "threadId": session_id,
        "usage": usage if has_usage else None,
        "eventCount": event_count,
        "unparsedLineCount": parse_errors,
        "failureMessage": failure_message,
        "finalMessage": final_message,
        "resultSubtype": result_subtype,
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


def is_run_configuration_failure(message: str | None, raw_output: str = "") -> bool:
    if is_model_selection_failure(message, raw_output):
        return True
    evidence = f"{message or ''}\n{raw_output}".lower()
    unsupported_model_option = all(
        pattern in evidence
        for pattern in (
            "unsupported value:",
            "is not supported with",
            "model",
            "supported values are:",
        )
    )
    explicit_effort_error = (
        "reasoning effort" in evidence or "model_reasoning_effort" in evidence
    ) and any(
        pattern in evidence
        for pattern in ("invalid", "not supported", "unsupported")
    )
    return unsupported_model_option or explicit_effort_error


def is_transient_harness_failure(message: str | None, raw_output: str = "") -> bool:
    evidence = f"{message or ''}\n{raw_output}".lower()
    if is_run_configuration_failure(message, raw_output):
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
        "you've hit your session limit",
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


def run_claude_streaming_session(
    args: argparse.Namespace,
    command: list[str],
    run_dir: Path,
    task: str,
    label: str,
    timeout_seconds: float,
    attempt_number: int,
) -> dict[str, Any]:
    started = time.monotonic()
    deadline = started + timeout_seconds
    reporter = start_progress_reporter(
        run_dir,
        label,
        attempt_number,
        args.max_attempts,
        args.count,
    )
    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    input_lines: list[str] = []
    output_queue: queue.Queue[str | None] = queue.Queue()
    rounds: list[dict[str, Any]] = []
    stale_rounds = 0
    stop_reason: str | None = None
    timed_out = False
    timeout_message: str | None = None
    helper_failure: str | None = None
    last_result: dict[str, Any] | None = None
    process: subprocess.Popen[str] | None = None
    stdout_thread: threading.Thread | None = None
    stderr_thread: threading.Thread | None = None

    def read_stdout() -> None:
        try:
            if process is None or process.stdout is None:
                return
            for line in process.stdout:
                stdout_lines.append(line)
                output_queue.put(line)
        finally:
            output_queue.put(None)

    def read_stderr() -> None:
        if process is None or process.stderr is None:
            return
        for line in process.stderr:
            stderr_lines.append(line)

    def send_message(content: str) -> bool:
        nonlocal helper_failure
        payload = f"{claude_stream_message(content)}\n"
        input_lines.append(payload)
        try:
            if process is None or process.stdin is None:
                raise BrokenPipeError("Claude CLI stdin is unavailable")
            process.stdin.write(payload)
            process.stdin.flush()
            return True
        except (BrokenPipeError, OSError) as error:
            helper_failure = f"Could not send a continuation to {label}: {error}"
            return False

    def wait_for_result() -> dict[str, Any] | None:
        nonlocal timed_out, timeout_message, helper_failure
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                timeout_message = (
                    f"{label} timed out after "
                    f"{format_timeout(max(1, math.ceil(timeout_seconds)))}."
                )
                return None
            try:
                line = output_queue.get(timeout=min(0.5, remaining))
            except queue.Empty:
                if process is not None and process.poll() is not None:
                    helper_failure = (
                        f"{label} exited before returning a result for the current turn."
                    )
                    return None
                continue
            if line is None:
                helper_failure = (
                    f"{label} closed its output before returning a result for the current turn."
                )
                return None
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict) and event.get("type") == "result":
                return event

    def stop_process(force: bool = False) -> int:
        if process is None:
            return 127
        if force and process.poll() is None:
            process.terminate()
        elif process.stdin is not None and not process.stdin.closed:
            try:
                process.stdin.close()
            except OSError:
                pass
        wait_seconds = max(0.1, min(30.0, deadline - time.monotonic()))
        try:
            return process.wait(timeout=wait_seconds)
        except subprocess.TimeoutExpired:
            if process.poll() is None:
                process.terminate()
            try:
                return process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                return process.wait()

    try:
        process = subprocess.Popen(
            command,
            cwd=run_dir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=harness_environment(args, run_dir),
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        stdout_thread = threading.Thread(
            target=read_stdout,
            name="claude-stdout-reader",
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=read_stderr,
            name="claude-stderr-reader",
            daemon=True,
        )
        stdout_thread.start()
        stderr_thread.start()

        next_message = task
        for round_number in range(1, DEFAULT_CLAUDE_MAX_ROUNDS + 1):
            before = generation_progress_snapshot(run_dir)
            round_started = time.monotonic()
            round_started_at = utc_now()
            if not send_message(next_message):
                stop_reason = "harness_failed"
                break

            print(
                f"Claude continuation turn {round_number}/{DEFAULT_CLAUDE_MAX_ROUNDS} started; "
                f"{expected_sgf_count(run_dir, args.count)}/{args.count} expected SGFs present.",
                flush=True,
            )
            result_event = wait_for_result()
            if result_event is None:
                stop_reason = "timeout" if timed_out else "harness_failed"
                break
            last_result = result_event

            after = generation_progress_snapshot(run_dir)
            made_progress = after != before
            stale_rounds = 0 if made_progress else stale_rounds + 1
            queries_before = before[1]
            queries_after = after[1]
            output_limit = is_claude_output_limit_result(result_event)
            result_error = bool(
                result_event.get("is_error")
                or result_event.get("subtype") not in {None, "success"}
            )
            round_record = {
                "number": round_number,
                "attempt": attempt_number,
                "startedAt": round_started_at,
                "completedAt": utc_now(),
                "durationSeconds": round(time.monotonic() - round_started, 3),
                "outputFileCountBefore": len(before[0]),
                "outputFileCountAfter": len(after[0]),
                "originalityQueriesBefore": queries_before,
                "originalityQueriesAfter": queries_after,
                "progressMade": made_progress,
                "consecutiveStaleRounds": stale_rounds,
                "resultSubtype": result_event.get("subtype"),
                "resultError": result_error,
                "outputLimitBoundary": output_limit,
            }
            rounds.append(round_record)
            present_count = expected_sgf_count(run_dir, args.count)
            boundary = " (output-token boundary)" if output_limit else ""
            progress_detail = (
                "progress recorded"
                if made_progress
                else (
                    "no file or query progress "
                    f"({stale_rounds}/{DEFAULT_CLAUDE_STALE_ROUND_LIMIT} stale)"
                )
            )
            print(
                f"Claude continuation turn {round_number}/{DEFAULT_CLAUDE_MAX_ROUNDS} "
                f"finished{boundary}; {present_count}/{args.count} expected SGFs are present; "
                f"{progress_detail}.",
                flush=True,
            )

            if present_count >= args.count:
                stop_reason = "outputs_complete"
                break
            if result_error and not output_limit:
                helper_failure = event_message(result_event) or str(result_event.get("result") or "")
                stop_reason = "harness_failed"
                break
            if stale_rounds >= DEFAULT_CLAUDE_STALE_ROUND_LIMIT:
                stop_reason = "stale"
                break
            if round_number >= DEFAULT_CLAUDE_MAX_ROUNDS:
                stop_reason = "max_rounds"
                break
            next_message = claude_continuation_task(
                run_dir,
                args.count,
                round_number + 1,
                DEFAULT_CLAUDE_MAX_ROUNDS,
                result_event,
                consecutive_stale_rounds=stale_rounds,
            )

        process_exit_code = stop_process(force=timed_out)
    except OSError as error:
        helper_failure = f"Could not launch {label}: {error}"
        process_exit_code = 127
        stop_reason = "harness_failed"
    finally:
        stop_progress_reporter(reporter)
        if process is not None and process.poll() is None:
            process_exit_code = stop_process(force=True)
        if stdout_thread is not None:
            stdout_thread.join(timeout=2)
        if stderr_thread is not None:
            stderr_thread.join(timeout=2)
        if process is not None:
            for stream in (process.stdout, process.stderr):
                if stream is not None and not stream.closed:
                    stream.close()

    if timeout_message:
        stderr_lines.append(f"{timeout_message}\n")
    elif helper_failure:
        stderr_lines.append(f"{helper_failure.rstrip()}\n")

    process_exit_code = int(process_exit_code)
    exit_code = 124 if timed_out else process_exit_code
    if (
        exit_code
        and stop_reason in {"outputs_complete", "max_rounds", "stale"}
        and last_result is not None
        and is_claude_output_limit_result(last_result)
    ):
        # The CLI reports an output boundary with a nonzero process status. In
        # streaming mode that boundary is a continuation signal; if the runner's
        # own completion policy has been satisfied, it is not a harness failure.
        exit_code = 0
    if stop_reason == "harness_failed" and exit_code == 0:
        exit_code = 1

    return {
        "stdout": "".join(stdout_lines),
        "stderr": "".join(stderr_lines),
        "input": "".join(input_lines),
        "exitCode": exit_code,
        "processExitCode": process_exit_code,
        "timedOut": timed_out,
        "timeoutMessage": timeout_message,
        "failureMessage": timeout_message or helper_failure,
        "durationSeconds": round(time.monotonic() - started, 3),
        "rounds": rounds,
        "roundStopReason": stop_reason or "harness_failed",
    }


def run_harness_once(
    args: argparse.Namespace,
    command: list[str],
    run_dir: Path,
    task: str,
    label: str,
    timeout_seconds: float,
    attempt_number: int,
) -> dict[str, Any]:
    if args.harness == "claude":
        return run_claude_streaming_session(
            args,
            command,
            run_dir,
            task,
            label,
            timeout_seconds,
            attempt_number,
        )

    started = time.monotonic()
    reporter = start_progress_reporter(
        run_dir,
        label,
        attempt_number,
        args.max_attempts,
        args.count,
    )
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
    finally:
        stop_progress_reporter(reporter)

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


def wait_for_review_site(
    url: str,
    process: subprocess.Popen[Any],
    timeout: float = DEFAULT_REVIEW_STARTUP_TIMEOUT_SECONDS,
    request_timeout: float = REVIEW_PROBE_REQUEST_TIMEOUT_SECONDS,
    windows_runtime: bool = False,
) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        remaining = deadline - time.monotonic()
        probe_timeout = max(0.1, min(request_timeout, remaining))
        if windows_runtime:
            curl = shutil.which("curl.exe")
            if not curl:
                return False
            try:
                probe = subprocess.run(
                    [
                        curl,
                        "--noproxy",
                        "*",
                        "--silent",
                        "--output",
                        "NUL",
                        "--write-out",
                        "%{http_code}",
                        "--max-time",
                        str(max(1, math.ceil(probe_timeout))),
                        url,
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=probe_timeout + 2,
                )
                status = int(probe.stdout.strip() or "0")
                if 100 <= status < 500:
                    return True
            except (OSError, subprocess.TimeoutExpired, ValueError):
                pass
        else:
            try:
                with urllib.request.urlopen(url, timeout=probe_timeout) as response:
                    if response.status < 500:
                        return True
            except (OSError, urllib.error.URLError):
                pass
        time.sleep(0.25)
    return False


def capture_terminal_state() -> tuple[int, list[Any]] | None:
    if os.name == "nt" or not sys.stdin.isatty():
        return None
    try:
        import termios

        descriptor = sys.stdin.fileno()
        return descriptor, termios.tcgetattr(descriptor)
    except (ImportError, OSError, ValueError):
        return None


def restore_terminal_state(state: tuple[int, list[Any]] | None) -> None:
    if state is None:
        return
    try:
        import termios

        descriptor, attributes = state
        termios.tcsetattr(descriptor, termios.TCSANOW, attributes)
    except (ImportError, OSError, ValueError):
        pass


def launch_review_site(command: list[str]) -> subprocess.Popen[Any]:
    # The dev server must not inherit the operator's terminal input. Vite can
    # otherwise enable raw mode after startup, preventing Python from receiving
    # the Ctrl+C that is supposed to end the review session.
    return subprocess.Popen(command, cwd=PROJECT_ROOT, stdin=subprocess.DEVNULL)


def open_review_url(url: str) -> bool:
    try:
        if os.name == "nt":
            os.startfile(url)  # type: ignore[attr-defined]
            return True
        if is_wsl():
            if viewer := shutil.which("wslview"):
                return subprocess.run([viewer, url], check=False).returncode == 0
            if handler := shutil.which("rundll32.exe"):
                return (
                    subprocess.run(
                        [handler, "url.dll,FileProtocolHandler", url],
                        check=False,
                    ).returncode
                    == 0
                )
            return False
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
    manifest = {
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
    if args.harness == "claude":
        manifest["artifacts"]["harnessInput"] = "logs/claude-input.jsonl"
        manifest["harness"]["retryPolicy"].update(
            {
                "pauseForSessionLimit": True,
                "sessionResetGraceSeconds": DEFAULT_CLAUDE_SESSION_RESET_GRACE_SECONDS,
                "sessionLimitConsumesAttempt": False,
            }
        )
        manifest["harness"].update(
            {
                "sessionLimitPauseCount": 0,
                "sessionLimitPauseSeconds": 0,
            }
        )
    if args.harness in {"claude", "grok", "opencode"}:
        max_rounds = {
            "claude": DEFAULT_CLAUDE_MAX_ROUNDS,
            "grok": DEFAULT_GROK_MAX_ROUNDS,
            "opencode": DEFAULT_OPENCODE_MAX_ROUNDS,
        }[args.harness]
        round_policy: dict[str, Any] = {
            "maxRounds": max_rounds,
            "stopWhenExpectedOutputsExist": True,
        }
        if args.harness == "claude":
            round_policy.update(
                {
                    "sameSession": True,
                    "staleRoundLimit": DEFAULT_CLAUDE_STALE_ROUND_LIMIT,
                }
            )
        elif args.harness == "grok":
            round_policy.update(
                {
                    "sameSession": True,
                    "staleRoundLimit": DEFAULT_GROK_STALE_ROUND_LIMIT,
                }
            )
        manifest["harness"].update(
            {
                "roundPolicy": round_policy,
                "roundsCompleted": 0,
                "roundStopReason": None,
                "rounds": [],
            }
        )
        if args.harness == "claude":
            manifest["harness"]["outputTokenCeiling"] = CLAUDE_OUTPUT_TOKEN_MAX
        elif args.harness == "opencode":
            manifest["harness"]["outputTokenCeiling"] = OPENCODE_OUTPUT_TOKEN_MAX
    return manifest


def harness_executable(args: argparse.Namespace) -> str:
    if args.harness == "claude":
        return args.claude or os.environ.get("CLAUDE_CLI") or command_name("claude")
    if args.harness == "grok":
        return args.grok or os.environ.get("GROK_CLI") or command_name("grok")
    if args.harness == "opencode":
        return args.opencode or os.environ.get("OPENCODE_CLI") or command_name("opencode")
    return args.codex or os.environ.get("CODEX_CLI") or command_name("codex")


def harness_environment(args: argparse.Namespace, run_dir: Path) -> dict[str, str] | None:
    if args.harness == "claude":
        environment = os.environ.copy()
        environment["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = str(CLAUDE_OUTPUT_TOKEN_MAX)
        return environment
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
            "OPENCODE_EXPERIMENTAL_OUTPUT_TOKEN_MAX": str(OPENCODE_OUTPUT_TOKEN_MAX),
        }
    )
    return environment


def build_harness_command(
    args: argparse.Namespace,
    run_dir: Path,
    executable: str,
    *,
    grok_prompt_file: Path | None = None,
    grok_continue: bool = False,
) -> list[str]:
    if args.harness == "claude":
        file_tools = "Read,Write,Edit,Glob,Grep"
        command = [
            executable,
            "--safe-mode",
            "--print",
            "--input-format",
            "stream-json",
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
        ]
        if grok_continue:
            command.append("--continue")
        command.extend(
            [
                "--prompt-file",
                str(grok_prompt_file or run_dir / "inputs" / "task.md"),
                "--verbatim",
                "--output-format",
                "streaming-json",
                "--always-approve",
                # Grok 1.0.0 under WSL can block its own inference transport under
                # `strict`; `workspace` retains write confinement while the deny
                # rules below block shell, web, and MCP access.
                "--sandbox",
                "workspace",
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
        )
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


def _run_command(args: argparse.Namespace) -> int:
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
        model_error = opencode_model_validation_error(executable, args.model)
        if model_error:
            print(f"error: {model_error}", file=sys.stderr)
            print("No model was invoked, and no run was saved.", file=sys.stderr)
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
    if args.harness == "claude":
        print(
            "Claude continuation turns: up to "
            f"{DEFAULT_CLAUDE_MAX_ROUNDS} in one live session, stopping when all "
            f"{args.count} expected SGFs exist or after "
            f"{DEFAULT_CLAUDE_STALE_ROUND_LIMIT} turns without file or query progress."
        )
        print(
            "Claude per-response output ceiling: "
            f"{CLAUDE_OUTPUT_TOKEN_MAX:,} tokens"
        )
        print(
            "Claude session-limit policy: pause until the reported reset time plus "
            f"{format_elapsed(DEFAULT_CLAUDE_SESSION_RESET_GRACE_SECONDS)}, preserve "
            "partial SGFs, and resume without consuming a transient retry attempt."
        )
    if args.harness == "opencode":
        print(
            "OpenCode generation rounds: up to "
            f"{DEFAULT_OPENCODE_MAX_ROUNDS}, stopping when all {args.count} expected SGFs exist."
        )
        print(
            "OpenCode per-call output ceiling: "
            f"{OPENCODE_OUTPUT_TOKEN_MAX:,} tokens"
        )
    if args.harness == "grok":
        print(
            "Grok continuation rounds: up to "
            f"{DEFAULT_GROK_MAX_ROUNDS} in the same saved session, stopping when all "
            f"{args.count} expected SGFs exist or after "
            f"{DEFAULT_GROK_STALE_ROUND_LIMIT} rounds without file or query progress."
        )
        print(
            "Grok output-token truncation policy: preserve the run directory and resume "
            "the saved session in the next round."
        )
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
        retry_scope = (
            " per generation round"
            if args.harness in {"grok", "opencode"}
            else ""
        )
        print(
            f"Transient retry policy: up to {args.max_attempts} attempts{retry_scope}; "
            f"backoff delays {', '.join(f'{delay}s' for delay in retry_delays)} "
            f"({format_elapsed(sum(retry_delays))} maximum wait)."
        )
    else:
        print("Transient retry policy: disabled (one attempt).")
    print(
        "Progress updates every "
        f"{format_elapsed(DEFAULT_PROGRESS_INTERVAL_SECONDS)} while the model runs; "
        "they include elapsed time, generated SGFs, and originality queries when enabled.",
        flush=True,
    )
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
    total_session_pause_seconds = 0
    session_limit_pause_count = 0
    max_rounds = {
        "grok": DEFAULT_GROK_MAX_ROUNDS,
        "opencode": DEFAULT_OPENCODE_MAX_ROUNDS,
    }.get(args.harness, 1)
    rounds_completed = 0
    round_stop_reason: str | None = None
    invocation_number = 0
    accepted_stdout_chunks: list[str] = []
    accepted_stderr_chunks: list[str] = []
    accepted_input_chunks: list[str] = []
    last_final_message: str | None = None
    claude_round_records: list[dict[str, Any]] = []
    claude_round_stop_reason: str | None = None
    grok_round_records: list[dict[str, Any]] = []
    grok_stale_rounds = 0
    event_parsers = {
        "codex": parse_codex_events,
        "claude": parse_claude_events,
        "grok": parse_grok_events,
        "opencode": parse_opencode_events,
    }

    stop_model_phase = False
    for round_number in range(1, max_rounds + 1):
        if (
            args.harness in {"grok", "opencode"}
            and expected_sgf_count(run_dir, args.count) >= args.count
        ):
            round_stop_reason = "outputs_complete"
            break

        if args.harness == "opencode":
            round_task = opencode_round_task(
                task,
                run_dir,
                args.count,
                round_number,
                max_rounds,
            )
        elif args.harness == "grok":
            round_task = grok_round_task(
                task,
                run_dir,
                args.count,
                round_number,
                max_rounds,
                grok_stale_rounds,
            )
        else:
            round_task = task
        round_label = (
            f"{label} round {round_number}/{max_rounds}"
            if args.harness in {"grok", "opencode"}
            else label
        )
        if args.harness == "opencode":
            print(
                f"Starting OpenCode generation round {round_number}/{max_rounds}; "
                f"{expected_sgf_count(run_dir, args.count)}/{args.count} expected SGFs present.",
                flush=True,
            )
        elif args.harness == "grok":
            print(
                f"Starting Grok continuation round {round_number}/{max_rounds}; "
                f"{expected_sgf_count(run_dir, args.count)}/{args.count} expected SGFs present.",
                flush=True,
            )

        grok_round_before = (
            generation_progress_snapshot(run_dir)
            if args.harness == "grok"
            else None
        )
        grok_round_started = time.monotonic()
        grok_round_started_at = utc_now()

        round_completed = False
        round_attempt = 1
        resume_after_session_limit = False
        while round_attempt <= args.max_attempts:
            remaining_timeout = args.timeout - (time.monotonic() - started)
            if remaining_timeout <= 0:
                timed_out = True
                exit_code = 124
                timeout_message = (
                    f"{label} exhausted the overall execution timeout of "
                    f"{format_timeout(args.timeout)}."
                )
                stderr = timeout_message
                accepted_stderr_chunks.append(stderr)
                round_stop_reason = "timeout"
                stop_model_phase = True
                break

            invocation_number += 1
            if args.harness == "opencode":
                attempt_description = (
                    f"Starting round attempt {round_attempt}/{args.max_attempts} "
                    f"for OpenCode round {round_number}/{max_rounds}…"
                )
            elif args.harness == "grok":
                attempt_description = (
                    f"Starting round attempt {round_attempt}/{args.max_attempts} "
                    f"for Grok continuation round {round_number}/{max_rounds}…"
                )
            elif args.harness == "claude" and resume_after_session_limit:
                attempt_description = (
                    f"Resuming model attempt {round_attempt}/{args.max_attempts} after "
                    "the Claude session reset…"
                )
            else:
                attempt_description = (
                    f"Starting model attempt {round_attempt}/{args.max_attempts}…"
                )
            print(attempt_description, flush=True)

            attempt_started_at = utc_now()
            invocation_task = (
                claude_session_resume_task(round_task, run_dir, args.count)
                if args.harness == "claude" and resume_after_session_limit
                else round_task
            )
            resume_after_session_limit = False
            invocation_command = command
            grok_input_path: str | None = None
            if args.harness == "grok":
                if round_number == 1:
                    grok_prompt_file = run_dir / "inputs" / "task.md"
                else:
                    grok_attempt_dir = (
                        run_dir
                        / "logs"
                        / "attempts"
                        / f"attempt-{invocation_number:02d}"
                    )
                    grok_attempt_dir.mkdir(parents=True, exist_ok=True)
                    grok_prompt_file = grok_attempt_dir / "grok-prompt.md"
                    grok_prompt_file.write_text(round_task, encoding="utf-8")
                grok_input_path = grok_prompt_file.relative_to(run_dir).as_posix()
                invocation_command = build_harness_command(
                    args,
                    run_dir,
                    executable,
                    grok_prompt_file=grok_prompt_file,
                    grok_continue=round_number > 1,
                )
            result = run_harness_once(
                args,
                invocation_command,
                run_dir,
                invocation_task,
                round_label,
                remaining_timeout,
                round_attempt,
            )
            stdout = result["stdout"]
            stderr = result["stderr"]
            exit_code = result["exitCode"]
            timed_out = result["timedOut"]
            timeout_message = result["timeoutMessage"]
            attempt_events = event_parsers[args.harness](stdout)
            result_failure = result.get("failureMessage")
            if isinstance(result_failure, str) and result_failure.strip():
                attempt_events["failureMessage"] = result_failure.strip()
            if timeout_message and not attempt_events.get("failureMessage"):
                attempt_events["failureMessage"] = timeout_message
            attempt_final_message = attempt_events.pop("finalMessage", None)
            failure_message = attempt_events.get("failureMessage")
            raw_output = f"{stdout}\n{stderr}"
            claude_session_limited = bool(
                exit_code
                and args.harness == "claude"
                and is_claude_session_limit_failure(failure_message, raw_output)
            )
            claude_session_resume_at = (
                claude_session_limit_reset_at(failure_message, raw_output)
                if claude_session_limited
                else None
            )
            grok_output_limited = bool(
                exit_code
                and args.harness == "grok"
                and is_grok_output_limit_failure(failure_message, raw_output)
            )
            configuration_rejected = bool(
                exit_code and is_run_configuration_failure(failure_message, raw_output)
            )
            retryable = bool(
                exit_code
                and not timed_out
                and not configuration_rejected
                and not grok_output_limited
                and (
                    claude_session_limited
                    or is_transient_harness_failure(failure_message, raw_output)
                )
            )
            failure_detail = (
                compact_failure(failure_message, stdout, stderr, exit_code)
                if exit_code is not None and exit_code != 0
                else None
            )
            attempt_dir, attempt_stdout, attempt_stderr = write_harness_attempt_logs(
                run_dir,
                args.harness,
                invocation_number,
                stdout,
                stderr,
            )
            attempt_input: str | None = None
            attempt_input_path: str | None = None
            if args.harness == "claude":
                raw_input = result.get("input")
                attempt_input = raw_input if isinstance(raw_input, str) else ""
                input_path = attempt_dir / "claude-input.jsonl"
                input_path.write_text(attempt_input, encoding="utf-8")
                attempt_input_path = input_path.relative_to(run_dir).as_posix()
            elif args.harness == "grok":
                attempt_input_path = grok_input_path
            output_file_count = generated_sgf_count(run_dir)
            attempt_record: dict[str, Any] = {
                "number": invocation_number,
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
            if args.harness == "claude":
                attempt_rounds = result.get("rounds")
                if not isinstance(attempt_rounds, list):
                    attempt_rounds = []
                attempt_record.update(
                    {
                        "input": attempt_input_path,
                        "processExitCode": result.get("processExitCode", exit_code),
                        "roundStopReason": result.get("roundStopReason"),
                        "rounds": attempt_rounds,
                    }
                )
                claude_round_records.extend(attempt_rounds)
                claude_round_stop_reason = result.get("roundStopReason")
            if args.harness in {"grok", "opencode"}:
                attempt_record.update(
                    {
                        "roundNumber": round_number,
                        "attemptInRound": round_attempt,
                    }
                )
            if args.harness == "grok":
                attempt_record.update(
                    {
                        "input": attempt_input_path,
                        "processExitCode": exit_code,
                        "outputLimitBoundary": grok_output_limited,
                    }
                )

            if claude_session_limited and claude_session_resume_at is not None:
                pause_seconds = claude_session_limit_pause_seconds(claude_session_resume_at)
                remaining_after_attempt = args.timeout - (time.monotonic() - started)
                if pause_seconds < remaining_after_attempt:
                    attempt_record.update(
                        {
                            "outcome": "session_limit_pause",
                            "sessionLimitResumeAt": claude_session_resume_at.isoformat(),
                            "sessionLimitPauseSeconds": pause_seconds,
                        }
                    )
                    attempt_records.append(attempt_record)
                    manifest["harness"]["attempts"] = attempt_records
                    write_json(manifest_path, manifest)
                    print(
                        "Claude reached its session limit after "
                        f"{format_elapsed(result['durationSeconds'])}; "
                        f"{output_file_count}/{args.count} SGFs and the shared originality "
                        "state will remain in place."
                    )
                    print(
                        "Pausing until "
                        f"{format_claude_session_reset(claude_session_resume_at)} "
                        f"({format_elapsed(pause_seconds)}). This does not consume transient "
                        f"retry attempt {round_attempt}/{args.max_attempts}."
                    )
                    waited = wait_for_claude_session_reset(
                        run_dir,
                        args.count,
                        claude_session_resume_at,
                    )
                    total_session_pause_seconds += waited
                    session_limit_pause_count += 1
                    manifest["harness"].update(
                        {
                            "sessionLimitPauseCount": session_limit_pause_count,
                            "sessionLimitPauseSeconds": total_session_pause_seconds,
                        }
                    )
                    write_json(manifest_path, manifest)
                    resume_after_session_limit = True
                    continue
                attempt_record["retrySkippedReason"] = (
                    "The reported Claude session reset occurs after the remaining "
                    "execution-time budget."
                )
            elif claude_session_limited:
                attempt_record["retrySkippedReason"] = (
                    "The Claude session-limit reset time could not be parsed."
                )

            can_retry = (
                retryable
                and not claude_session_limited
                and round_attempt < args.max_attempts
            )
            if can_retry:
                delay = retry_delay_seconds(
                    round_attempt,
                    args.retry_base_delay,
                    args.retry_max_delay,
                )
                remaining_after_attempt = args.timeout - (time.monotonic() - started)
                if delay < remaining_after_attempt:
                    attempt_record["outcome"] = "transient_failure"
                    attempt_record["retryDelaySeconds"] = delay
                    # Outer generation rounds deliberately share their workspace.
                    # Preserve partial SGFs so retries and later rounds can continue them.
                    if args.harness not in {"grok", "opencode"}:
                        archived_outputs = archive_retry_outputs(run_dir, attempt_dir)
                        if archived_outputs:
                            attempt_record["archivedOutputs"] = archived_outputs
                    attempt_records.append(attempt_record)
                    manifest["harness"]["attempts"] = attempt_records
                    write_json(manifest_path, manifest)
                    prefix = (
                        f"Round {round_number}/{max_rounds} attempt"
                        if args.harness in {"grok", "opencode"}
                        else "Attempt"
                    )
                    print(
                        f"{prefix} {round_attempt}/{args.max_attempts} failed after "
                        f"{format_elapsed(result['durationSeconds'])} with a transient error: "
                        f"{failure_detail}"
                    )
                    print(
                        f"Retrying in {format_elapsed(delay)} "
                        f"(attempt {round_attempt + 1}/{args.max_attempts})."
                    )
                    time.sleep(delay)
                    total_backoff_seconds += delay
                    round_attempt += 1
                    continue
                attempt_record["retrySkippedReason"] = (
                    "The remaining execution-time budget was too short for the next backoff delay."
                )

            if grok_output_limited:
                attempt_record["outcome"] = "output_limit_boundary"
            elif exit_code == 0:
                attempt_record["outcome"] = "success"
            elif configuration_rejected:
                attempt_record["outcome"] = "configuration_rejected"
            elif timed_out:
                attempt_record["outcome"] = "timeout"
            elif retryable:
                attempt_record["outcome"] = "transient_failure"
            else:
                attempt_record["outcome"] = "permanent_failure"
            attempt_records.append(attempt_record)
            manifest["harness"]["attempts"] = attempt_records

            accepted_stdout_chunks.append(stdout)
            accepted_stderr_chunks.append(stderr)
            if attempt_input:
                accepted_input_chunks.append(attempt_input)
            if attempt_final_message:
                last_final_message = attempt_final_message
            if exit_code == 0 or grok_output_limited:
                round_completed = True
                rounds_completed += 1
                if args.harness in {"grok", "opencode"}:
                    manifest["harness"]["roundsCompleted"] = rounds_completed
            write_json(manifest_path, manifest)
            break

        if stop_model_phase:
            break
        if not round_completed:
            round_stop_reason = "timeout" if timed_out else "harness_failed"
            break
        if args.harness not in {"grok", "opencode"}:
            round_stop_reason = "single_round"
            break

        present_count = expected_sgf_count(run_dir, args.count)
        if args.harness == "grok":
            grok_round_after = generation_progress_snapshot(run_dir)
            grok_made_progress = grok_round_after != grok_round_before
            grok_stale_rounds = 0 if grok_made_progress else grok_stale_rounds + 1
            grok_round_record = {
                "number": round_number,
                "attempt": round_attempt,
                "startedAt": grok_round_started_at,
                "completedAt": utc_now(),
                "durationSeconds": round(time.monotonic() - grok_round_started, 3),
                "outputFileCountBefore": len(grok_round_before[0]),
                "outputFileCountAfter": len(grok_round_after[0]),
                "originalityQueriesBefore": grok_round_before[1],
                "originalityQueriesAfter": grok_round_after[1],
                "progressMade": grok_made_progress,
                "consecutiveStaleRounds": grok_stale_rounds,
                "resultSubtype": attempt_events.get("resultSubtype"),
                "resultError": bool(exit_code),
                "outputLimitBoundary": grok_output_limited,
            }
            grok_round_records.append(grok_round_record)
            boundary = " (output-token boundary)" if grok_output_limited else ""
            progress_detail = (
                "progress recorded"
                if grok_made_progress
                else (
                    "no file or query progress "
                    f"({grok_stale_rounds}/{DEFAULT_GROK_STALE_ROUND_LIMIT} stale)"
                )
            )
            print(
                f"Grok continuation round {round_number}/{max_rounds} finished{boundary}; "
                f"{present_count}/{args.count} expected SGFs are present; {progress_detail}.",
                flush=True,
            )
            if present_count >= args.count:
                round_stop_reason = "outputs_complete"
                break
            if grok_stale_rounds >= DEFAULT_GROK_STALE_ROUND_LIMIT:
                round_stop_reason = "stale"
                break
            if round_number >= max_rounds:
                round_stop_reason = "max_rounds"
                break
            print("Expected outputs are still missing; resuming the saved Grok session.")
            continue

        print(
            f"OpenCode round {round_number}/{max_rounds} finished; "
            f"{present_count}/{args.count} expected SGFs are present.",
            flush=True,
        )
        if present_count >= args.count:
            round_stop_reason = "outputs_complete"
            break
        if round_number >= max_rounds:
            round_stop_reason = "max_rounds"
            break
        print("Expected outputs are still missing; starting a fresh OpenCode round.")

    if args.harness in {"grok", "opencode"}:
        round_stop_reason = round_stop_reason or "max_rounds"
        manifest["harness"].update(
            {
                "roundsCompleted": rounds_completed,
                "roundStopReason": round_stop_reason,
            }
        )
        if args.harness == "grok":
            manifest["harness"]["rounds"] = grok_round_records
            if round_stop_reason in {"outputs_complete", "max_rounds", "stale"}:
                # Grok reports an output-token boundary as process exit 1. Once
                # the runner's continuation policy reaches its own terminal
                # condition, that boundary is not a harness failure.
                exit_code = 0
        write_json(manifest_path, manifest)
    elif args.harness == "claude":
        manifest["harness"].update(
            {
                "roundsCompleted": len(claude_round_records),
                "roundStopReason": claude_round_stop_reason or "harness_failed",
                "rounds": claude_round_records,
                "sessionLimitPauseCount": session_limit_pause_count,
                "sessionLimitPauseSeconds": total_session_pause_seconds,
            }
        )
        write_json(manifest_path, manifest)

    stdout = concatenate_harness_output(accepted_stdout_chunks)
    stderr = concatenate_harness_output(accepted_stderr_chunks)
    events = event_parsers[args.harness](stdout)
    parsed_final_message = events.pop("finalMessage", None)
    events.pop("resultSubtype", None)
    final_message = last_final_message or parsed_final_message
    if (
        args.harness == "claude"
        and not exit_code
        and claude_round_records
        and claude_round_records[-1].get("outputLimitBoundary") is True
    ):
        events["failureMessage"] = None
    if args.harness == "grok" and not exit_code:
        events["failureMessage"] = None
    if timeout_message and not events.get("failureMessage"):
        events["failureMessage"] = timeout_message
    if exit_code and attempt_records and attempt_records[-1].get("failureMessage"):
        events["failureMessage"] = attempt_records[-1]["failureMessage"]

    if originality_broker is not None:
        broker_exit_code = stop_originality_broker(run_dir, originality_broker)
        if broker_exit_code:
            broker_stderr_path = run_dir / "logs" / "originality-broker-stderr.txt"
            broker_error = (
                broker_stderr_path.read_text(encoding="utf-8").strip()
                if broker_stderr_path.exists()
                else ""
            )
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
    print(
        f"Model phase finished in {format_elapsed(duration)}; "
        f"{expected_sgf_count(run_dir, args.count)}/{args.count} expected SGF files are present.",
        flush=True,
    )
    if session_limit_pause_count:
        print(
            "Claude session-limit handling paused "
            f"{format_elapsed(total_session_pause_seconds)} across "
            f"{session_limit_pause_count} "
            f"{'reset' if session_limit_pause_count == 1 else 'resets'}; "
            "these pauses did not consume transient retry attempts."
        )
    (run_dir / manifest["artifacts"]["stdout"]).write_text(stdout, encoding="utf-8")
    (run_dir / manifest["artifacts"]["stderr"]).write_text(stderr, encoding="utf-8")
    harness_input_path = manifest["artifacts"].get("harnessInput")
    if isinstance(harness_input_path, str):
        (run_dir / harness_input_path).write_text(
            concatenate_harness_output(accepted_input_chunks),
            encoding="utf-8",
        )
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
    if args.harness == "grok" and not exit_code:
        if round_stop_reason == "outputs_complete":
            print(
                f"Grok created all {args.count} expected SGFs in "
                f"{rounds_completed} "
                f"{'round' if rounds_completed == 1 else 'rounds'}."
            )
        elif round_stop_reason == "max_rounds":
            print(
                f"Grok reached the {max_rounds}-round cap with "
                f"{expected_sgf_count(run_dir, args.count)}/{args.count} expected SGFs present.",
                file=sys.stderr,
            )
        elif round_stop_reason == "stale":
            print(
                "Grok stopped after "
                f"{DEFAULT_GROK_STALE_ROUND_LIMIT} consecutive continuation rounds without "
                "file or originality-query progress.",
                file=sys.stderr,
            )
        if total_backoff_seconds:
            print(
                "Transient retries waited "
                f"{format_elapsed(total_backoff_seconds)} total across the Grok rounds."
            )
    elif args.harness == "opencode" and not exit_code:
        if round_stop_reason == "outputs_complete":
            print(
                f"OpenCode created all {args.count} expected SGFs in "
                f"{rounds_completed} {'round' if rounds_completed == 1 else 'rounds'}."
            )
        elif round_stop_reason == "max_rounds":
            print(
                f"OpenCode reached the {max_rounds}-round cap with "
                f"{expected_sgf_count(run_dir, args.count)}/{args.count} expected SGFs present.",
                file=sys.stderr,
            )
        if total_backoff_seconds:
            print(
                "Transient retries waited "
                f"{format_elapsed(total_backoff_seconds)} total across the OpenCode rounds."
            )
    elif args.harness == "claude" and not exit_code:
        final_claude_round_count = (
            len(attempt_records[-1].get("rounds", [])) if attempt_records else 0
        )
        if claude_round_stop_reason == "outputs_complete":
            print(
                f"Claude created all {args.count} expected SGFs in "
                f"{final_claude_round_count} continuation "
                f"{'turn' if final_claude_round_count == 1 else 'turns'} within the successful session."
            )
        elif claude_round_stop_reason == "max_rounds":
            print(
                f"Claude reached the {DEFAULT_CLAUDE_MAX_ROUNDS}-turn cap with "
                f"{expected_sgf_count(run_dir, args.count)}/{args.count} expected SGFs present.",
                file=sys.stderr,
            )
        elif claude_round_stop_reason == "stale":
            print(
                "Claude stopped after "
                f"{DEFAULT_CLAUDE_STALE_ROUND_LIMIT} consecutive continuation turns without "
                "file or originality-query progress.",
                file=sys.stderr,
            )
    elif not exit_code and len(attempt_records) > 1:
        print(
            f"{label} succeeded on attempt {len(attempt_records)}/{args.max_attempts} "
            f"after {format_elapsed(duration)} total "
            f"({format_elapsed(total_backoff_seconds)} in backoff)."
        )
    if exit_code and is_run_configuration_failure(failure_message, f"{stdout}\n{stderr}"):
        discard_new_run(run_dir)
        detail = failure_message or f"{label} exited with status {exit_code}."
        print(
            f"Benchmark configuration for model {args.model!r} was rejected by {label}: "
            f"{detail}",
            file=sys.stderr,
        )
        print(
            "No retries were attempted because model and reasoning-effort configuration "
            "failures are permanent. No run was saved, and evaluation was not started. "
            "Check --model and --reasoning-effort, then try again.",
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
    print("Evaluating generated SGFs…", flush=True)
    evaluation_started = time.monotonic()
    evaluator = run_evaluator(run_dir, args.local_only)
    print(
        f"Evaluation finished in {format_elapsed(time.monotonic() - evaluation_started)}.",
        flush=True,
    )
    manifest = read_json(manifest_path)
    if evaluator.returncode:
        manifest["status"] = "evaluation_failed"
    elif exit_code:
        manifest["status"] = "harness_failed"
    else:
        manifest["status"] = "completed"
    manifest["completedAt"] = utc_now()
    write_json(manifest_path, manifest)

    print("Rebuilding the web index…", flush=True)
    index_started = time.monotonic()
    indexed = build_run_index()
    print(
        f"Web index rebuild finished in {format_elapsed(time.monotonic() - index_started)}.",
        flush=True,
    )
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


def run_command(args: argparse.Namespace) -> int:
    started = time.monotonic()
    try:
        return _run_command(args)
    finally:
        print(
            f"Benchmark finished in {format_elapsed(time.monotonic() - started)}.",
            flush=True,
        )


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
    terminal_state = capture_terminal_state()

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
        process = launch_review_site(command)
        site_root = f"http://127.0.0.1:{web_port}"
        # Probe the lightweight root route. Probing /runs during a cold Vite start can
        # repeatedly abort its first SSR compilation before the review route is ready.
        # Under WSL this project can use Windows node.exe for Windows node_modules. In
        # that case Vite is on Windows loopback, so probe it with Windows curl.exe.
        windows_runtime = is_wsl() and executable.lower().endswith(".exe")
        if not wait_for_review_site(site_root, process, windows_runtime=windows_runtime):
            return_code = process.poll()
            message = (
                f"The review site exited with status {return_code}."
                if return_code is not None
                else (
                    "The review site did not become ready within "
                    f"{DEFAULT_REVIEW_STARTUP_TIMEOUT_SECONDS} seconds."
                )
            )
            print(f"error: {message}", file=sys.stderr)
            return 1

        # Vite enables raw input while it starts. Python remains the session owner, so
        # restore the operator's terminal before printing instructions or waiting.
        restore_terminal_state(terminal_state)

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
        restore_terminal_state(terminal_state)


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
        help="Maximum model-phase wall-clock time in seconds (default: 43200 / 12 hours).",
    )
    run.add_argument(
        "--max-attempts",
        type=int,
        default=DEFAULT_MAX_HARNESS_ATTEMPTS,
        help=(
            "Maximum CLI attempts per harness invocation (or per Grok/OpenCode outer round) "
            "for recognized transient failures "
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
