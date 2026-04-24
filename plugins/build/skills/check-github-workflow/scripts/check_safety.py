#!/usr/bin/env python3
"""Tier-1 safety checker for GitHub Actions workflows.

Nine safety checks. Five are FAIL; four are WARN/INFO.

  FAIL (Tier-2 exclude):
    - pr-target-checkout    — pull_request_target + checkout of PR ref
    - template-injection    — ${{ github.event.* }} / head_ref / inputs in run:
    - deprecated-cmds       — ::set-output / ::set-env / ::add-path

  FAIL (non-exclude):
    - workflow-env-secrets  — ${{ secrets.* }} in top-level env:
    - fork-pr-secrets       — pull_request workflows using secrets without source gate
    - self-hosted-public-pr — self-hosted runner on public-repo pull_request

  WARN:
    - strict-bash           — multi-line bash run: missing `set -euo pipefail`
    - persist-credentials   — actions/checkout without persist-credentials: false

  INFO:
    - harden-runner-first   — step-security/harden-runner not first step

Example:
    ./check_safety.py .github/workflows/ci.yml
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

EXIT_USAGE = 64

_WORKFLOW_SUFFIXES = (".yml", ".yaml")

_DEPRECATED_RE = re.compile(r"::(?:set-output|set-env|add-path)(?:\s+name=|::)")
_TEMPLATE_INJECTION_RE = re.compile(
    r"\$\{\{\s*(?:github\.event\.(?!sender\.login\b|repository\.(?:full_)?name\b|repository_id\b|pull_request\.number\b|issue\.number\b)"
    r"|github\.head_ref"
    r"|inputs\.)"
)
_SECRETS_REF_RE = re.compile(r"\$\{\{\s*secrets\.")
_PR_CHECKOUT_REF_RE = re.compile(
    r"\$\{\{\s*github\.(?:event\.pull_request\.head\.(?:sha|ref)|head_ref)\s*\}\}"
)
_RUN_HEADER_RE = re.compile(r"^(?P<indent>\s*)(?:-\s+)?run:\s*[|>][+-]?\s*$")
_USES_CHECKOUT_RE = re.compile(r"uses:\s*actions/checkout@")
_HARDEN_RUNNER_RE = re.compile(r"uses:\s*step-security/harden-runner@")
_GIT_PUSH_RE = re.compile(
    r"git\s+push\b|peaceiris/actions-gh-pages|ad-m/github-push-action"
)
_SELF_HOSTED_RE = re.compile(r"\bself-hosted\b")

_PUBLIC_REPO_MARKER_RE = re.compile(
    r"^\s*#\s*repo-visibility:\s*public", re.IGNORECASE
)


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


def _find_triggers(lines: list[str]) -> dict[str, bool]:
    """Return a map of trigger names found at the top-level `on:` key."""
    triggers: dict[str, bool] = {}
    in_on = False
    on_indent = -1
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = _indent_of(line)
        stripped = line.strip()
        if indent == 0 and stripped.startswith("on:"):
            in_on = True
            on_indent = 0
            tail = stripped[len("on:"):].strip()
            # Inline forms: `on: push`, `on: [push, pull_request]`
            if tail:
                tail_clean = tail.strip("[]").replace(",", " ")
                for tok in tail_clean.split():
                    triggers[tok.strip().strip('"').strip("'")] = True
            continue
        if in_on:
            if indent == 0 and stripped:
                in_on = False
                continue
            # Nested trigger keys: `  push:`, `  pull_request_target:`
            if indent > on_indent and stripped.endswith(":"):
                name = stripped.rstrip(":").strip()
                if name and not name.startswith("-"):
                    triggers[name] = True
            elif indent > on_indent and stripped.startswith("- "):
                name = stripped[2:].strip().rstrip(":")
                triggers[name] = True
    return triggers


def _check_template_injection_and_deprecated(path: Path, lines: list[str]) -> list[str]:
    """Walk run: blocks and flag template injection + deprecated commands."""
    findings: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        header = _RUN_HEADER_RE.match(lines[i])
        if not header:
            i += 1
            continue
        base_indent = len(header.group("indent"))
        body_lines: list[tuple[int, str]] = []
        i += 1
        while i < n:
            line = lines[i]
            if not line.strip():
                i += 1
                continue
            if _indent_of(line) <= base_indent:
                break
            body_lines.append((i + 1, line))
            i += 1
        for lineno, body_line in body_lines:
            if _DEPRECATED_RE.search(body_line):
                findings.append(
                    f"FAIL     {path}:{lineno} — deprecated-cmds: "
                    f"deprecated workflow command in `run:` block"
                )
                findings.append(
                    "  Recommendation: Use `$GITHUB_OUTPUT` / `$GITHUB_ENV` / "
                    "`$GITHUB_PATH`. `::set-output` etc. are silently "
                    "non-functional on new runners."
                )
            if _TEMPLATE_INJECTION_RE.search(body_line):
                findings.append(
                    f"FAIL     {path}:{lineno} — template-injection: "
                    f"user-controlled `${{{{ ... }}}}` expression in `run:` body"
                )
                findings.append(
                    "  Recommendation: Move the expression to a per-step "
                    "`env:` block; reference as `\"$VAR\"` in the run body."
                )
    return findings


def _check_pr_target_checkout(
    path: Path, lines: list[str], triggers: dict[str, bool]
) -> list[str]:
    findings: list[str] = []
    if not triggers.get("pull_request_target"):
        return findings
    for i, line in enumerate(lines, start=1):
        if _PR_CHECKOUT_REF_RE.search(line):
            findings.append(
                f"FAIL     {path}:{i} — pr-target-checkout: "
                f"`pull_request_target` + checkout of PR ref"
            )
            findings.append(
                "  Recommendation: Either switch the trigger to `pull_request` "
                "(no secrets for fork PRs), or remove the `ref:` and run only "
                "on the base branch. The combined pattern has no safe form."
            )
            break
    return findings


def _check_strict_bash(path: Path, lines: list[str]) -> list[str]:
    findings: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        header = _RUN_HEADER_RE.match(lines[i])
        if not header:
            i += 1
            continue
        start_lineno = i + 1
        base_indent = len(header.group("indent"))
        body_lines: list[tuple[int, str]] = []
        i += 1
        while i < n:
            line = lines[i]
            if not line.strip():
                i += 1
                continue
            if _indent_of(line) <= base_indent:
                break
            body_lines.append((i + 1, line))
            i += 1
        if len(body_lines) < 2:
            continue  # single-line body — not a strict-bash concern
        first_nonblank = body_lines[0][1].strip()
        has_strict = "set -" in first_nonblank and (
            "eo pipefail" in first_nonblank
            or "eu" in first_nonblank
            or "-o errexit" in first_nonblank
        )
        # Allow `#!/bin/sh` shebang-style opening as "explicitly not bash" — skip.
        if first_nonblank.startswith("#!") and "bash" not in first_nonblank:
            continue
        if not has_strict:
            findings.append(
                f"WARN     {path}:{start_lineno} — strict-bash: "
                f"multi-line `run:` block does not start with `set -euo pipefail`"
            )
            findings.append(
                "  Recommendation: Prepend `set -euo pipefail` to the run "
                "block. Bash's defaults silently swallow pipeline failures "
                "and unset variables."
            )
    return findings


def _check_workflow_env_secrets(path: Path, lines: list[str]) -> list[str]:
    findings: list[str] = []
    in_env = False
    env_indent = -1
    for i, line in enumerate(lines, start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = _indent_of(line)
        stripped = line.strip()
        if indent == 0 and stripped.startswith("env:"):
            in_env = True
            env_indent = 0
            continue
        if in_env:
            if indent <= env_indent and stripped:
                in_env = False
                continue
            if _SECRETS_REF_RE.search(line):
                findings.append(
                    f"FAIL     {path}:{i} — workflow-env-secrets: "
                    f"`${{{{ secrets.* }}}}` in top-level `env:`"
                )
                findings.append(
                    "  Recommendation: Remove from top-level `env:`; move to "
                    "step-level `env:` on the specific step that uses the secret."
                )
    return findings


def _check_fork_pr_secrets(
    path: Path, lines: list[str], triggers: dict[str, bool]
) -> list[str]:
    findings: list[str] = []
    if not triggers.get("pull_request"):
        return findings
    has_source_gate = any(
        "github.event.pull_request.head.repo.full_name" in line
        and "github.repository" in line
        for line in lines
    )
    if has_source_gate:
        return findings
    for i, line in enumerate(lines, start=1):
        if _SECRETS_REF_RE.search(line):
            findings.append(
                f"FAIL     {path}:{i} — fork-pr-secrets: "
                f"`pull_request` workflow references `${{{{ secrets.* }}}}` "
                f"without source gating"
            )
            findings.append(
                "  Recommendation: Either split into a `pull_request` (no "
                "secrets) and merge/label-gated workflow (with secrets), or "
                "gate the secret-using step with `if: "
                "github.event.pull_request.head.repo.full_name == github.repository`."
            )
            break
    return findings


def _check_self_hosted(
    path: Path, lines: list[str], triggers: dict[str, bool]
) -> list[str]:
    findings: list[str] = []
    if not triggers.get("pull_request"):
        return findings
    is_public = any(_PUBLIC_REPO_MARKER_RE.match(line) for line in lines[:5])
    if not is_public:
        return findings  # can't confirm visibility without a marker
    for i, line in enumerate(lines, start=1):
        if "runs-on:" in line and _SELF_HOSTED_RE.search(line):
            findings.append(
                f"FAIL     {path}:{i} — self-hosted-public-pr: "
                f"public-repo `pull_request` workflow uses self-hosted runner"
            )
            findings.append(
                "  Recommendation: Switch to a GitHub-hosted runner "
                "(`ubuntu-latest`). PR code running on self-hosted "
                "infrastructure is severe."
            )
    return findings


def _check_persist_credentials_and_harden(path: Path, lines: list[str]) -> list[str]:
    findings: list[str] = []
    job_has_push = _file_has_push(lines)
    # Walk steps to track "first step of each job" and checkout persist-credentials.
    in_jobs = False
    job_indent = -1
    in_steps = False
    steps_indent = -1
    current_job_line = -1
    first_step_of_job_flagged = False
    first_step_is_harden = False
    first_step_checked = False
    checkout_line = -1
    checkout_has_persist_false = False

    def _flush_harden() -> None:
        nonlocal first_step_of_job_flagged, first_step_is_harden, first_step_checked
        if current_job_line < 0 or not first_step_checked:
            return
        if not first_step_is_harden and not first_step_of_job_flagged:
            findings.append(
                f"INFO     {path}:{current_job_line} — harden-runner-first: "
                f"job first step is not `step-security/harden-runner`"
            )
            findings.append(
                "  Recommendation: Prepend a `Harden runner` step pinned to a "
                "SHA with `egress-policy: audit` (or `block` if characterized)."
            )
        first_step_of_job_flagged = True

    def _flush_checkout() -> None:
        nonlocal checkout_line, checkout_has_persist_false
        if checkout_line < 0:
            return
        if not checkout_has_persist_false and not job_has_push:
            findings.append(
                f"WARN     {path}:{checkout_line} — persist-credentials: "
                f"`actions/checkout` without `persist-credentials: false`"
            )
            findings.append(
                "  Recommendation: Add `with: { persist-credentials: false }` "
                "to the checkout step unless the job pushes back to the repo."
            )
        checkout_line = -1
        checkout_has_persist_false = False

    for i, line in enumerate(lines, start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = _indent_of(line)
        stripped = line.strip()

        if indent == 0 and stripped.startswith("jobs:"):
            in_jobs = True
            continue
        if in_jobs and indent == 0 and stripped:
            _flush_checkout()
            _flush_harden()
            in_jobs = False
            continue

        if in_jobs and job_indent == -1 and indent > 0:
            job_indent = indent

        if in_jobs and indent == job_indent and stripped.endswith(":"):
            _flush_checkout()
            _flush_harden()
            current_job_line = i
            first_step_is_harden = False
            first_step_checked = False
            first_step_of_job_flagged = False
            in_steps = False
            continue

        inner_indent = job_indent + 2 if job_indent >= 0 else -1
        if (
            inner_indent >= 0
            and indent == inner_indent
            and stripped.startswith("steps:")
        ):
            in_steps = True
            steps_indent = indent
            continue

        if in_steps and indent > steps_indent:
            if line.lstrip().startswith("- "):
                # new step
                if not first_step_checked:
                    first_step_checked = True
                    if _HARDEN_RUNNER_RE.search(line):
                        first_step_is_harden = True
                _flush_checkout()
                if _USES_CHECKOUT_RE.search(line):
                    checkout_line = i
                    checkout_has_persist_false = False
            else:
                if (
                    checkout_line > 0
                    and "persist-credentials" in line
                    and "false" in line
                ):
                    checkout_has_persist_false = True
                # Fallthrough — we don't track step-by-step bodies for harden.

    _flush_checkout()
    _flush_harden()
    return findings


def _file_has_push(lines: list[str]) -> bool:
    for line in lines:
        if _GIT_PUSH_RE.search(line):
            return True
    return False


def _scan(path: Path) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        print(f"WARN     {path} — read: {exc}", file=sys.stderr)
        return []

    findings: list[str] = []
    triggers = _find_triggers(lines)
    findings.extend(_check_pr_target_checkout(path, lines, triggers))
    findings.extend(_check_template_injection_and_deprecated(path, lines))
    findings.extend(_check_workflow_env_secrets(path, lines))
    findings.extend(_check_fork_pr_secrets(path, lines, triggers))
    findings.extend(_check_self_hosted(path, lines, triggers))
    findings.extend(_check_strict_bash(path, lines))
    findings.extend(_check_persist_credentials_and_harden(path, lines))
    return findings


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Safety checks for GitHub Actions workflows."
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
