#!/usr/bin/env python3
"""Tier-1 structural checker for GitHub Actions workflows.

Indentation-aware line walk (no YAML parser — stdlib only) that emits
the nine structural check IDs documented in audit-dimensions.md:

  FAIL:
    - permissions-top       — top-level `permissions:` missing or `write-all`
    - timeout-minutes       — any job missing `timeout-minutes:`
    - concurrency-deploy    — deploy/release workflows with cancel-in-progress: true

  WARN:
    - workflow-name         — top-level `name:` missing
    - job-name              — any job missing `name:`
    - step-name             — any multi-line run: step missing `name:`
    - defaults-shell        — workflow missing `defaults.run.shell: bash`
    - concurrency-group     — concurrency.group without `workflow`+`ref` keys
    - id-kebab              — job or step ID not kebab-case

Example:
    ./check_structure.py .github/workflows/ci.yml
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

EXIT_USAGE = 64

_WORKFLOW_SUFFIXES = (".yml", ".yaml")

_KEBAB_RE = re.compile(r"^[a-z][a-z0-9-]*$")
_DEPLOY_FILENAME_RE = re.compile(r"(?:^|[-_])(deploy|release|publish)", re.IGNORECASE)
_CLASSIFICATION_RE = re.compile(r"^\s*#\s*classification:\s*(\w+)", re.IGNORECASE)
_RUN_HEADER_RE = re.compile(r"^\s*(?:-\s+)?run:")


def _iter_workflows(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            for suffix in _WORKFLOW_SUFFIXES:
                files.extend(sorted(p.glob(f"*{suffix}")))
        elif p.is_file():
            files.append(p)
    return files


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _strip_inline_comment(value: str) -> str:
    # Very rough — misses `#` inside quoted strings, acceptable for our keys.
    if "#" in value:
        value = value.split("#", 1)[0]
    return value.strip().strip('"').strip("'")


def _classify_workflow(path: Path, lines: list[str]) -> str:
    for line in lines[:3]:
        match = _CLASSIFICATION_RE.match(line)
        if match:
            value = match.group(1).lower()
            return "deploy" if value in {"deploy", "release"} else "ci"
    if _DEPLOY_FILENAME_RE.search(path.stem):
        return "deploy"
    return "ci"


def _check_top_level(path: Path, lines: list[str]) -> list[str]:
    findings: list[str] = []
    has_name = False
    has_permissions = False
    permissions_value: str | None = None
    has_defaults_shell = False
    concurrency_lines: list[str] = []
    in_concurrency = False
    concurrency_indent = -1

    for i, line in enumerate(lines, start=1):
        stripped = line.rstrip()
        if not stripped or stripped.lstrip().startswith("#"):
            continue
        indent = _indent_of(stripped)

        if indent == 0:
            in_concurrency = False
            if stripped.startswith("name:"):
                has_name = True
            elif stripped.startswith("permissions:"):
                has_permissions = True
                tail = stripped[len("permissions:"):].strip()
                if tail:
                    permissions_value = _strip_inline_comment(tail)
            elif stripped.startswith("concurrency:"):
                in_concurrency = True
                concurrency_indent = 0
                tail = stripped[len("concurrency:"):].strip()
                if tail and not tail.startswith("#"):
                    concurrency_lines.append(tail)
            elif stripped.startswith("defaults:"):
                # Look ahead for `run: { shell: bash }` inline, or nested key.
                block_indent = 0
                for j in range(i, min(i + 10, len(lines))):
                    subline = lines[j]
                    if not subline.strip() or subline.lstrip().startswith("#"):
                        continue
                    sub_indent = _indent_of(subline)
                    if sub_indent <= block_indent:
                        break
                    if "shell:" in subline and "bash" in subline:
                        has_defaults_shell = True
                        break
        elif in_concurrency and indent > concurrency_indent:
            concurrency_lines.append(stripped.strip())
        elif in_concurrency:
            in_concurrency = False

    if not has_name:
        findings.append(
            f"WARN     {path} — workflow-name: top-level `name:` missing"
        )
        findings.append(
            "  Recommendation: Add `name: <Title>` as the first non-comment line."
        )

    if not has_permissions:
        findings.append(
            f"FAIL     {path} — permissions-top: "
            f"top-level `permissions:` block missing"
        )
        findings.append(
            "  Recommendation: Add `permissions: { contents: read }` at the "
            "workflow top level. Elevate per-job where needed."
        )
    elif permissions_value and permissions_value.lower() == "write-all":
        findings.append(
            f"FAIL     {path} — permissions-top: `permissions: write-all`"
        )
        findings.append(
            "  Recommendation: Replace with `contents: read` and elevate per-job."
        )

    if not has_defaults_shell:
        findings.append(
            f"WARN     {path} — defaults-shell: "
            f"`defaults.run.shell: bash` missing at workflow level"
        )
        findings.append(
            "  Recommendation: Add a top-level `defaults: { run: { shell: bash } }` "
            "to avoid OS-dependent shell differences."
        )

    if concurrency_lines:
        concurrency_text = " ".join(concurrency_lines).lower()
        if "group:" in concurrency_text:
            if (
                "github.workflow" not in concurrency_text
                or "github.ref" not in concurrency_text
            ):
                findings.append(
                    f"WARN     {path} — concurrency-group: concurrency.group "
                    f"does not include both `github.workflow` and `github.ref`"
                )
                findings.append(
                    "  Recommendation: Set "
                    "`group: ${{ github.workflow }}-${{ github.ref }}`."
                )

    return findings


def _check_concurrency_deploy(
    path: Path, lines: list[str], classification: str
) -> list[str]:
    findings: list[str] = []
    if classification != "deploy":
        return findings
    in_concurrency = False
    concurrency_indent = -1
    for i, line in enumerate(lines, start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = _indent_of(line)
        if indent == 0 and line.startswith("concurrency:"):
            in_concurrency = True
            concurrency_indent = 0
            continue
        if in_concurrency:
            if indent <= concurrency_indent and line.strip():
                in_concurrency = False
                continue
            if "cancel-in-progress" in line and "true" in line:
                findings.append(
                    f"FAIL     {path}:{i} — concurrency-deploy: "
                    f"deploy/release workflow sets `cancel-in-progress: true`"
                )
                findings.append(
                    "  Recommendation: Remove `cancel-in-progress` (or set "
                    "`false`). Cancelling a deploy mid-run leaves systems "
                    "inconsistent. Keep the `group:` key to serialize deploys."
                )
    return findings


def _check_jobs(path: Path, lines: list[str]) -> list[str]:
    """Walk `jobs:` to check per-job name / timeout / IDs and per-step names / IDs."""
    findings: list[str] = []
    in_jobs = False
    job_indent = -1
    current_job: dict[str, object] | None = None
    in_steps = False
    steps_indent = -1
    current_step: dict[str, object] | None = None

    def _flush_job() -> None:
        if current_job is None:
            return
        job_id = str(current_job["id"])
        job_line = int(current_job["line"])
        if not _KEBAB_RE.match(job_id):
            findings.append(
                f"WARN     {path}:{job_line} — id-kebab: "
                f"job id `{job_id}` is not kebab-case"
            )
            findings.append(
                "  Recommendation: Rename to lowercase kebab-case "
                "(`build-and-test`). Update `needs:` references."
            )
        if not current_job.get("has_name"):
            findings.append(
                f"WARN     {path}:{job_line} — job-name: "
                f"job `{job_id}` has no `name:` field"
            )
            findings.append(
                "  Recommendation: Add `name: <Human-readable title>` under the job."
            )
        if not current_job.get("has_timeout"):
            findings.append(
                f"FAIL     {path}:{job_line} — timeout-minutes: "
                f"job `{job_id}` has no `timeout-minutes:`"
            )
            findings.append(
                "  Recommendation: Add `timeout-minutes: <n>` (default ceiling 60). "
                "Runner default is 360 minutes."
            )

    def _flush_step() -> None:
        if current_step is None:
            return
        step_line = int(current_step["line"])
        step_id = current_step.get("id")
        if step_id and isinstance(step_id, str) and not _KEBAB_RE.match(step_id):
            findings.append(
                f"WARN     {path}:{step_line} — id-kebab: "
                f"step id `{step_id}` is not kebab-case"
            )
            findings.append(
                "  Recommendation: Rename to lowercase kebab-case. "
                "Update `steps.<id>.outputs` references."
            )
        if current_step.get("is_multiline_run") and not current_step.get("has_name"):
            findings.append(
                f"WARN     {path}:{step_line} — step-name: "
                f"multi-line `run:` step has no `name:`"
            )
            findings.append(
                "  Recommendation: Add `name: <Action>` above the `run:` block."
            )

    for i, line in enumerate(lines, start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = _indent_of(line)

        if indent == 0 and line.startswith("jobs:"):
            in_jobs = True
            job_indent = -1
            continue

        if in_jobs:
            if indent == 0 and line.strip():
                _flush_step()
                _flush_job()
                in_jobs = False
                current_job = None
                current_step = None
                in_steps = False
                continue

            if job_indent == -1 and indent > 0:
                job_indent = indent

            # New job entry: `  <id>:` at job_indent.
            if indent == job_indent and line.rstrip().endswith(":"):
                _flush_step()
                _flush_job()
                job_id = line.strip().rstrip(":").strip()
                current_job = {
                    "id": job_id,
                    "line": i,
                    "has_name": False,
                    "has_timeout": False,
                }
                current_step = None
                in_steps = False
                continue

            if current_job is None:
                continue

            # Inside a job — key at job_indent + 2 (typical 2-space YAML).
            inner_indent = job_indent + 2
            if indent == inner_indent:
                _flush_step()
                current_step = None
                in_steps = False
                stripped = line.strip()
                if stripped.startswith("name:"):
                    current_job["has_name"] = True
                elif stripped.startswith("timeout-minutes:"):
                    tail = stripped[len("timeout-minutes:"):].strip()
                    if tail and tail[0].isdigit():
                        current_job["has_timeout"] = True
                elif stripped.startswith("uses:"):
                    # Reusable workflow call — inherits timeout semantics
                    # from the callee; treat as having a timeout.
                    current_job["has_timeout"] = True
                    current_job["has_name"] = True
                elif stripped.startswith("steps:"):
                    in_steps = True
                    steps_indent = indent
                continue

            if in_steps and indent > steps_indent:
                # Step-level parse.
                stripped_no_dash = line.lstrip()
                if stripped_no_dash.startswith("- "):
                    _flush_step()
                    current_step = {
                        "line": i,
                        "has_name": False,
                        "is_multiline_run": False,
                        "id": None,
                    }
                    rest = stripped_no_dash[2:].strip()
                    if rest.startswith("name:"):
                        current_step["has_name"] = True
                    elif rest.startswith("id:"):
                        current_step["id"] = _strip_inline_comment(
                            rest[len("id:"):].strip()
                        )
                    elif rest.startswith("run:"):
                        # Single-line run — no name needed.
                        pass
                    continue
                if current_step is None:
                    continue
                stripped = line.strip()
                if stripped.startswith("name:"):
                    current_step["has_name"] = True
                elif stripped.startswith("id:"):
                    current_step["id"] = _strip_inline_comment(
                        stripped[len("id:"):].strip()
                    )
                elif stripped.startswith("run:"):
                    if stripped.rstrip() in (
                        "run: |", "run: |-", "run: >", "run: >-", "run: |+"
                    ):
                        current_step["is_multiline_run"] = True

    _flush_step()
    _flush_job()
    return findings


def _scan(path: Path) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        print(f"WARN     {path} — read: {exc}", file=sys.stderr)
        return []

    classification = _classify_workflow(path, lines)
    findings: list[str] = []
    findings.extend(_check_top_level(path, lines))
    findings.extend(_check_concurrency_deploy(path, lines, classification))
    findings.extend(_check_jobs(path, lines))
    return findings


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Structural checks for GitHub Actions workflows."
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
