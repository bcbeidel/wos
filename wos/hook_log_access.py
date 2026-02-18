#!/usr/bin/env python3
"""PostToolUse hook — log Read access to context files.

Receives JSON on stdin from Claude Code's PostToolUse event.
Extracts file_path, checks if it's under context/, and appends
to the utilization log via record_reference().

Must always exit 0 — a crashing hook blocks the agent.
"""

from __future__ import annotations

import json
import os
import sys


def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, OSError):
        return

    file_path = (data.get("tool_input") or {}).get("file_path", "")
    cwd = data.get("cwd", "")

    if not file_path or not cwd:
        return

    # Convert absolute path to project-relative
    try:
        rel_path = os.path.relpath(file_path, cwd)
    except ValueError:
        return

    # Only log context files
    if not rel_path.startswith("context/"):
        return

    # Lazy import to keep startup fast when filtering out non-context reads
    from wos.utilization import record_reference

    context = data.get("session_id", "agent")
    record_reference(cwd, rel_path, context=context)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # Never crash — always exit 0
