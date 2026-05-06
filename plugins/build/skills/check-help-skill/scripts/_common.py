"""JSON-emit helpers for check-bash-script detection scripts.

Every detection script (`check_*.py`, `check_*.sh` via `python3 -c`) emits
its findings as a JSON envelope matching the canonical shape documented in
`assets/output-example.json`:

    {
      "rule_id": "<rule>",
      "overall_status": "pass" | "warn" | "fail" | "inapplicable",
      "findings": [
        {
          "status": "warn" | "fail",
          "location": {"line": int, "context": str} | None,
          "reasoning": str,
          "recommended_changes": str   # REQUIRED — non-empty
        },
        ...
      ]
    }

Multi-rule scripts emit a JSON array of envelopes (one per rule_id).
Single-rule scripts emit a single envelope.

`recommended_changes` is REQUIRED on every finding. Scripts must embed
their canonical repair recipes as module-level constants — the orchestrator
does not enrich script output. This is the single-artifact-per-rule
discipline: detection AND recipe live in the same script.
"""

from __future__ import annotations

import json
import sys

_VALID_FINDING_STATUSES = ("warn", "fail")
_VALID_OVERALL_STATUSES = ("pass", "warn", "fail", "inapplicable")


def emit_json_finding(
    rule_id: str,
    status: str,
    location: dict | None,
    reasoning: str,
    recommended_changes: str,
) -> dict:
    """Build a single finding dict.

    `recommended_changes` is REQUIRED — passing an empty string raises
    ValueError. Scripts must embed concrete repair guidance.
    """
    if status not in _VALID_FINDING_STATUSES:
        raise ValueError(
            f"status must be one of {_VALID_FINDING_STATUSES}, got {status!r}"
        )
    if not recommended_changes or not recommended_changes.strip():
        raise ValueError(
            f"recommended_changes is required and must be non-empty "
            f"(rule_id={rule_id!r})"
        )
    return {
        "rule_id": rule_id,
        "status": status,
        "location": location,
        "reasoning": reasoning,
        "recommended_changes": recommended_changes,
    }


def emit_rule_envelope(
    rule_id: str,
    findings: list[dict],
    inapplicable: bool = False,
) -> dict:
    """Build a per-rule envelope; derive overall_status from findings.

    Severity ladder: fail > warn > pass. If `inapplicable=True`, returns
    overall_status='inapplicable' regardless of findings (caller is asserting
    the rule's preconditions are unmet for this artifact).
    """
    if inapplicable:
        overall_status = "inapplicable"
    elif any(f.get("status") == "fail" for f in findings):
        overall_status = "fail"
    elif any(f.get("status") == "warn" for f in findings):
        overall_status = "warn"
    else:
        overall_status = "pass"
    return {
        "rule_id": rule_id,
        "overall_status": overall_status,
        "findings": findings,
    }


def print_envelope(envelope: dict | list[dict]) -> None:
    """JSON-dump an envelope (or array of envelopes) to stdout."""
    json.dump(envelope, sys.stdout, indent=2)
    sys.stdout.write("\n")


__all__ = ["emit_json_finding", "emit_rule_envelope", "print_envelope"]
