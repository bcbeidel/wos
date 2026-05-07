#!/usr/bin/env python3
"""Detect frontmatter-echo body leads in `references/*.md` files.

A `references/*.md` file's frontmatter `description:` is the retrieval
anchor — the body opens with `**Why:**`. When the first body paragraph
paraphrases the description, the restatement adds tokens without
adding signal.

This detector tokenizes both strings and computes *coverage of the
description by the lead* — `|desc ∩ lead| / |desc|`, with stopwords
and short tokens excluded. Coverage answers the question that matches
the audit pattern: does the lead say what the description already
said? When coverage >= the threshold, the lead is a restatement.

The threshold is fixed at 0.70, calibrated against
`plugins/build/skills/check-*/references/**` (112 reference files):

    - 0.50 → 62 hits (55%). Flags leads sharing topic words but
      adding genuinely distinct content.
    - 0.60 → 48 hits (43%). Borderline cases where the lead names
      a partial subset of the description.
    - 0.70 → 37 hits (33%). Catches restatements (lead reproduces
      >=70% of description's content tokens) while preserving leads
      that extend the description with new claims. Chosen.
    - 0.80 → 29 hits (26%). Misses leads that paraphrase via
      light rewording.

The 2026-05-07 audit visually estimated ~99 of 112 files; the
measured rate at 0.70 is lower because the audit counted any
thematic restatement, while the detector requires content-token
preservation. The smaller measured count is the load-bearing number
for the sweep.

Jaccard was tried first but proved too conservative: leads commonly
extend the description with concrete examples ("a sequence of small,
named operations"), inflating union size and pushing Jaccard below
0.70 even when the description is fully restated. Coverage is the
right asymmetric metric for this pattern.

See `plugins/build/_shared/references/check-skill-pattern.md` for the
authoring rule.

Usage:
    check_reference_lead.py <path> [<path> ...]
    check_reference_lead.py --human plugins/build/skills/check-bash-script
    check_reference_lead.py --envelope plugins/build/skills/check-skill

Each path may be a directory (walked recursively for any `.md` file
beneath a `references/` directory) or a single `.md` file. With no
paths, walks the current working directory.

Output: JSON array of violations to stdout (or human-readable lines
with --human, or check-skill envelopes with --envelope). Exit 0 if
clean, 1 if any violations, 2 on read error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

THRESHOLD = 0.70

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_DESCRIPTION_LINE_RE = re.compile(
    r"^description:\s*(?P<style>[>|][-+]?)?\s*(?P<inline>.*)$",
    re.MULTILINE,
)
_PUNCT_RE = re.compile(r"[\.,;:!?()\[\]{}\"'`/\\]+")

_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "are",
        "have",
        "from",
        "when",
        "where",
        "what",
        "will",
        "into",
        "must",
        "can",
        "may",
        "not",
        "but",
        "also",
        "its",
        "any",
        "all",
        "via",
        "per",
        "use",
        "uses",
        "used",
        "one",
        "two",
        "than",
        "then",
        "such",
        "each",
        "they",
        "them",
        "their",
        "there",
        "these",
        "those",
    }
)


def _iter_reference_files(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        if p.is_file() and p.suffix == ".md" and "references" in p.parts:
            out.append(p)
        elif p.is_dir():
            for candidate in sorted(p.rglob("*.md")):
                if "references" in candidate.parts:
                    out.append(candidate)
    return out


def _parse_frontmatter(text: str) -> tuple[str, int] | None:
    """Return (frontmatter_block, body_offset) or None."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None
    return m.group(1), m.end()


def extract_description(frontmatter: str) -> str:
    """Pull the `description:` value, handling inline / folded / literal."""
    m = _DESCRIPTION_LINE_RE.search(frontmatter)
    if not m:
        return ""
    inline = m.group("inline").strip()
    style = m.group("style") or ""
    if style and not inline:
        # Folded `>-` or literal `|` block scalar — collect indented lines.
        rest = frontmatter[m.end() :].lstrip("\n")
        collected: list[str] = []
        for raw in rest.splitlines():
            if not raw.strip():
                if collected:
                    break
                continue
            if not raw.startswith((" ", "\t")):
                break
            collected.append(raw.strip())
        joined = " ".join(collected) if style.startswith(">") else "\n".join(collected)
        return joined
    return inline


def extract_lead(body: str) -> tuple[str, int, int]:
    """Return (lead_text, start_line, end_line) of the first paragraph.

    Lines are 1-indexed within the body. Stops at the first blank line
    or the first line beginning with `**` (e.g. `**Why:**`).
    Returns ("", 0, 0) if no lead paragraph is present.
    """
    lines = body.splitlines()
    # Skip leading blank lines.
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines):
        return "", 0, 0
    if lines[i].lstrip().startswith("**"):
        return "", 0, 0
    start = i
    captured: list[str] = []
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped:
            break
        if stripped.startswith("**"):
            break
        captured.append(stripped)
        i += 1
    end = i  # end-exclusive
    return " ".join(captured), start + 1, end


def tokenize(text: str) -> set[str]:
    """Lowercase, strip punctuation, drop short tokens and stopwords."""
    cleaned = _PUNCT_RE.sub(" ", text.lower())
    return {
        tok
        for tok in cleaned.split()
        if len(tok) >= 3 and tok not in _STOPWORDS
    }


def coverage(reference: set[str], lead: set[str]) -> float:
    """Return fraction of `reference` tokens also present in `lead`."""
    if not reference:
        return 0.0
    return len(reference & lead) / len(reference)


def find_violation(text: str) -> dict | None:
    parsed = _parse_frontmatter(text)
    if parsed is None:
        return None
    frontmatter, body_offset = parsed
    description = extract_description(frontmatter)
    if not description:
        return None
    body = text[body_offset:]
    lead_text, lead_start, lead_end = extract_lead(body)
    if not lead_text:
        return None
    desc_tokens = tokenize(description)
    lead_tokens = tokenize(lead_text)
    overlap = coverage(desc_tokens, lead_tokens)
    if overlap < THRESHOLD:
        return None
    body_offset_line = text[:body_offset].count("\n") + 1
    abs_start = body_offset_line + lead_start - 1
    abs_end = body_offset_line + lead_end - 1
    return {
        "overlap": round(overlap, 3),
        "description": description,
        "lead_text": lead_text,
        "lead_line_start": abs_start,
        "lead_line_end": abs_end,
    }


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Flag references/*.md whose body lead restates "
            "frontmatter description."
        ),
    )
    parser.add_argument(
        "paths",
        type=Path,
        nargs="*",
        help="Reference files or directories to walk. Defaults to current dir.",
    )
    parser.add_argument(
        "--human",
        action="store_true",
        help="Emit human-readable lines instead of JSON.",
    )
    parser.add_argument(
        "--envelope",
        action="store_true",
        help="Emit a check-skill-style envelope (rule_id=reference-lead-echo).",
    )
    return parser


_RECOMMENDED_CHANGES = (
    "Drop the leading paragraph. The frontmatter `description:` already "
    "carries the imperative; the body should open with **Why:**. See "
    "check-skill-pattern.md (Judgment Rule File Contract → Body lead)."
)


def _build_envelope(violations: list[dict]) -> dict:
    findings = [
        {
            "status": "warn",
            "location": {
                "line": v["lead_line_start"],
                "context": f"{v['file']}: {v['lead_text'][:80]}",
            },
            "reasoning": (
                f"First body paragraph covers {v['overlap']:.0%} of the "
                f"frontmatter `description:` tokens (threshold {THRESHOLD:.0%}); "
                f"the lead restates the description."
            ),
            "recommended_changes": _RECOMMENDED_CHANGES,
        }
        for v in violations
    ]
    return {
        "rule_id": "reference-lead-echo",
        "overall_status": "warn" if findings else "pass",
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = get_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as err:
        return int(err.code) if err.code is not None else 0
    paths = args.paths or [Path.cwd()]
    files = _iter_reference_files(paths)
    all_violations: list[dict] = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except OSError as err:
            print(f"error: cannot read {f}: {err}", file=sys.stderr)
            return 2
        v = find_violation(text)
        if v is not None:
            all_violations.append({"file": str(f), **v})
    if args.human:
        for v in all_violations:
            print(
                f"{v['file']}:{v['lead_line_start']}-{v['lead_line_end']}: "
                f"overlap={v['overlap']}: {v['lead_text'][:80]}"
            )
        if all_violations:
            print(
                f"\n{len(all_violations)} violations across "
                f"{len({v['file'] for v in all_violations})} files",
                file=sys.stderr,
            )
    elif args.envelope:
        json.dump(_build_envelope(all_violations), sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        json.dump(all_violations, sys.stdout, indent=2)
        sys.stdout.write("\n")
    return 1 if all_violations else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
