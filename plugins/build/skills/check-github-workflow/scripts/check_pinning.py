#!/usr/bin/env python3
"""Tier-1 pinning checker for GitHub Actions workflows.

Emits findings for unsafe or unpinned action/image references:

  - `sha-pin-third-party` (FAIL) — third-party `uses:` not a 40-char SHA.
  - `sha-pin-first-party` (WARN) — first-party (`actions/*`, `github/*`)
    tag-pinned without an inline `# dependabot-managed` (or equivalent)
    comment.
  - `no-floating-ref` (FAIL) — any `@main`, `@master`, or floating
    semver wildcard on a `uses:`.
  - `docker-tag` (FAIL) — docker image reference missing a non-`latest`
    tag or `@sha256:` digest.
  - `runner-pin-deploy` (WARN) — release/deploy workflows (filename
    heuristic, or `# classification: deploy` header) using `*-latest`
    runner.

Example:
    ./check_pinning.py .github/workflows/deploy-prod.yml
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

EXIT_USAGE = 64

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
# `@v3.x`, `@v3.*`, `@v3-patch`, etc.
_FLOATING_SEMVER_RE = re.compile(r"^v\d+(?:\.[x*]|\.\d+\.[x*])")

_LATEST_TAG_RE = re.compile(r":latest\b|^[^:@]+$")


def _iter_workflows(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            for suffix in _WORKFLOW_SUFFIXES:
                files.extend(sorted(p.glob(f"*{suffix}")))
        elif p.is_file():
            files.append(p)
    return files


def _classify_workflow(path: Path, lines: list[str]) -> str:
    """Return 'deploy' or 'ci' based on header override or filename."""
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


def _check_uses(
    path: Path, lineno: int, ref: str, trailing: str
) -> list[str]:
    """Check a `uses:` ref. Does not handle `docker://` — see _check_docker_uses."""
    findings: list[str] = []
    if "@" not in ref:
        findings.append(
            f"FAIL     {path}:{lineno} — no-floating-ref: `uses: {ref}` has no ref"
        )
        findings.append(
            "  Recommendation: Pin to a 40-char commit SHA. Fetch via "
            "`gh api repos/<owner>/<repo>/git/refs/tags/<tag> --jq '.object.sha'`."
        )
        return findings

    repo, _, pinref = ref.rpartition("@")
    # Local `./.github/...` refs (reusable workflow calls) — skip pinning.
    if repo.startswith("./") or repo.startswith("../"):
        return findings

    if pinref in _FLOATING_REFS or _FLOATING_SEMVER_RE.match(pinref):
        findings.append(
            f"FAIL     {path}:{lineno} — no-floating-ref: `{ref}` "
            f"(@{pinref} is mutable)"
        )
        findings.append(
            "  Recommendation: Replace with a 40-char commit SHA. Never use "
            "`@main`, `@master`, or floating semver wildcards — "
            "unreproducible and unsafe."
        )
        return findings

    if _SHA_RE.match(pinref):
        return findings  # properly SHA-pinned

    # It's a tag ref (not a SHA). Differentiate first-party vs third-party.
    if _is_first_party(repo):
        dependabot_comment = "dependabot" in trailing.lower()
        if not dependabot_comment:
            findings.append(
                f"WARN     {path}:{lineno} — sha-pin-first-party: `{ref}` "
                f"(first-party tag pin without documented Dependabot coverage)"
            )
            findings.append(
                "  Recommendation: Either SHA-pin (preferred) or keep the tag "
                "and add an inline `# dependabot-managed` comment. Ensure "
                "`.github/dependabot.yml` covers `package-ecosystem: github-actions`."
            )
    else:
        findings.append(
            f"FAIL     {path}:{lineno} — sha-pin-third-party: `{ref}` "
            f"(third-party action pinned to tag, not SHA)"
        )
        findings.append(
            f"  Recommendation: Replace with the 40-char commit SHA. "
            f"Fetch via `gh api repos/{repo}/git/refs/tags/{pinref} "
            f"--jq '.object.sha'`. Add Dependabot for `github-actions`."
        )
    return findings


def _check_docker_image(path: Path, lineno: int, ref: str) -> list[str]:
    findings: list[str] = []
    if ref.endswith(":latest"):
        findings.append(
            f"FAIL     {path}:{lineno} — docker-tag: image `{ref}` uses `:latest`"
        )
        findings.append(
            "  Recommendation: Pin to an explicit non-`latest` tag "
            "(e.g., `node:20.11.1`) or a `@sha256:` digest."
        )
        return findings
    if "@sha256:" in ref or ":" in ref.split("/")[-1]:
        return findings
    findings.append(
        f"FAIL     {path}:{lineno} — docker-tag: image `{ref}` has no explicit tag"
    )
    findings.append(
        "  Recommendation: Add an explicit tag or `@sha256:` digest."
    )
    return findings


def _scan(path: Path) -> list[str]:
    findings: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        print(f"WARN     {path} — read: {exc}", file=sys.stderr)
        return findings

    classification = _classify_workflow(path, lines)

    for i, line in enumerate(lines, start=1):
        docker_match = _DOCKER_URI_RE.match(line)
        if docker_match:
            findings.extend(_check_docker_image(path, i, docker_match.group("ref")))
            continue

        uses_match = _USES_RE.match(line)
        if uses_match:
            findings.extend(_check_uses(
                path, i, uses_match.group("ref"), uses_match.group("trailing")
            ))
            continue

        image_match = _CONTAINER_IMAGE_RE.match(line)
        if image_match:
            ref = image_match.group("ref").strip('"').strip("'")
            # Skip `image: ${{ ... }}` dynamic refs.
            if not ref.startswith("${{"):
                findings.extend(_check_docker_image(path, i, ref))
            continue

        if classification == "deploy":
            runs_match = _RUNS_ON_RE.match(line)
            if runs_match:
                value = runs_match.group("value").strip()
                if value.endswith("-latest") or value == "ubuntu-latest":
                    findings.append(
                        f"WARN     {path}:{i} — runner-pin-deploy: "
                        f"deploy/release workflow uses `runs-on: {value}`"
                    )
                    findings.append(
                        "  Recommendation: Pin to an explicit runner version "
                        "(e.g., `ubuntu-24.04`). Image drift breaks releases."
                    )

    return findings


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Pinning checks for GitHub Actions workflows."
    )
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args(argv)

    workflows = _iter_workflows(args.paths)
    if not workflows:
        print("INFO     no workflow files found in provided paths")
        return 0

    had_fail = False
    for path in workflows:
        for line in _scan(path):
            print(line)
            if line.startswith("FAIL"):
                had_fail = True

    return 1 if had_fail else 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.exit(130)
