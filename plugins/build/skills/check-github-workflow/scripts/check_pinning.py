#!/usr/bin/env python3
"""Tier-1 pinning checker for GitHub Actions workflows.

Emits a JSON ARRAY of five envelopes:

  - `sha-pin-third-party` (FAIL) — third-party `uses:` not a 40-char SHA.
  - `sha-pin-first-party` (WARN) — first-party (`actions/*`, `github/*`)
    tag-pinned without an inline `# dependabot-managed` (or equivalent).
  - `no-floating-ref` (FAIL) — any `@main`, `@master`, missing-ref, or
    floating semver wildcard on a `uses:`.
  - `docker-tag` (FAIL) — docker image reference missing a non-`latest`
    tag or `@sha256:` digest.
  - `runner-pin-deploy` (WARN) — release/deploy workflows using a
    `*-latest` runner.

Exit codes:
  0   — overall_status pass / warn / inapplicable
  1   — any envelope overall_status=fail
  64  — usage error

Example:
    ./check_pinning.py .github/workflows/deploy-prod.yml
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

_WORKFLOW_SUFFIXES = (".yml", ".yaml")
_FIRST_PARTY_PREFIXES = ("actions/", "github/")
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")

_USES_RE = re.compile(
    r"^(?P<indent>\s*)(?:-\s+)?uses:\s*(?P<ref>\S+)\s*(?P<trailing>.*)$"
)
_DOCKER_URI_RE = re.compile(
    r"^(?P<indent>\s*)(?:-\s+)?uses:\s*docker://(?P<ref>\S+)\s*(?P<trailing>.*)$"
)
_CONTAINER_IMAGE_RE = re.compile(
    r"^(?P<indent>\s*)image:\s*(?P<ref>\S+)\s*(?P<trailing>.*)$"
)
_RUNS_ON_RE = re.compile(
    r"^(?P<indent>\s*)runs-on:\s*(?P<value>[^#\n]+?)\s*(?:#.*)?$"
)

_DEPLOY_FILENAME_RE = re.compile(r"(?:^|[-_])(deploy|release|publish)", re.IGNORECASE)
_CLASSIFICATION_RE = re.compile(r"^\s*#\s*classification:\s*(\w+)", re.IGNORECASE)

_FLOATING_REFS = {"main", "master", "HEAD"}
_FLOATING_SEMVER_RE = re.compile(r"^v\d+(?:\.[x*]|\.\d+\.[x*])")

_RULE_ORDER: list[str] = [
    "sha-pin-third-party",
    "sha-pin-first-party",
    "no-floating-ref",
    "docker-tag",
    "runner-pin-deploy",
]

_RECIPE_SHA_PIN_THIRD_PARTY = (
    "Replace the tag ref with the full 40-char commit SHA. Add a "
    "trailing comment with the tag for readability. Ensure "
    "`.github/dependabot.yml` covers `package-ecosystem: github-actions` "
    "so the SHA does not rot. Post-tj-actions (CVE-2025-30066), tags "
    "are mutable supply-chain liabilities.\n\n"
    "Example:\n"
    "    uses: tj-actions/changed-files@v44\n"
    "      -> uses: tj-actions/changed-files@<40-char-sha>  # v44\n"
    "Fetch with: gh api repos/<owner>/<repo>/git/refs/tags/<tag> "
    "--jq '.object.sha'\n"
)

_RECIPE_SHA_PIN_FIRST_PARTY = (
    "Either (a) SHA-pin like a third-party action (preferred), or (b) "
    "keep the major tag and add an inline `# dependabot-managed` "
    "comment, then verify `.github/dependabot.yml` covers "
    "`package-ecosystem: github-actions`. The first-party tag exemption "
    "is pragmatic but it requires documentation and Dependabot "
    "coverage — otherwise the exemption is invisible to the auditor.\n\n"
    "Example:\n"
    "    uses: actions/checkout@v4\n"
    "      -> uses: actions/checkout@<sha>  # v4.2.2\n"
    "      -> uses: actions/checkout@v4  # dependabot-managed\n"
)

_RECIPE_NO_FLOATING_REF = (
    "Replace the floating ref with a pinned 40-char SHA (preferred) or "
    "a specific tag (`@v4.2.2`, not `@v4`). Mutable refs are "
    "unreproducible and unsafe. A push to `main` or a tag move on "
    "`@v4` silently changes what runs.\n\n"
    "Example:\n"
    "    uses: some-action/foo@main\n"
    "      -> uses: some-action/foo@<40-char-sha>  # v1.2.3\n"
)

_RECIPE_DOCKER_TAG = (
    "Pin the image to an explicit non-`latest` tag or `@sha256:` "
    "digest. Docker `:latest` has the same mutable-ref failure mode as "
    "`@main` on an action.\n\n"
    "Example:\n"
    "    image: node:latest\n"
    "      -> image: node:20.11.1\n"
    "      -> image: node@sha256:abc123...\n"
)

_RECIPE_RUNNER_PIN_DEPLOY = (
    "Replace `ubuntu-latest` (or `*-latest`) with the current Ubuntu "
    "LTS version (`ubuntu-24.04`, as of 2026). Image drift breaks "
    "production release pipelines — rare but catastrophic on the exact "
    "workflow you can least afford to break.\n\n"
    "Example:\n"
    "    runs-on: ubuntu-latest\n"
    "      -> runs-on: ubuntu-24.04\n"
)

_RECIPES: dict[str, str] = {
    "sha-pin-third-party": _RECIPE_SHA_PIN_THIRD_PARTY,
    "sha-pin-first-party": _RECIPE_SHA_PIN_FIRST_PARTY,
    "no-floating-ref": _RECIPE_NO_FLOATING_REF,
    "docker-tag": _RECIPE_DOCKER_TAG,
    "runner-pin-deploy": _RECIPE_RUNNER_PIN_DEPLOY,
}


class _UsageError(Exception):
    pass


def _iter_workflows(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            for suffix in _WORKFLOW_SUFFIXES:
                files.extend(sorted(p.glob(f"*{suffix}")))
        elif p.is_file():
            files.append(p)
        else:
            print(f"check_pinning.py: path not found: {p}", file=sys.stderr)
            raise _UsageError
    return files


def _classify_workflow(path: Path, lines: list[str]) -> str:
    for line in lines[:3]:
        match = _CLASSIFICATION_RE.match(line)
        if match:
            value = match.group(1).lower()
            return "deploy" if value in {"deploy", "release"} else "ci"
    if _DEPLOY_FILENAME_RE.search(path.stem):
        return "deploy"
    return "ci"


def _is_first_party(repo: str) -> bool:
    return any(repo.startswith(prefix) for prefix in _FIRST_PARTY_PREFIXES)


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


def _check_uses(
    path: Path,
    lineno: int,
    ref: str,
    trailing: str,
    per_rule: dict[str, list[dict]],
) -> None:
    if "@" not in ref:
        per_rule["no-floating-ref"].append(
            _make_finding(
                "no-floating-ref",
                "fail",
                f"{path}:{lineno}: `uses: {ref}` has no ref",
                f"`uses: {ref}` at line {lineno} of {path} has no "
                "pinned ref. Mutable refs are unreproducible and unsafe.",
                line=lineno,
            )
        )
        return

    repo, _, pinref = ref.rpartition("@")
    # Local `./.github/...` refs (reusable workflow calls) — skip pinning.
    if repo.startswith("./") or repo.startswith("../"):
        return

    if pinref in _FLOATING_REFS or _FLOATING_SEMVER_RE.match(pinref):
        per_rule["no-floating-ref"].append(
            _make_finding(
                "no-floating-ref",
                "fail",
                f"{path}:{lineno}: `{ref}` (@{pinref} is mutable)",
                f"Line {lineno} of {path}: `uses: {ref}` uses mutable "
                f"ref `@{pinref}`. A tag move or branch push silently "
                "changes what runs.",
                line=lineno,
            )
        )
        return

    if _SHA_RE.match(pinref):
        return  # properly SHA-pinned

    # Tag ref (not a SHA). Differentiate first-party vs third-party.
    if _is_first_party(repo):
        dependabot_comment = "dependabot" in trailing.lower()
        if not dependabot_comment:
            per_rule["sha-pin-first-party"].append(
                _make_finding(
                    "sha-pin-first-party",
                    "warn",
                    f"{path}:{lineno}: `{ref}` (first-party tag pin "
                    "without documented Dependabot coverage)",
                    f"Line {lineno} of {path}: first-party action "
                    f"`{ref}` is tag-pinned without an inline "
                    "`# dependabot-managed` marker.",
                    line=lineno,
                )
            )
    else:
        per_rule["sha-pin-third-party"].append(
            _make_finding(
                "sha-pin-third-party",
                "fail",
                f"{path}:{lineno}: `{ref}` (third-party action "
                "pinned to tag, not SHA)",
                f"Line {lineno} of {path}: third-party action `{ref}` "
                "is pinned to a tag rather than a 40-char commit SHA. "
                "Tags are mutable supply-chain liabilities.",
                line=lineno,
            )
        )


def _check_docker_image(
    path: Path, lineno: int, ref: str, per_rule: dict[str, list[dict]]
) -> None:
    if ref.endswith(":latest"):
        per_rule["docker-tag"].append(
            _make_finding(
                "docker-tag",
                "fail",
                f"{path}:{lineno}: image `{ref}` uses `:latest`",
                f"Line {lineno} of {path}: docker image `{ref}` uses "
                "the mutable `:latest` tag.",
                line=lineno,
            )
        )
        return
    if "@sha256:" in ref or ":" in ref.split("/")[-1]:
        return
    per_rule["docker-tag"].append(
        _make_finding(
            "docker-tag",
            "fail",
            f"{path}:{lineno}: image `{ref}` has no explicit tag",
            f"Line {lineno} of {path}: docker image `{ref}` has no "
            "explicit tag — defaults to `:latest`.",
            line=lineno,
        )
    )


def _scan(path: Path, per_rule: dict[str, list[dict]]) -> None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        print(f"check_pinning.py: cannot read {path}: {exc}", file=sys.stderr)
        return

    classification = _classify_workflow(path, lines)

    for i, line in enumerate(lines, start=1):
        docker_match = _DOCKER_URI_RE.match(line)
        if docker_match:
            _check_docker_image(path, i, docker_match.group("ref"), per_rule)
            continue

        uses_match = _USES_RE.match(line)
        if uses_match:
            _check_uses(
                path,
                i,
                uses_match.group("ref"),
                uses_match.group("trailing"),
                per_rule,
            )
            continue

        image_match = _CONTAINER_IMAGE_RE.match(line)
        if image_match:
            ref = image_match.group("ref").strip('"').strip("'")
            if not ref.startswith("${{"):
                _check_docker_image(path, i, ref, per_rule)
            continue

        if classification == "deploy":
            runs_match = _RUNS_ON_RE.match(line)
            if runs_match:
                value = runs_match.group("value").strip()
                if value.endswith("-latest") or value == "ubuntu-latest":
                    per_rule["runner-pin-deploy"].append(
                        _make_finding(
                            "runner-pin-deploy",
                            "warn",
                            f"{path}:{i}: deploy/release workflow uses "
                            f"`runs-on: {value}`",
                            f"Line {i} of {path}: deploy/release "
                            f"workflow uses `runs-on: {value}`. Image "
                            "drift breaks releases.",
                            line=i,
                        )
                    )


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_pinning.py",
        description="Pinning checks for GitHub Actions workflows.",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        metavar="path",
        help="One or more workflow .yml/.yaml files or directories.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)
    try:
        per_rule: dict[str, list[dict]] = {r: [] for r in _RULE_ORDER}
        files = _iter_workflows(args.paths)
        for path in files:
            _scan(path, per_rule)
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
