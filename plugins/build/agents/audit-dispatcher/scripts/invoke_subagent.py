#!/usr/bin/env python3
"""Anthropic SDK wrapper for the audit-dispatcher subagent.

Invokes the parameterized audit-dispatcher (defined at
plugins/build/agents/audit-dispatcher.md) against a single (rule, artifact)
pair and returns structured findings via the `report_audit_finding` tool.

Tool-use is enforced (`tool_choice` directs the model to the tool); text-only
responses trigger one retry, then raise SubagentToolCallError.

Prompt caching: system prompt and rule body are cache_control-marked so an
N-rule audit run caches the system prompt across all invocations and the
rule body across multiple artifacts using the same rule.

Dependencies: anthropic>=0.40 (Python SDK). Install per-script:
    pip install 'anthropic>=0.40'

Example:
    python3 invoke_subagent.py \\
        --rule-file <skill-path>/references/rule-strict-mode.md \\
        --artifact-file /path/to/script.sh
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

EXIT_USAGE = 64
EXIT_TOOL_CALL_FAILURE = 70

# Resolve subagent body from <plugin>/agents/audit-dispatcher.md.
# This script lives at <plugin>/agents/audit-dispatcher/scripts/invoke_subagent.py,
# so .parent.parent.parent reaches the plugin/build/agents/ directory.
_SUBAGENT_PATH = Path(__file__).resolve().parent.parent.parent / "audit-dispatcher.md"

DEFAULT_MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096

REPORT_AUDIT_FINDING_TOOL = {
    "name": "report_audit_finding",
    "description": (
        "Report the audit result for one rule against one artifact. "
        "Call exactly once per invocation. The only valid response shape."
    ),
    "input_schema": {
        "type": "object",
        "required": ["rule_id", "overall_status", "findings"],
        "properties": {
            "rule_id": {
                "type": "string",
                "description": (
                    "Kebab-case rule id, derived from the rule file's "
                    "filename (drop 'rule-' prefix and '.md' suffix)."
                ),
            },
            "overall_status": {
                "type": "string",
                "enum": ["pass", "warn", "fail", "inapplicable"],
            },
            "findings": {
                "type": "array",
                "description": (
                    "List of findings. Empty for pass or inapplicable. "
                    "One or more entries for warn/fail."
                ),
                "items": {
                    "type": "object",
                    "required": ["status", "reasoning"],
                    "properties": {
                        "location": {
                            "type": "object",
                            "properties": {
                                "line": {"type": "integer"},
                                "context": {"type": "string"},
                            },
                        },
                        "status": {
                            "type": "string",
                            "enum": ["warn", "fail"],
                        },
                        "reasoning": {"type": "string"},
                        "recommended_changes": {"type": "string"},
                    },
                },
            },
        },
    },
}


class SubagentToolCallError(RuntimeError):
    """Raised when the subagent declines to call the tool after one retry."""


def _load_subagent_body() -> str:
    """Read the subagent definition's body (everything after the closing `---`)."""
    if not _SUBAGENT_PATH.exists():
        raise FileNotFoundError(f"subagent definition not found at {_SUBAGENT_PATH}")
    text = _SUBAGENT_PATH.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError(
            f"subagent definition has no frontmatter delimiters: {_SUBAGENT_PATH}"
        )
    return parts[2].strip()


def _derive_rule_id(rule_md: str, fallback: str | None = None) -> str:
    """Extract `name:` from frontmatter; fall back to filename stem."""
    if rule_md.startswith("---"):
        end = rule_md.find("---", 3)
        if end > 0:
            for line in rule_md[3:end].splitlines():
                if line.startswith("name:"):
                    name = line.split(":", 1)[1].strip().strip("'\"")
                    return name.lower().replace(" ", "-")
    if fallback:
        stem = Path(fallback).stem
        return stem.removeprefix("rule-")
    return "unknown-rule"


def _build_user_message(
    rule_md: str, artifact: str, findings: list[dict] | None
) -> list[dict]:
    """Assemble the user-message content blocks with cache markers.

    Cache strategy:
      - Rule body cached (varies per rule, stable across artifacts using it).
      - Artifact cached (varies per artifact, stable across rules judging it).
      - Findings inline (varies per call; not worth caching).
    """
    blocks: list[dict] = [
        {
            "type": "text",
            "text": "## Rule\n\n" + rule_md,
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": "## Artifact\n\n```\n" + artifact + "\n```",
            "cache_control": {"type": "ephemeral"},
        },
    ]
    if findings:
        blocks.append(
            {
                "type": "text",
                "text": (
                    "## Findings (recipe mode)\n\n"
                    "A deterministic script has detected the following violations. "
                    "For each, generate localized recommended_changes grounded in the "
                    "rule's How to apply. Do not re-evaluate detection — these are "
                    "known violations.\n\n" + json.dumps(findings, indent=2)
                ),
            }
        )
    else:
        blocks.append(
            {
                "type": "text",
                "text": (
                    "## Mode\n\n"
                    "No findings provided — this is judgment mode. Examine the "
                    "artifact end-to-end against the rule's imperative. Determine "
                    "overall_status and populate findings[] with each location of "
                    "noncompliance."
                ),
            }
        )
    return blocks


def _build_request(
    rule_md: str, artifact: str, findings: list[dict] | None, model: str
) -> dict:
    system = [
        {
            "type": "text",
            "text": _load_subagent_body(),
            "cache_control": {"type": "ephemeral"},
        }
    ]
    user_blocks = _build_user_message(rule_md, artifact, findings)
    return {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "system": system,
        "messages": [{"role": "user", "content": user_blocks}],
        "tools": [REPORT_AUDIT_FINDING_TOOL],
        "tool_choice": {"type": "tool", "name": "report_audit_finding"},
    }


def _extract_tool_input(response: Any) -> dict | None:
    """Return the tool_use block's input dict, or None if no tool_use present."""
    for block in getattr(response, "content", []):
        if (
            getattr(block, "type", None) == "tool_use"
            and getattr(block, "name", None) == "report_audit_finding"
        ):
            return dict(block.input)
    return None


def invoke_subagent(
    rule_md: str,
    artifact: str,
    findings: list[dict] | None = None,
    *,
    model: str = DEFAULT_MODEL,
    client: Any = None,
) -> dict:
    """Run one (rule, artifact) audit through the dispatcher subagent.

    Args:
        rule_md: Full rule file content (frontmatter + body).
        artifact: File content under audit.
        findings: Optional list of script-detected findings (recipe mode).
        model: Claude model id.
        client: Optional anthropic.Anthropic instance (for tests). When None,
            constructs one from the ANTHROPIC_API_KEY environment variable.

    Returns:
        Dict matching the report_audit_finding tool's input_schema.

    Raises:
        SubagentToolCallError: subagent failed to call the tool after one retry.
    """
    if client is None:
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise RuntimeError(
                "anthropic SDK not installed; pip install 'anthropic>=0.40'"
            ) from exc
        client = Anthropic()

    request = _build_request(rule_md, artifact, findings, model)
    response = client.messages.create(**request)

    result = _extract_tool_input(response)
    if result is not None:
        return result

    # Retry once: append a corrective user message instructing the model to
    # call the tool, including the original assistant turn for continuity.
    request["messages"].append({"role": "assistant", "content": response.content})
    request["messages"].append(
        {
            "role": "user",
            "content": (
                "You did not call the report_audit_finding tool. "
                "Call it now with the structured result. Do not respond with prose."
            ),
        }
    )
    retry_response = client.messages.create(**request)
    result = _extract_tool_input(retry_response)
    if result is not None:
        return result

    raise SubagentToolCallError(
        "subagent failed to call report_audit_finding tool after one retry; "
        "response contained only text blocks"
    )


def _dry_run(
    rule_md: str, artifact: str, findings: list[dict] | None, model: str
) -> None:
    """Print the request that would be sent, without calling the API."""
    request = _build_request(rule_md, artifact, findings, model)
    print(json.dumps(request, indent=2))


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--rule-file", required=True, type=Path, help="Path to a rule-*.md file"
    )
    parser.add_argument(
        "--artifact-file",
        required=True,
        type=Path,
        help="Path to the artifact under audit",
    )
    parser.add_argument(
        "--findings-file",
        type=Path,
        default=None,
        help="Optional JSON file with script-detected findings (triggers recipe mode)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Claude model id (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the API request body without calling the API",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = get_parser()
    args = parser.parse_args(argv)

    if not args.rule_file.exists():
        print(f"error: rule file not found: {args.rule_file}", file=sys.stderr)
        return EXIT_USAGE
    if not args.artifact_file.exists():
        print(f"error: artifact file not found: {args.artifact_file}", file=sys.stderr)
        return EXIT_USAGE

    rule_md = args.rule_file.read_text(encoding="utf-8")
    artifact = args.artifact_file.read_text(encoding="utf-8")
    findings: list[dict] | None = None
    if args.findings_file is not None:
        if not args.findings_file.exists():
            print(
                f"error: findings file not found: {args.findings_file}", file=sys.stderr
            )
            return EXIT_USAGE
        findings = json.loads(args.findings_file.read_text(encoding="utf-8"))

    if args.dry_run:
        _dry_run(rule_md, artifact, findings, args.model)
        return 0

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("error: ANTHROPIC_API_KEY not set", file=sys.stderr)
        return EXIT_USAGE

    try:
        result = invoke_subagent(rule_md, artifact, findings, model=args.model)
    except SubagentToolCallError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_TOOL_CALL_FAILURE

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
