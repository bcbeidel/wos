#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Experiment state management CLI.

Usage:
    uv run scripts/experiment_state.py --root . status
    uv run scripts/experiment_state.py --root . init \\
        --tier exploratory --title "My Experiment"
    uv run scripts/experiment_state.py --root . advance --phase design
    uv run scripts/experiment_state.py --root . check-gates [--phase audit]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure `import wos` works whether pip-installed or run from plugin cache.
_plugin_root = Path(__file__).resolve().parent.parent
if str(_plugin_root) not in sys.path:
    sys.path.insert(0, str(_plugin_root))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Experiment state management.",
    )
    parser.add_argument("--root", default=".", help="Experiment repo root")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show experiment progress")

    init_p = sub.add_parser("init", help="Initialize experiment state")
    init_p.add_argument(
        "--tier",
        required=True,
        choices=["pilot", "exploratory", "confirmatory"],
    )
    init_p.add_argument("--title", required=True)

    adv_p = sub.add_parser("advance", help="Mark a phase complete")
    adv_p.add_argument(
        "--phase",
        required=True,
        choices=[
            "design", "audit", "evaluation",
            "execution", "analysis", "publication",
        ],
    )

    gates_p = sub.add_parser("check-gates", help="Check artifact gates")
    gates_p.add_argument("--phase", help="Phase to check (default: current)")

    args = parser.parse_args()

    # Deferred imports — keeps --help fast
    from wos.experiment_state import (
        advance_phase,
        check_gate,
        current_phase,
        format_progress,
        load_state,
        new_state,
        save_state,
    )

    root = Path(args.root).resolve()
    state_path = root / "experiment-state.json"

    if args.command == "status":
        if not state_path.is_file():
            print(
                "No experiment-state.json found. Not an experiment repo.",
                file=sys.stderr,
            )
            sys.exit(1)
        state = load_state(str(state_path))
        print(format_progress(state))

    elif args.command == "init":
        state = new_state(tier=args.tier, title=args.title)
        save_state(state, str(state_path))
        print(format_progress(state))

    elif args.command == "advance":
        if not state_path.is_file():
            print("No experiment-state.json found.", file=sys.stderr)
            sys.exit(1)
        state = load_state(str(state_path))
        advance_phase(state, args.phase)
        save_state(state, str(state_path))
        print(format_progress(state))

    elif args.command == "check-gates":
        if not state_path.is_file():
            print("No experiment-state.json found.", file=sys.stderr)
            sys.exit(1)
        state = load_state(str(state_path))
        phase = args.phase or current_phase(state)
        if not phase:
            print("All phases complete.")
            return
        missing = check_gate(str(root), phase)
        if missing:
            print(f"Missing for {phase}: {', '.join(missing)}")
            sys.exit(1)
        else:
            print(f"Gates satisfied for {phase}.")


if __name__ == "__main__":
    main()
