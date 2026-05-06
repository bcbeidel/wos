#!/usr/bin/env python3
"""Tier-1 README code-block checker.

Emits a JSON ARRAY of four envelopes per `_common.py`:

  - fence-language (WARN): every fenced block carries a non-empty
    language info-string.
  - shell-prompt (WARN): no `$`, `>`, or `#` prompt prefix on lines
    in shell-tagged blocks. The `#` prefix on a line that is wholly
    a bash comment (starts with `# ` and has no shell syntax) is
    accepted.
  - smart-quotes (WARN): no smart quotes, em/en-dashes, or ellipsis
    inside fenced blocks.
  - code-line-length (WARN): fenced code lines <= 80 characters.

Exit codes:
  0  — all envelopes pass / warn / inapplicable
  1  — any envelope overall_status=fail (this script does not produce fails)
  64 — usage error

Example:
    ./check_codeblocks.py README.md path/to/docs/
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import emit_json_finding, emit_rule_envelope, print_envelope  # noqa: E402

EXIT_USAGE = 64
EXIT_INTERRUPTED = 130

_MD_EXTENSIONS = (".md", ".markdown")
_FRONTMATTER_FENCE = "---"

MAX_CODE_LINE = 80

_FENCE_RE = re.compile(r"^(?P<fence>`{3,}|~{3,})\s*(?P<lang>\S*)")
_SHELL_LANGS = {"bash", "sh", "shell", "console", "zsh", "pwsh", "ps1"}
_PROMPT_RE = re.compile(r"^\s*(\$|>|#)\s+\S")

_SMART_CHARS = {
    "‘": "U+2018 LEFT SINGLE QUOTATION MARK",
    "’": "U+2019 RIGHT SINGLE QUOTATION MARK",
    "“": "U+201C LEFT DOUBLE QUOTATION MARK",
    "”": "U+201D RIGHT DOUBLE QUOTATION MARK",
    "–": "U+2013 EN DASH",
    "—": "U+2014 EM DASH",
    "…": "U+2026 HORIZONTAL ELLIPSIS",
}

_RULE_ORDER: list[str] = [
    "fence-language",
    "shell-prompt",
    "smart-quotes",
    "code-line-length",
]

_RECIPE_FENCE_LANGUAGE = (
    "Add the appropriate language identifier after the opening fence. "
    "Syntax highlighting, copy buttons, and tool extraction all key off "
    "the language tag.\n\n"
    "Example:\n"
    "    ```\n"
    "    npm install\n"
    "    ```\n"
    "      -> ```bash\n"
    "         npm install\n"
    "         ```\n"
)

_RECIPE_SHELL_PROMPT = (
    "Strip `$`, `>`, or `#` prefixes from command lines. If output needs "
    "showing, split into an input block and a separate output block. "
    "Prompt characters break copy-paste.\n\n"
    "Example:\n"
    "    $ npm install\n"
    "    $ npm start\n"
    "      -> npm install\n"
    "         npm start\n"
)

_RECIPE_SMART_QUOTES = (
    "Replace curly quotes, em-dashes, en-dashes, and ellipsis with ASCII "
    "equivalents inside the code block. Shells interpret ASCII quotes; "
    "smart quotes fail unpredictably at runtime.\n\n"
    "Example:\n"
    '    curl “https://api.example.com”\n'
    '      -> curl "https://api.example.com"\n'
)

_RECIPE_CODE_LINE_LENGTH = (
    "Break the command with line continuations (`\\`) or pull flag values "
    "into env vars set earlier. Terminal soft-wrap inside code blocks "
    "breaks copy-paste.\n\n"
    "Example:\n"
    "    one 180-char `curl` invocation\n"
    "      -> `curl ... \\` continuation, or `API=...; curl \"$API/...\"`\n"
)

_RECIPES: dict[str, str] = {
    "fence-language": _RECIPE_FENCE_LANGUAGE,
    "shell-prompt": _RECIPE_SHELL_PROMPT,
    "smart-quotes": _RECIPE_SMART_QUOTES,
    "code-line-length": _RECIPE_CODE_LINE_LENGTH,
}


class _UsageError(Exception):
    pass


def _is_markdown(path: Path) -> bool:
    return path.suffix.lower() in _MD_EXTENSIONS


def _collect_targets(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for target in paths:
        if target.is_file():
            if _is_markdown(target):
                files.append(target)
        elif target.is_dir():
            for child in sorted(target.iterdir()):
                if child.is_file() and _is_markdown(child):
                    files.append(child)
        else:
            print(f"check_codeblocks.py: path not found: {target}", file=sys.stderr)
            raise _UsageError
    return files


def _make_finding(
    rule_id: str,
    severity: str,
    location_context: str,
    reasoning: str,
    line: int = 0,
) -> dict:
    return emit_json_finding(
        rule_id=rule_id,
        status=severity,
        location={"line": line, "context": location_context},
        reasoning=reasoning,
        recommended_changes=_RECIPES[rule_id],
    )


def _strip_frontmatter(lines: list[str]) -> list[str]:
    if not lines or lines[0].strip() != _FRONTMATTER_FENCE:
        return lines
    for idx in range(1, len(lines)):
        if lines[idx].strip() == _FRONTMATTER_FENCE:
            return [""] * (idx + 1) + lines[idx + 1 :]
    return lines


def _is_bash_comment_line(line: str) -> bool:
    stripped = line.lstrip()
    if not stripped.startswith("#"):
        return False
    if stripped.startswith("#!"):
        return True
    rest = stripped[1:]
    return not rest or rest[0] == " "


def _check_file(path: Path, per_rule: dict[str, list[dict]]) -> None:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as err:
        print(f"check_codeblocks.py: cannot read {path}: {err}", file=sys.stderr)
        return
    lines = _strip_frontmatter(raw)

    emitted: set[tuple[str, int]] = set()
    in_fence = False
    fence_marker: str | None = None
    fence_lang: str = ""
    fence_start: int = 0

    for lineno, line in enumerate(lines, 1):
        match = _FENCE_RE.match(line)
        if match and (not in_fence or line.startswith(fence_marker or "")):
            if not in_fence:
                in_fence = True
                fence_marker = match.group("fence")
                fence_lang = match.group("lang").lower()
                fence_start = lineno
                if not fence_lang and ("fence-language", fence_start) not in emitted:
                    per_rule["fence-language"].append(
                        _make_finding(
                            "fence-language",
                            "warn",
                            f"{path}: fence at line {fence_start} has no "
                            "language info-string",
                            f"Fence at line {fence_start} of {path} has no "
                            "language tag (MD040). Syntax highlighting and "
                            "tool extraction depend on the language tag.",
                            line=fence_start,
                        )
                    )
                    emitted.add(("fence-language", fence_start))
                continue
            in_fence = False
            fence_marker = None
            fence_lang = ""
            continue
        if not in_fence:
            continue

        if (
            fence_lang in _SHELL_LANGS
            and _PROMPT_RE.match(line)
            and not (fence_lang == "bash" and _is_bash_comment_line(line))
        ):
            key = ("shell-prompt", fence_start)
            if key not in emitted:
                per_rule["shell-prompt"].append(
                    _make_finding(
                        "shell-prompt",
                        "warn",
                        f"{path}: line {lineno} has prompt prefix in "
                        f"{fence_lang} block",
                        f"Line {lineno} of {path} in a {fence_lang} block "
                        "starts with a prompt prefix ($/>/#). Prompt "
                        "characters break copy-paste.",
                        line=lineno,
                    )
                )
                emitted.add(key)

        for ch, desc in _SMART_CHARS.items():
            if ch in line:
                key = ("smart-quotes", fence_start)
                if key not in emitted:
                    per_rule["smart-quotes"].append(
                        _make_finding(
                            "smart-quotes",
                            "warn",
                            f"{path}: line {lineno} contains {desc}",
                            f"Line {lineno} of {path} inside a fenced block "
                            f"contains {desc}. Shells interpret ASCII quotes; "
                            "smart quotes fail at runtime.",
                            line=lineno,
                        )
                    )
                    emitted.add(key)
                break

        if len(line) > MAX_CODE_LINE:
            key = ("code-line-length", fence_start)
            if key not in emitted:
                per_rule["code-line-length"].append(
                    _make_finding(
                        "code-line-length",
                        "warn",
                        f"{path}: line {lineno} is {len(line)} chars in code",
                        f"Line {lineno} of {path} inside a fenced block is "
                        f"{len(line)} chars (> {MAX_CODE_LINE}). Terminal "
                        "soft-wrap inside code blocks breaks copy-paste.",
                        line=lineno,
                    )
                )
                emitted.add(key)


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_codeblocks.py",
        description="Tier-1 README code-block checker (4 sub-checks).",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        metavar="path",
        help="One or more .md files or directories (non-recursive).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)
    try:
        per_rule: dict[str, list[dict]] = {r: [] for r in _RULE_ORDER}
        files = _collect_targets(args.paths)
        for f in files:
            _check_file(f, per_rule)
        envelopes = [
            emit_rule_envelope(rule_id=r, findings=per_rule[r]) for r in _RULE_ORDER
        ]
        print_envelope(envelopes)
        any_fail = any(e["overall_status"] == "fail" for e in envelopes)
        return 1 if any_fail else 0
    except _UsageError:
        return EXIT_USAGE
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED


if __name__ == "__main__":
    sys.exit(main())
