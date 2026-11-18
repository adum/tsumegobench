#!/usr/bin/env python3
"""Antigravity PreToolUse hook copied into each run's protected inputs."""

import json
import sys
from pathlib import Path


READ_PATHS = {
    "read_file": "Path",
    "view_file": "AbsolutePath",
    "sed_file": "AbsolutePath",
    "list_dir": "DirectoryPath",
    "find_by_name": "SearchDirectory",
    "grep_search": "SearchPath",
}
WRITE_PATHS = {
    "write_file": "Path",
    "write_to_file": "TargetFile",
    "replace_file_content": "TargetFile",
    "multi_replace_file_content": "TargetFile",
}
LOCAL_TOOLS = {"run_command", "command_status", "send_command_input", "wait", "wait_5_seconds", "finish"}
PROTECTED = (
    "inputs", "logs", "evaluation", "run.json", ".agents",
    "originality/results", "originality/summary.json", "originality/ready.json", "originality/stop",
)


def decision(payload: dict, root: Path) -> dict:
    root = root.resolve()
    call = payload.get("toolCall", {})
    name = call.get("name")
    args = call.get("args", {})
    if not isinstance(args, dict):
        return {"decision": "deny", "reason": "Invalid tool arguments."}
    if name not in READ_PATHS and name not in WRITE_PATHS and name not in LOCAL_TOOLS:
        return {"decision": "deny", "reason": "This benchmark allows only local file and sandboxed command tools."}
    key = READ_PATHS.get(name)
    if name in WRITE_PATHS:
        key = WRITE_PATHS[name]
    elif name == "run_command":
        key = "Cwd"
        if any(value and ("unsandbox" in field.lower() or "escape" in field.lower())
               for field, value in args.items()):
            return {"decision": "deny", "reason": "Commands must stay in the sandbox."}
    if key:
        value = args.get(key, str(root) if name == "run_command" else None)
        if not isinstance(value, str) or not value:
            return {"decision": "deny", "reason": "An explicit workspace path is required."}
        path = Path(value).expanduser()
        path = (root / path).resolve() if not path.is_absolute() else path.resolve()
        if not path.is_relative_to(root):
            return {"decision": "deny", "reason": "File access is limited to this run directory."}
        if name in WRITE_PATHS and any(path == root / part or path.is_relative_to(root / part) for part in PROTECTED):
            return {"decision": "deny", "reason": "Benchmark inputs and runner records are read-only."}
        if name == "run_command":
            return {"decision": "allow", "overwrite": {"Cwd": str(path)}}
    # 'allow' defers to the CLI's permissions; it does not auto-approve commands.
    return {"decision": "allow"}


if __name__ == "__main__":
    try:
        result = decision(json.load(sys.stdin), Path(__file__).resolve().parent.parent)
    except (OSError, ValueError, TypeError, AttributeError):
        result = {"decision": "deny", "reason": "Invalid benchmark tool request."}
    print(json.dumps(result))
