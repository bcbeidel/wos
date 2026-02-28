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
import json
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

    manifest_p = sub.add_parser(
        "generate-manifest", help="Generate blinding manifest",
    )
    manifest_p.add_argument(
        "--conditions",
        required=True,
        help=(
            "Comma-separated label=description pairs "
            "(e.g., 'gpt-4=GPT-4,claude=Claude')"
        ),
    )
    manifest_p.add_argument(
        "--seed", type=int, default=None,
        help="Randomization seed (default: random)",
    )

    back_p = sub.add_parser("backtrack", help="Return to an earlier phase")
    back_p.add_argument(
        "--phase",
        required=True,
        choices=[
            "design", "audit", "evaluation",
            "execution", "analysis", "publication",
        ],
        help="Phase to return to",
    )

    args = parser.parse_args()

    # Deferred imports — keeps --help fast
    from wos.experiment_state import (
        PHASE_ORDER,
        advance_phase,
        backtrack_to_phase,
        check_gate,
        current_phase,
        format_progress,
        load_state,
        new_state,
        preserve_artifacts,
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

<<<<<<< HEAD
    elif args.command == "generate-manifest":
        if not state_path.is_file():
            print("No experiment-state.json found.", file=sys.stderr)
            sys.exit(1)

        conditions = {}
        for pair in args.conditions.split(","):
            pair = pair.strip()
            if "=" not in pair:
                print(
                    "Invalid condition format: '%s'. "
                    "Use label=description." % pair,
                    file=sys.stderr,
                )
                sys.exit(1)
            label, desc = pair.split("=", 1)
            conditions[label.strip()] = desc.strip()

        from wos.experiment_state import generate_manifest

        manifest = generate_manifest(conditions, seed=args.seed)

        manifest_path = root / "evaluation" / "blinding-manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
            f.write("\n")

        print(
            "Manifest written to %s"
            % manifest_path.relative_to(root)
        )
        print("Seed: %d" % manifest["randomization_seed"])
        print("Condition mapping (DO NOT share during execution):")
        for label, info in manifest["conditions"].items():
            print("  %s -> %s" % (label, info["opaque_id"]))

    elif args.command == "backtrack":
        if not state_path.is_file():
            print("No experiment-state.json found.", file=sys.stderr)
            sys.exit(1)
        state = load_state(str(state_path))

        # Preserve artifacts for the target phase and all downstream
        all_preserved = []
        target_idx = PHASE_ORDER.index(args.phase)
        for name in PHASE_ORDER[target_idx:]:
            preserved = preserve_artifacts(str(root), name)
            all_preserved.extend(preserved)

        report = backtrack_to_phase(state, args.phase)
        save_state(state, str(state_path))

        print("Backtracked to: %s" % args.phase)
        if report["reset_phases"]:
            print("Reset phases: %s" % ", ".join(report["reset_phases"]))
        if all_preserved:
            print(
                "Preserved %d artifact(s) as .prev files" % len(all_preserved)
            )
        print()
        print(format_progress(state))


if __name__ == "__main__":
    main()
