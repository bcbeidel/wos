#!/usr/bin/env python3
"""Tier-1 safety checker for GitHub Actions workflows.

Emits a JSON ARRAY of nine envelopes:

  FAIL:
    - pr-target-checkout    — pull_request_target + checkout of PR ref
    - template-injection    — ${{ github.event.* }} / head_ref / inputs in run:
    - deprecated-cmds       — ::set-output / ::set-env / ::add-path
    - workflow-env-secrets  — ${{ secrets.* }} in top-level env:
    - fork-pr-secrets       — pull_request workflows using secrets without source gate
    - self-hosted-public-pr — self-hosted runner on public-repo pull_request

  WARN:
    - strict-bash           — multi-line bash run: missing `set -euo pipefail`
    - persist-credentials   — actions/checkout without persist-credentials: false
    - harden-runner-first   — step-security/harden-runner not first step

Exit codes:
  0   — overall_status pass / warn / inapplicable
  1   — any envelope overall_status=fail
  64  — usage error

Example:
    ./check_safety.py .github/workflows/ci.yml
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

_RULE_ORDER: list[str] = [
    "pr-target-checkout",
    "template-injection",
    "deprecated-cmds",
    "workflow-env-secrets",
    "fork-pr-secrets",
    "self-hosted-public-pr",
    "strict-bash",
    "persist-credentials",
    "harden-runner-first",
]

_RECIPE_PR_TARGET_CHECKOUT = (
    "Either (a) switch the trigger to `pull_request` and remove any "
    "secret usage, or (b) keep `pull_request_target` but remove the "
    "PR-ref checkout and run only on the base ref. The combined "
    "pattern has no safe form. Fork code executing with write "
    "permissions and secrets is one of the most-exploited Actions "
    "patterns.\n\n"
    "Example:\n"
    "    on: pull_request_target\n"
    "    steps:\n"
    "      - uses: actions/checkout@<sha>\n"
    "        with:\n"
    "          ref: ${{ github.event.pull_request.head.sha }}\n"
    "      -> on: pull_request\n"
    "         steps:\n"
    "           - uses: actions/checkout@<sha>\n"
)

_RECIPE_TEMPLATE_INJECTION = (
    "Move the expression to a per-step `env:` block; reference as "
    "`\"$VAR\"` in the `run:` body. Direct `${{ }}` interpolation "
    "into `run:` text is shell injection — a PR title of "
    "`\"; rm -rf / #` executes as shell.\n\n"
    "Example:\n"
    "    - run: |\n"
    "        echo \"Title: ${{ github.event.issue.title }}\"\n"
    "      -> - env:\n"
    "             TITLE: ${{ github.event.issue.title }}\n"
    "           run: |\n"
    "             set -euo pipefail\n"
    "             echo \"Title: $TITLE\"\n"
)

_RECIPE_DEPRECATED_CMDS = (
    "Replace `::set-output` / `::set-env` / `::add-path` with the "
    "environment-file equivalents. The `::set-*` commands are "
    "deprecated and silently non-functional on new runners — workflows "
    "fail to pass outputs without any error signal.\n\n"
    "Example:\n"
    "    echo \"::set-output name=version::1.2.3\"\n"
    "    echo \"::set-env name=FOO::bar\"\n"
    "      -> echo \"version=1.2.3\" >> \"$GITHUB_OUTPUT\"\n"
    "         echo \"FOO=bar\" >> \"$GITHUB_ENV\"\n"
)

_RECIPE_WORKFLOW_ENV_SECRETS = (
    "Remove from top-level `env:`; add as step-level `env:` on the "
    "specific step that uses the secret. Workflow-level `env:` "
    "exposes the secret to every job, every step, and every action "
    "called from every step — including third-party actions that do "
    "not need it.\n\n"
    "Example:\n"
    "    env:\n"
    "      GH_TOKEN: ${{ secrets.GH_TOKEN }}\n"
    "      -> jobs:\n"
    "           release:\n"
    "             steps:\n"
    "               - env:\n"
    "                   GH_TOKEN: ${{ secrets.GH_TOKEN }}\n"
)

_RECIPE_FORK_PR_SECRETS = (
    "Split the workflow — a `pull_request` workflow with no secrets "
    "(safe for fork PRs), and a second workflow on merge or a "
    "`pull_request_target` label with secret access. Alternatively, "
    "gate the secret-using step on `github.event.pull_request.head."
    "repo.full_name == github.repository`. Fork PRs cannot safely "
    "receive secrets — fork code could exfiltrate them.\n"
)

_RECIPE_SELF_HOSTED_PUBLIC_PR = (
    "Switch the runner to a GitHub-hosted runner (`ubuntu-latest` for "
    "CI). If self-hosted is genuinely required, move the job to a "
    "merge- or label-gated workflow. PR code on your self-hosted "
    "infrastructure is severe — a malicious PR has access to whatever "
    "the runner has (persistent disk, network, credentials, neighbors "
    "on the host).\n\n"
    "Example:\n"
    "    on: pull_request\n"
    "    runs-on: [self-hosted, linux]\n"
    "      -> on: pull_request\n"
    "         runs-on: ubuntu-latest\n"
)

_RECIPE_STRICT_BASH = (
    "Prepend `set -euo pipefail` to the `run:` block. Bash defaults "
    "silently swallow pipeline failures and unset-variable typos; "
    "`set -euo pipefail` turns those into loud, early exits — the "
    "exact class of bug CI is supposed to catch.\n\n"
    "Example:\n"
    "    - run: |\n"
    "        echo \"step 1\"\n"
    "        make build\n"
    "      -> - run: |\n"
    "             set -euo pipefail\n"
    "             echo \"step 1\"\n"
    "             make build\n"
)

_RECIPE_PERSIST_CREDENTIALS = (
    "Add `persist-credentials: false` to the checkout `with:` block. "
    "Remove only if the job has a subsequent `git push` or push-shaped "
    "step. The checkout default leaves a usable `GITHUB_TOKEN` on "
    "disk (`.git/config`) for the rest of the job — every subsequent "
    "action can read it.\n\n"
    "Example:\n"
    "    - uses: actions/checkout@<sha>\n"
    "      -> - uses: actions/checkout@<sha>\n"
    "           with:\n"
    "             persist-credentials: false\n"
    "             fetch-depth: 1\n"
)

_RECIPE_HARDEN_RUNNER_FIRST = (
    "Prepend a `Harden runner` step to every job, pinned to a SHA, "
    "with `egress-policy: audit` (or `block` if you have characterized "
    "the egress). Runtime egress monitoring is the defense that "
    "catches what static pinning misses; OpenSSF explicitly recommends "
    "it post-tj-actions.\n\n"
    "Example:\n"
    "    jobs:\n"
    "      build:\n"
    "        steps:\n"
    "          - name: Harden runner\n"
    "            uses: step-security/harden-runner@<sha>\n"
    "            with:\n"
    "              egress-policy: audit\n"
    "          - uses: actions/checkout@<sha>\n"
)

_RECIPES: dict[str, str] = {
    "pr-target-checkout": _RECIPE_PR_TARGET_CHECKOUT,
    "template-injection": _RECIPE_TEMPLATE_INJECTION,
    "deprecated-cmds": _RECIPE_DEPRECATED_CMDS,
    "workflow-env-secrets": _RECIPE_WORKFLOW_ENV_SECRETS,
    "fork-pr-secrets": _RECIPE_FORK_PR_SECRETS,
    "self-hosted-public-pr": _RECIPE_SELF_HOSTED_PUBLIC_PR,
    "strict-bash": _RECIPE_STRICT_BASH,
    "persist-credentials": _RECIPE_PERSIST_CREDENTIALS,
    "harden-runner-first": _RECIPE_HARDEN_RUNNER_FIRST,
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
            print(f"check_safety.py: path not found: {p}", file=sys.stderr)
            raise _UsageError
    return files


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


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


def _find_triggers(lines: list[str]) -> dict[str, bool]:
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
            if tail:
                tail_clean = tail.strip("[]").replace(",", " ")
                for tok in tail_clean.split():
                    triggers[tok.strip().strip('"').strip("'")] = True
            continue
        if in_on:
            if indent == 0 and stripped:
                in_on = False
                continue
            if indent > on_indent and stripped.endswith(":"):
                name = stripped.rstrip(":").strip()
                if name and not name.startswith("-"):
                    triggers[name] = True
            elif indent > on_indent and stripped.startswith("- "):
                name = stripped[2:].strip().rstrip(":")
                triggers[name] = True
    return triggers


def _check_template_injection_and_deprecated(
    path: Path, lines: list[str], per_rule: dict[str, list[dict]]
) -> None:
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
                per_rule["deprecated-cmds"].append(
                    _make_finding(
                        "deprecated-cmds",
                        "fail",
                        f"{path}:{lineno}: deprecated workflow command "
                        "in `run:` block",
                        f"Line {lineno} of {path}: deprecated "
                        "`::set-output` / `::set-env` / `::add-path` "
                        "command — silently non-functional on new runners.",
                        line=lineno,
                    )
                )
            if _TEMPLATE_INJECTION_RE.search(body_line):
                per_rule["template-injection"].append(
                    _make_finding(
                        "template-injection",
                        "fail",
                        f"{path}:{lineno}: user-controlled `${{ ... }}` "
                        "expression in `run:` body",
                        f"Line {lineno} of {path}: `${{ ... }}` "
                        "expression interpolated directly into `run:` "
                        "text — shell injection risk.",
                        line=lineno,
                    )
                )


def _check_pr_target_checkout(
    path: Path,
    lines: list[str],
    triggers: dict[str, bool],
    per_rule: dict[str, list[dict]],
) -> None:
    if not triggers.get("pull_request_target"):
        return
    for i, line in enumerate(lines, start=1):
        if _PR_CHECKOUT_REF_RE.search(line):
            per_rule["pr-target-checkout"].append(
                _make_finding(
                    "pr-target-checkout",
                    "fail",
                    f"{path}:{i}: `pull_request_target` + checkout of PR ref",
                    f"Line {i} of {path}: workflow uses "
                    "`pull_request_target` and checks out the PR ref. "
                    "Fork code with secrets — textbook CVE vector.",
                    line=i,
                )
            )
            break


def _check_strict_bash(
    path: Path, lines: list[str], per_rule: dict[str, list[dict]]
) -> None:
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
            continue
        first_nonblank = body_lines[0][1].strip()
        has_strict = "set -" in first_nonblank and (
            "eo pipefail" in first_nonblank
            or "eu" in first_nonblank
            or "-o errexit" in first_nonblank
        )
        if first_nonblank.startswith("#!") and "bash" not in first_nonblank:
            continue
        if not has_strict:
            per_rule["strict-bash"].append(
                _make_finding(
                    "strict-bash",
                    "warn",
                    f"{path}:{start_lineno}: multi-line `run:` block does "
                    "not start with `set -euo pipefail`",
                    f"Line {start_lineno} of {path}: multi-line `run:` "
                    "block has no `set -euo pipefail` prefix.",
                    line=start_lineno,
                )
            )


def _check_workflow_env_secrets(
    path: Path, lines: list[str], per_rule: dict[str, list[dict]]
) -> None:
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
                per_rule["workflow-env-secrets"].append(
                    _make_finding(
                        "workflow-env-secrets",
                        "fail",
                        f"{path}:{i}: `${{ secrets.* }}` in top-level `env:`",
                        f"Line {i} of {path}: secret reference in "
                        "top-level `env:` — exposes the secret to every "
                        "job and every step.",
                        line=i,
                    )
                )


def _check_fork_pr_secrets(
    path: Path,
    lines: list[str],
    triggers: dict[str, bool],
    per_rule: dict[str, list[dict]],
) -> None:
    if not triggers.get("pull_request"):
        return
    has_source_gate = any(
        "github.event.pull_request.head.repo.full_name" in line
        and "github.repository" in line
        for line in lines
    )
    if has_source_gate:
        return
    for i, line in enumerate(lines, start=1):
        if _SECRETS_REF_RE.search(line):
            per_rule["fork-pr-secrets"].append(
                _make_finding(
                    "fork-pr-secrets",
                    "fail",
                    f"{path}:{i}: `pull_request` workflow references "
                    "`${{ secrets.* }}` without source gating",
                    f"Line {i} of {path}: `pull_request` workflow "
                    "references a secret without a source gate. Fork "
                    "PRs could exfiltrate the secret.",
                    line=i,
                )
            )
            break


def _check_self_hosted(
    path: Path,
    lines: list[str],
    triggers: dict[str, bool],
    per_rule: dict[str, list[dict]],
) -> None:
    if not triggers.get("pull_request"):
        return
    is_public = any(_PUBLIC_REPO_MARKER_RE.match(line) for line in lines[:5])
    if not is_public:
        return
    for i, line in enumerate(lines, start=1):
        if "runs-on:" in line and _SELF_HOSTED_RE.search(line):
            per_rule["self-hosted-public-pr"].append(
                _make_finding(
                    "self-hosted-public-pr",
                    "fail",
                    f"{path}:{i}: public-repo `pull_request` workflow uses "
                    "self-hosted runner",
                    f"Line {i} of {path}: public-repo `pull_request` "
                    "workflow runs on a self-hosted runner — PR code "
                    "executes on your infrastructure.",
                    line=i,
                )
            )


def _file_has_push(lines: list[str]) -> bool:
    for line in lines:
        if _GIT_PUSH_RE.search(line):
            return True
    return False


def _check_persist_credentials_and_harden(
    path: Path, lines: list[str], per_rule: dict[str, list[dict]]
) -> None:
    job_has_push = _file_has_push(lines)
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
            per_rule["harden-runner-first"].append(
                _make_finding(
                    "harden-runner-first",
                    "warn",
                    f"{path}:{current_job_line}: job first step is not "
                    "`step-security/harden-runner`",
                    f"Job at line {current_job_line} of {path} does not "
                    "start with a harden-runner step — runtime egress "
                    "monitoring is missing.",
                    line=current_job_line,
                )
            )
        first_step_of_job_flagged = True

    def _flush_checkout() -> None:
        nonlocal checkout_line, checkout_has_persist_false
        if checkout_line < 0:
            return
        if not checkout_has_persist_false and not job_has_push:
            per_rule["persist-credentials"].append(
                _make_finding(
                    "persist-credentials",
                    "warn",
                    f"{path}:{checkout_line}: `actions/checkout` without "
                    "`persist-credentials: false`",
                    f"Line {checkout_line} of {path}: `actions/checkout` "
                    "leaves a usable token on disk for the rest of the job.",
                    line=checkout_line,
                )
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

    _flush_checkout()
    _flush_harden()


def _scan(path: Path, per_rule: dict[str, list[dict]]) -> None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        print(f"check_safety.py: cannot read {path}: {exc}", file=sys.stderr)
        return

    triggers = _find_triggers(lines)
    _check_pr_target_checkout(path, lines, triggers, per_rule)
    _check_template_injection_and_deprecated(path, lines, per_rule)
    _check_workflow_env_secrets(path, lines, per_rule)
    _check_fork_pr_secrets(path, lines, triggers, per_rule)
    _check_self_hosted(path, lines, triggers, per_rule)
    _check_strict_bash(path, lines, per_rule)
    _check_persist_credentials_and_harden(path, lines, per_rule)


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_safety.py",
        description="Safety checks for GitHub Actions workflows.",
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
