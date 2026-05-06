#!/usr/bin/env python3
"""Tier-1 structural checker for GitHub Actions workflows.

Indentation-aware line walk (no YAML parser — stdlib only). Emits a
JSON ARRAY of nine envelopes:

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

Exit codes:
  0   — overall_status pass / warn / inapplicable
  1   — any envelope overall_status=fail
  64  — usage error

Example:
    ./check_structure.py .github/workflows/ci.yml
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

_KEBAB_RE = re.compile(r"^[a-z][a-z0-9-]*$")
_DEPLOY_FILENAME_RE = re.compile(r"(?:^|[-_])(deploy|release|publish)", re.IGNORECASE)
_CLASSIFICATION_RE = re.compile(r"^\s*#\s*classification:\s*(\w+)", re.IGNORECASE)

_RULE_ORDER: list[str] = [
    "workflow-name",
    "job-name",
    "step-name",
    "permissions-top",
    "timeout-minutes",
    "defaults-shell",
    "concurrency-group",
    "concurrency-deploy",
    "id-kebab",
]

_RECIPE_WORKFLOW_NAME = (
    "Add `name: <Title>` as the first non-comment line. Without `name:`, "
    "the Checks UI derives a label from the filename — required-check "
    "configuration and PR comments read worse.\n\n"
    "Example:\n"
    "    on: push\n"
    "      -> name: CI\n"
    "         on: push\n"
)

_RECIPE_JOB_NAME = (
    "Add a `name:` to the job (human-readable, distinct from the job "
    "ID). Job names appear in the Checks UI and required-check names.\n\n"
    "Example:\n"
    "    jobs:\n"
    "      test:\n"
    "        runs-on: ubuntu-latest\n"
    "      -> jobs:\n"
    "           test:\n"
    "             name: Unit tests\n"
    "             runs-on: ubuntu-latest\n"
)

_RECIPE_STEP_NAME = (
    "Add a `name:` above the `run:` block. Unnamed multi-line steps "
    "render as `Run set -euo pipefail` (or longer) in logs — "
    "unreadable in a list of 20 steps.\n\n"
    "Example:\n"
    "    - run: |\n"
    "        set -euo pipefail\n"
    "        pytest -v\n"
    "      -> - name: Run tests\n"
    "           run: |\n"
    "             set -euo pipefail\n"
    "             pytest -v\n"
)

_RECIPE_PERMISSIONS_TOP = (
    "Add top-level `permissions: { contents: read }`. Elevate per-job "
    "where the specific job needs write scopes. The default "
    "`GITHUB_TOKEN` scope is too broad — a compromised action inherits "
    "the full scope.\n\n"
    "Example:\n"
    "    permissions:\n"
    "      contents: read\n"
    "    jobs:\n"
    "      release:\n"
    "        permissions:\n"
    "          contents: write   # only the release job elevates\n"
)

_RECIPE_TIMEOUT_MINUTES = (
    "Add `timeout-minutes:` to the job. Default ceiling: 60; tune to "
    "the expected duration + 25%% buffer. Runner default is 360 "
    "minutes — a hung job at that default burns $40+ of compute per "
    "incident.\n\n"
    "Example:\n"
    "    jobs:\n"
    "      build:\n"
    "        runs-on: ubuntu-latest\n"
    "        timeout-minutes: 20\n"
    "        steps: [...]\n"
)

_RECIPE_DEFAULTS_SHELL = (
    "Add `defaults.run.shell: bash` at workflow top level. The default "
    "`run:` shell differs across runner OSes (`bash` on Linux/macOS, "
    "PowerShell on Windows). Pinning one shell avoids the class of "
    "bugs where the same `run:` body behaves differently on different "
    "runners.\n\n"
    "Example:\n"
    "    defaults:\n"
    "      run:\n"
    "        shell: bash\n"
)

_RECIPE_CONCURRENCY_GROUP = (
    "Add workflow-level `concurrency` with a group keyed on "
    "`github.workflow` and `github.ref`. Set `cancel-in-progress: true` "
    "for PR/push workflows; omit (or set `false`) for deploy/release. "
    "Without concurrency, force-pushes pile up queued runs and waste "
    "minutes.\n\n"
    "Example:\n"
    "    concurrency:\n"
    "      group: ${{ github.workflow }}-${{ github.ref }}\n"
    "      cancel-in-progress: true\n"
)

_RECIPE_CONCURRENCY_DEPLOY = (
    "Remove `cancel-in-progress: true` (or set `false`) on the "
    "deploy/release workflow. Keep the `group:` key to serialize "
    "deploys. Cancelling a deploy mid-run leaves systems in "
    "inconsistent states; recovery is manual and error-prone.\n\n"
    "Example:\n"
    "    concurrency:\n"
    "      group: deploy-prod\n"
    "      cancel-in-progress: true\n"
    "      -> concurrency:\n"
    "           group: deploy-prod\n"
    "           cancel-in-progress: false\n"
)

_RECIPE_ID_KEBAB = (
    "Rename the ID to lowercase kebab-case (`build-and-test`, not "
    "`buildAndTest` or `BuildAndTest`). Update all `needs:` / `if:` / "
    "output references. Job IDs appear in URLs and required-check "
    "names; mixed case hurts readability.\n\n"
    "Example:\n"
    "    jobs:\n"
    "      BuildAndTest:\n"
    "      -> jobs:\n"
    "           build-and-test:\n"
)

_RECIPES: dict[str, str] = {
    "workflow-name": _RECIPE_WORKFLOW_NAME,
    "job-name": _RECIPE_JOB_NAME,
    "step-name": _RECIPE_STEP_NAME,
    "permissions-top": _RECIPE_PERMISSIONS_TOP,
    "timeout-minutes": _RECIPE_TIMEOUT_MINUTES,
    "defaults-shell": _RECIPE_DEFAULTS_SHELL,
    "concurrency-group": _RECIPE_CONCURRENCY_GROUP,
    "concurrency-deploy": _RECIPE_CONCURRENCY_DEPLOY,
    "id-kebab": _RECIPE_ID_KEBAB,
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
            print(f"check_structure.py: path not found: {p}", file=sys.stderr)
            raise _UsageError
    return files


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _strip_inline_comment(value: str) -> str:
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


def _check_top_level(
    path: Path, lines: list[str], per_rule: dict[str, list[dict]]
) -> None:
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
        per_rule["workflow-name"].append(
            _make_finding(
                "workflow-name",
                "warn",
                f"{path}: top-level `name:` missing",
                f"{path} has no top-level `name:` field. The Checks UI "
                "will derive a label from the filename.",
                line=1,
            )
        )

    if not has_permissions:
        per_rule["permissions-top"].append(
            _make_finding(
                "permissions-top",
                "fail",
                f"{path}: top-level `permissions:` block missing",
                f"{path} has no top-level `permissions:` block — the "
                "default `GITHUB_TOKEN` scope is too broad.",
                line=1,
            )
        )
    elif permissions_value and permissions_value.lower() == "write-all":
        per_rule["permissions-top"].append(
            _make_finding(
                "permissions-top",
                "fail",
                f"{path}: `permissions: write-all`",
                f"{path} sets `permissions: write-all` — the broadest "
                "possible scope, exact opposite of least-privilege.",
                line=1,
            )
        )

    if not has_defaults_shell:
        per_rule["defaults-shell"].append(
            _make_finding(
                "defaults-shell",
                "warn",
                f"{path}: `defaults.run.shell: bash` missing",
                f"{path} has no top-level `defaults.run.shell: bash`. "
                "The default `run:` shell differs across runner OSes.",
                line=1,
            )
        )

    if concurrency_lines:
        concurrency_text = " ".join(concurrency_lines).lower()
        if "group:" in concurrency_text:
            if (
                "github.workflow" not in concurrency_text
                or "github.ref" not in concurrency_text
            ):
                per_rule["concurrency-group"].append(
                    _make_finding(
                        "concurrency-group",
                        "warn",
                        f"{path}: concurrency.group does not include both "
                        "`github.workflow` and `github.ref`",
                        f"{path}: concurrency.group is set but does not "
                        "key on both `github.workflow` and `github.ref`.",
                        line=1,
                    )
                )


def _check_concurrency_deploy(
    path: Path,
    lines: list[str],
    classification: str,
    per_rule: dict[str, list[dict]],
) -> None:
    if classification != "deploy":
        return
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
                per_rule["concurrency-deploy"].append(
                    _make_finding(
                        "concurrency-deploy",
                        "fail",
                        f"{path}:{i}: deploy/release workflow sets "
                        "`cancel-in-progress: true`",
                        f"Line {i} of {path}: deploy/release workflow "
                        "sets `cancel-in-progress: true`. Cancelling a "
                        "deploy mid-run leaves systems inconsistent.",
                        line=i,
                    )
                )


def _check_jobs(
    path: Path, lines: list[str], per_rule: dict[str, list[dict]]
) -> None:
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
            per_rule["id-kebab"].append(
                _make_finding(
                    "id-kebab",
                    "warn",
                    f"{path}:{job_line}: job id `{job_id}` is not kebab-case",
                    f"Line {job_line} of {path}: job id `{job_id}` is "
                    "not lowercase kebab-case.",
                    line=job_line,
                )
            )
        if not current_job.get("has_name"):
            per_rule["job-name"].append(
                _make_finding(
                    "job-name",
                    "warn",
                    f"{path}:{job_line}: job `{job_id}` has no `name:` field",
                    f"Job `{job_id}` at line {job_line} of {path} has "
                    "no `name:` field.",
                    line=job_line,
                )
            )
        if not current_job.get("has_timeout"):
            per_rule["timeout-minutes"].append(
                _make_finding(
                    "timeout-minutes",
                    "fail",
                    f"{path}:{job_line}: job `{job_id}` has no `timeout-minutes:`",
                    f"Job `{job_id}` at line {job_line} of {path} has "
                    "no `timeout-minutes:` — runner default is 360 minutes.",
                    line=job_line,
                )
            )

    def _flush_step() -> None:
        if current_step is None:
            return
        step_line = int(current_step["line"])
        step_id = current_step.get("id")
        if step_id and isinstance(step_id, str) and not _KEBAB_RE.match(step_id):
            per_rule["id-kebab"].append(
                _make_finding(
                    "id-kebab",
                    "warn",
                    f"{path}:{step_line}: step id `{step_id}` is not kebab-case",
                    f"Line {step_line} of {path}: step id `{step_id}` "
                    "is not lowercase kebab-case.",
                    line=step_line,
                )
            )
        if current_step.get("is_multiline_run") and not current_step.get("has_name"):
            per_rule["step-name"].append(
                _make_finding(
                    "step-name",
                    "warn",
                    f"{path}:{step_line}: multi-line `run:` step has no `name:`",
                    f"Line {step_line} of {path}: multi-line `run:` "
                    "step has no `name:` — log lines will be unreadable.",
                    line=step_line,
                )
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
                    current_job["has_timeout"] = True
                    current_job["has_name"] = True
                elif stripped.startswith("steps:"):
                    in_steps = True
                    steps_indent = indent
                continue

            if in_steps and indent > steps_indent:
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


def _scan(path: Path, per_rule: dict[str, list[dict]]) -> None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        print(f"check_structure.py: cannot read {path}: {exc}", file=sys.stderr)
        return

    classification = _classify_workflow(path, lines)
    _check_top_level(path, lines, per_rule)
    _check_concurrency_deploy(path, lines, classification, per_rule)
    _check_jobs(path, lines, per_rule)


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_structure.py",
        description="Structural checks for GitHub Actions workflows.",
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
