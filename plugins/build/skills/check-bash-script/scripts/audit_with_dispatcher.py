#!/usr/bin/env python3
"""Run check-bash-script audit via the audit-dispatcher subagent (Stage-2 pilot).

Thin wrapper around the generic orchestrator at
`plugins/build/agents/audit-dispatcher/scripts/orchestrator.py`. Defaults
`--skill-dir` to this script's parent directory so the caller only needs
to supply `--artifact-file <path>`.

Stage-2 pilot scope: this is the single-skill integration of the
audit-dispatcher subagent. The existing per-script entry points
(check_secrets.py, check_structure.py, etc.) remain unchanged — the
orchestrator runs them as part of its dispatch logic. This wrapper just
provides a convenience entry point for the dispatcher path.

Requires ANTHROPIC_API_KEY (unless --dry-run). Per-rule LLM cost estimate
on a clean bash script: 8 calls (the judgment dimensions). On a violation-
laden script: 8 + N where N is the number of distinct Tier-1 rules that
fired.

Example:
    python3 audit_with_dispatcher.py --artifact-file path/to/script.sh
    python3 audit_with_dispatcher.py --artifact-file path/to/script.sh --dry-run
    python3 audit_with_dispatcher.py --artifact-file path/to/script.sh \\
        --rules strict-mode,unquoted-variable-expansion
"""

from __future__ import annotations

import sys
from pathlib import Path

# Resolve the dispatcher orchestrator from the toolkit's agents directory.
# Walk up from this script's location to <plugin>/build, then descend into
# agents/audit-dispatcher/scripts.
_THIS_DIR = Path(__file__).resolve().parent
_PLUGIN_BUILD_DIR = _THIS_DIR.parent.parent.parent
_ORCHESTRATOR_DIR = _PLUGIN_BUILD_DIR / "agents" / "audit-dispatcher" / "scripts"

if not _ORCHESTRATOR_DIR.is_dir():
    print(
        f"error: audit-dispatcher orchestrator not found at {_ORCHESTRATOR_DIR}",
        file=sys.stderr,
    )
    sys.exit(64)

sys.path.insert(0, str(_ORCHESTRATOR_DIR))
import orchestrator  # noqa: E402

# Default skill-dir to this script's parent directory
# (plugins/build/skills/check-bash-script/).
_DEFAULT_SKILL_DIR = _THIS_DIR.parent


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    # Inject --skill-dir if the caller didn't supply one.
    if not any(a.startswith("--skill-dir") for a in argv):
        argv = ["--skill-dir", str(_DEFAULT_SKILL_DIR), *argv]
    return orchestrator.main(argv)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
