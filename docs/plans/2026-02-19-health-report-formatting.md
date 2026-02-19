# Health Report Formatting Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add human-readable text output to the health check script, making text the default and moving JSON behind `--json`.

**Architecture:** New `wos/formatting.py` module with pure functions that take the existing report dict and return formatted strings. `scripts/check_health.py` gains `--detailed`, `--json`, and `--no-color` flags. Skill workflow files simplified to show text output directly.

**Tech Stack:** Python 3.9, pytest, no new dependencies

---

### Task 1: Color Helpers and Status Line Formatter

**Files:**
- Create: `wos/formatting.py`
- Create: `tests/test_formatting.py`

**Context:** The formatting module needs ANSI color helpers and a status line
renderer. The status line is shared between summary and detailed modes:
`Health: WARN (3 issues in 12 files)`. Color mapping: FAIL=red, WARN=yellow,
INFO=dim, PASS=green. Only severity labels and the status word get colored.

**Step 1: Write the failing tests**

```python
"""Tests for wos.formatting — human-readable health report output."""

from __future__ import annotations

from wos.formatting import (
    _colorize,
    _status_line,
    _SEVERITY_ORDER,
)


class TestColorize:
    def test_no_color_returns_plain(self) -> None:
        assert _colorize("FAIL", "fail", color=False) == "FAIL"

    def test_color_wraps_with_ansi(self) -> None:
        result = _colorize("FAIL", "fail", color=True)
        assert result.startswith("\033[")
        assert "FAIL" in result
        assert result.endswith("\033[0m")

    def test_pass_is_green(self) -> None:
        result = _colorize("PASS", "pass", color=True)
        assert "\033[32m" in result  # green

    def test_warn_is_yellow(self) -> None:
        result = _colorize("WARN", "warn", color=True)
        assert "\033[33m" in result  # yellow

    def test_info_is_dim(self) -> None:
        result = _colorize("INFO", "info", color=True)
        assert "\033[2m" in result  # dim


class TestSeverityOrder:
    def test_fail_before_warn_before_info(self) -> None:
        assert _SEVERITY_ORDER["fail"] < _SEVERITY_ORDER["warn"]
        assert _SEVERITY_ORDER["warn"] < _SEVERITY_ORDER["info"]


class TestStatusLine:
    def test_pass_status(self) -> None:
        line = _status_line("pass", 0, 5, color=False)
        assert line == "Health: PASS (0 issues in 5 files)"

    def test_fail_status(self) -> None:
        line = _status_line("fail", 3, 12, color=False)
        assert line == "Health: FAIL (3 issues in 12 files)"

    def test_singular_issue(self) -> None:
        line = _status_line("warn", 1, 1, color=False)
        assert line == "Health: WARN (1 issue in 1 file)"

    def test_color_status(self) -> None:
        line = _status_line("fail", 1, 5, color=True)
        assert "\033[" in line
        assert "FAIL" in line
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_formatting.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'wos.formatting'`

**Step 3: Implement the color helpers and status line**

```python
"""Human-readable health report formatting.

Pure functions that take a health report dict and return formatted strings.
The report dict has keys: status, files_checked, issues, triggers, token_budget.
"""

from __future__ import annotations

from typing import Dict, List, Optional

# ── ANSI color codes ────────────────────────────────────────────

_COLORS: Dict[str, str] = {
    "fail": "\033[31m",   # red
    "warn": "\033[33m",   # yellow
    "info": "\033[2m",    # dim
    "pass": "\033[32m",   # green
}
_RESET = "\033[0m"

_SEVERITY_ORDER: Dict[str, int] = {"fail": 0, "warn": 1, "info": 2}


def _colorize(text: str, severity: str, *, color: bool) -> str:
    """Wrap text in ANSI color codes for the given severity."""
    if not color:
        return text
    code = _COLORS.get(severity, "")
    if not code:
        return text
    return f"{code}{text}{_RESET}"


def _status_line(
    status: str, issue_count: int, file_count: int, *, color: bool
) -> str:
    """Render the top-level status line."""
    label = status.upper()
    issues_word = "issue" if issue_count == 1 else "issues"
    files_word = "file" if file_count == 1 else "files"
    status_colored = _colorize(label, status, color=color)
    return (
        f"Health: {status_colored} "
        f"({issue_count} {issues_word} in {file_count} {files_word})"
    )
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_formatting.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add wos/formatting.py tests/test_formatting.py
git commit -m "feat: add color helpers and status line formatter (#15)"
```

---

### Task 2: Token Budget Formatter

**Files:**
- Modify: `wos/formatting.py`
- Modify: `tests/test_formatting.py`

**Context:** Both summary and detailed modes show a token budget line. Summary
shows a one-liner: `Token budget: 28,500 / 40,000`. Detailed shows per-area
breakdown beneath it. The token_budget dict from check_health.py has keys:
`total_estimated_tokens`, `warning_threshold`, `over_budget`, `areas` (list of
`{area, files, estimated_tokens}`).

**Step 1: Write the failing tests**

Add to `tests/test_formatting.py`:

```python
from wos.formatting import _format_token_budget


class TestFormatTokenBudget:
    def test_summary_one_liner(self) -> None:
        budget = {
            "total_estimated_tokens": 28500,
            "warning_threshold": 40000,
            "over_budget": False,
            "areas": [
                {"area": "python", "files": 5, "estimated_tokens": 18200},
                {"area": "testing", "files": 1, "estimated_tokens": 2000},
            ],
        }
        result = _format_token_budget(budget, detailed=False, color=False)
        assert result == "Token budget: 28,500 / 40,000"

    def test_detailed_with_areas(self) -> None:
        budget = {
            "total_estimated_tokens": 28500,
            "warning_threshold": 40000,
            "over_budget": False,
            "areas": [
                {"area": "python", "files": 5, "estimated_tokens": 18200},
                {"area": "testing", "files": 1, "estimated_tokens": 2000},
            ],
        }
        result = _format_token_budget(budget, detailed=True, color=False)
        assert "Token budget: 28,500 / 40,000 (2 areas)" in result
        assert "python" in result
        assert "18,200" in result
        assert "testing" in result

    def test_empty_budget(self) -> None:
        budget = {
            "total_estimated_tokens": 0,
            "warning_threshold": 40000,
            "over_budget": False,
            "areas": [],
        }
        result = _format_token_budget(budget, detailed=False, color=False)
        assert result == "Token budget: 0 / 40,000"

    def test_over_budget_colored(self) -> None:
        budget = {
            "total_estimated_tokens": 50000,
            "warning_threshold": 40000,
            "over_budget": True,
            "areas": [],
        }
        result = _format_token_budget(budget, detailed=False, color=True)
        assert "\033[33m" in result  # yellow for warn
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_formatting.py::TestFormatTokenBudget -v`
Expected: FAIL — `cannot import name '_format_token_budget'`

**Step 3: Implement the token budget formatter**

Add to `wos/formatting.py`:

```python
def _format_token_budget(
    budget: dict, *, detailed: bool, color: bool
) -> str:
    """Render token budget as a summary line or detailed breakdown."""
    total = budget["total_estimated_tokens"]
    threshold = budget["warning_threshold"]
    over = budget.get("over_budget", False)
    areas = budget.get("areas", [])

    headline = f"Token budget: {total:,} / {threshold:,}"
    if over and color:
        headline = _colorize(headline, "warn", color=True)

    if not detailed or not areas:
        return headline

    # Detailed: add area count and per-area lines
    headline += f" ({len(areas)} {'area' if len(areas) == 1 else 'areas'})"
    lines = [headline]

    # Find max area name length for alignment
    max_name = max(len(a["area"]) for a in areas) if areas else 0
    for area in areas:
        name = area["area"].ljust(max_name)
        tokens = f"{area['estimated_tokens']:,}"
        files = area["files"]
        files_word = "file" if files == 1 else "files"
        lines.append(f"  {name}  {tokens:>8} ({files} {files_word})")

    return "\n".join(lines)
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_formatting.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add wos/formatting.py tests/test_formatting.py
git commit -m "feat: add token budget formatter (#15)"
```

---

### Task 3: format_summary()

**Files:**
- Modify: `wos/formatting.py`
- Modify: `tests/test_formatting.py`

**Context:** `format_summary()` renders the compact one-line-per-issue view.
Format: status line, blank line, one line per issue (sorted: fail > warn > info,
then by file path), blank line, token budget line. Each issue line:
`  FAIL  context/area/topic.md        Missing required section: ## Guidance`
(severity label is 4 chars, right-padded, then file path, then issue text).

The report dict from `check_health.py` has this shape:
```python
{
    "status": "warn",
    "files_checked": 12,
    "issues": [{"file": "...", "issue": "...", "severity": "...", ...}],
    "triggers": [...],
    "token_budget": {...},
}
```

**Step 1: Write the failing tests**

Add to `tests/test_formatting.py`:

```python
from wos.formatting import format_summary


def _make_report(
    issues=None,
    status="pass",
    files_checked=5,
):
    """Build a minimal report dict for testing."""
    return {
        "status": status,
        "files_checked": files_checked,
        "issues": issues or [],
        "triggers": [],
        "token_budget": {
            "total_estimated_tokens": 1200,
            "warning_threshold": 40000,
            "over_budget": False,
            "areas": [],
        },
    }


class TestFormatSummary:
    def test_clean_report(self) -> None:
        report = _make_report()
        result = format_summary(report, color=False)
        assert "Health: PASS (0 issues in 5 files)" in result
        assert "Token budget:" in result

    def test_issues_sorted_by_severity(self) -> None:
        issues = [
            {"file": "b.md", "issue": "info issue", "severity": "info",
             "validator": "v", "section": None, "suggestion": None},
            {"file": "a.md", "issue": "fail issue", "severity": "fail",
             "validator": "v", "section": None, "suggestion": None},
            {"file": "c.md", "issue": "warn issue", "severity": "warn",
             "validator": "v", "section": None, "suggestion": None},
        ]
        report = _make_report(issues=issues, status="fail", files_checked=3)
        result = format_summary(report, color=False)
        lines = result.strip().split("\n")
        issue_lines = [
            l for l in lines
            if l.strip().startswith(("FAIL", "WARN", "INFO"))
        ]
        assert len(issue_lines) == 3
        assert "FAIL" in issue_lines[0]
        assert "WARN" in issue_lines[1]
        assert "INFO" in issue_lines[2]

    def test_issues_sorted_by_path_within_severity(self) -> None:
        issues = [
            {"file": "z.md", "issue": "issue z", "severity": "warn",
             "validator": "v", "section": None, "suggestion": None},
            {"file": "a.md", "issue": "issue a", "severity": "warn",
             "validator": "v", "section": None, "suggestion": None},
        ]
        report = _make_report(issues=issues, status="warn", files_checked=2)
        result = format_summary(report, color=False)
        lines = [
            l for l in result.split("\n") if l.strip().startswith("WARN")
        ]
        assert "a.md" in lines[0]
        assert "z.md" in lines[1]

    def test_no_issues_no_blank_issue_block(self) -> None:
        report = _make_report()
        result = format_summary(report, color=False)
        assert "\n\n\n" not in result
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_formatting.py::TestFormatSummary -v`
Expected: FAIL — `cannot import name 'format_summary'`

**Step 3: Implement format_summary**

Add to `wos/formatting.py`:

```python
def format_summary(report: dict, *, color: bool = False) -> str:
    """Render a compact one-line-per-issue health report."""
    status = report["status"]
    files_checked = report["files_checked"]
    issues = report.get("issues", [])
    budget = report.get("token_budget", {})

    parts: List[str] = []

    # Status line
    parts.append(
        _status_line(status, len(issues), files_checked, color=color)
    )

    # Issue lines
    if issues:
        parts.append("")  # blank line
        sorted_issues = sorted(
            issues,
            key=lambda i: (
                _SEVERITY_ORDER.get(i["severity"], 99),
                i["file"],
            ),
        )
        for issue in sorted_issues:
            sev = issue["severity"]
            label = _colorize(sev.upper().ljust(4), sev, color=color)
            parts.append(f"  {label}  {issue['file']}  {issue['issue']}")

    # Token budget
    if budget:
        parts.append("")
        parts.append(_format_token_budget(budget, detailed=False, color=color))

    return "\n".join(parts) + "\n"
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_formatting.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add wos/formatting.py tests/test_formatting.py
git commit -m "feat: add format_summary for compact health output (#15)"
```

---

### Task 4: format_detailed()

**Files:**
- Modify: `wos/formatting.py`
- Modify: `tests/test_formatting.py`

**Context:** `format_detailed()` groups issues by severity with suggestions.
Each severity group has a header (`Failures (N)`, `Warnings (N)`, `Info (N)`),
then issues indented under their file path with suggestion lines prefixed `→`.
Token budget shows per-area breakdown.

**Step 1: Write the failing tests**

Add to `tests/test_formatting.py`:

```python
from wos.formatting import format_detailed


class TestFormatDetailed:
    def test_groups_by_severity(self) -> None:
        issues = [
            {"file": "a.md", "issue": "broken", "severity": "fail",
             "validator": "v", "section": None, "suggestion": "Fix it"},
            {"file": "b.md", "issue": "stale", "severity": "info",
             "validator": "v", "section": None, "suggestion": "Review"},
        ]
        report = _make_report(issues=issues, status="fail", files_checked=2)
        result = format_detailed(report, color=False)
        assert "Failures (1)" in result
        assert "Info (1)" in result
        assert "Warnings" not in result

    def test_suggestion_arrow(self) -> None:
        issues = [
            {"file": "a.md", "issue": "bad", "severity": "warn",
             "validator": "v", "section": None, "suggestion": "Fix this"},
        ]
        report = _make_report(issues=issues, status="warn", files_checked=1)
        result = format_detailed(report, color=False)
        assert "\u2192 Fix this" in result

    def test_no_suggestion_no_arrow(self) -> None:
        issues = [
            {"file": "a.md", "issue": "bad", "severity": "warn",
             "validator": "v", "section": None, "suggestion": None},
        ]
        report = _make_report(issues=issues, status="warn", files_checked=1)
        result = format_detailed(report, color=False)
        assert "\u2192" not in result

    def test_multiple_issues_same_file_grouped(self) -> None:
        issues = [
            {"file": "a.md", "issue": "issue 1", "severity": "warn",
             "validator": "v", "section": None, "suggestion": None},
            {"file": "a.md", "issue": "issue 2", "severity": "warn",
             "validator": "v", "section": None, "suggestion": None},
        ]
        report = _make_report(issues=issues, status="warn", files_checked=1)
        result = format_detailed(report, color=False)
        # File path appears once as a header, both issues underneath
        lines = result.split("\n")
        file_lines = [l for l in lines if "a.md" in l and not l.startswith("    ")]
        assert len(file_lines) == 1

    def test_detailed_token_budget_shows_areas(self) -> None:
        report = _make_report()
        report["token_budget"] = {
            "total_estimated_tokens": 5000,
            "warning_threshold": 40000,
            "over_budget": False,
            "areas": [
                {"area": "python", "files": 3, "estimated_tokens": 5000},
            ],
        }
        result = format_detailed(report, color=False)
        assert "python" in result
        assert "5,000" in result

    def test_clean_report(self) -> None:
        report = _make_report()
        result = format_detailed(report, color=False)
        assert "Health: PASS" in result
        assert "Failures" not in result
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_formatting.py::TestFormatDetailed -v`
Expected: FAIL — `cannot import name 'format_detailed'`

**Step 3: Implement format_detailed**

Add to `wos/formatting.py`:

```python
_SEVERITY_LABELS: Dict[str, str] = {
    "fail": "Failures",
    "warn": "Warnings",
    "info": "Info",
}


def format_detailed(report: dict, *, color: bool = False) -> str:
    """Render a severity-grouped health report with suggestions."""
    status = report["status"]
    files_checked = report["files_checked"]
    issues = report.get("issues", [])
    budget = report.get("token_budget", {})

    parts: List[str] = []

    # Status line
    parts.append(
        _status_line(status, len(issues), files_checked, color=color)
    )

    # Group issues by severity
    for sev in ("fail", "warn", "info"):
        sev_issues = sorted(
            [i for i in issues if i["severity"] == sev],
            key=lambda i: i["file"],
        )
        if not sev_issues:
            continue

        label = _SEVERITY_LABELS[sev]
        count = len(sev_issues)
        header = _colorize(f"{label} ({count})", sev, color=color)
        parts.append("")
        parts.append(header)

        # Group by file within severity
        current_file: Optional[str] = None
        for issue in sev_issues:
            if issue["file"] != current_file:
                current_file = issue["file"]
                parts.append(f"  {current_file}")
            parts.append(f"    {issue['issue']}")
            if issue.get("suggestion"):
                parts.append(f"    \u2192 {issue['suggestion']}")

    # Token budget (detailed with areas)
    if budget:
        parts.append("")
        parts.append(
            _format_token_budget(budget, detailed=True, color=color)
        )

    return "\n".join(parts) + "\n"
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_formatting.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add wos/formatting.py tests/test_formatting.py
git commit -m "feat: add format_detailed for grouped health output (#15)"
```

---

### Task 5: Wire Formatters into CLI Script

**Files:**
- Modify: `scripts/check_health.py`
- Modify: `tests/test_check_health_integration.py`

**Context:** Currently `check_health.py` always outputs JSON via
`json.dumps(report, indent=2)`. Add `--detailed`, `--json`, and `--no-color`
flags. Default behavior changes from JSON to summary text. `--json` preserves
the exact current output. Existing integration tests that call `json.loads()`
on stdout need to pass `--json`.

The current `_run_health_script` helper (line 58-68) runs the script without
`--json`. Since default output is changing to text, update this helper to pass
`--json` so the existing `TestHealthScriptTokenBudget` and
`TestHealthScriptSourceReachability` tests keep working.

**Step 1: Write the failing integration tests**

Add a new helper and test class to `tests/test_check_health_integration.py`:

```python
def _run_health_script_with_flags(
    tmp_path: str, *flags: str
) -> subprocess.CompletedProcess:
    """Run health script with extra flags."""
    env = os.environ.copy()
    env["PYTHONPATH"] = PROJECT_ROOT
    return subprocess.run(
        [sys.executable, "scripts/check_health.py", "--root", tmp_path, *flags],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        env=env,
    )


class TestHealthOutputFormats:
    def test_default_is_text(self, tmp_path: Path) -> None:
        """Default output is human-readable text, not JSON."""
        area = tmp_path / "context" / "python"
        area.mkdir(parents=True)
        _write_topic(area, "error-handling")
        _write_overview(area, "python", ["error-handling"])

        result = _run_health_script_with_flags(str(tmp_path))
        assert result.stdout.startswith("Health:")

    def test_json_flag_preserves_current_behavior(self, tmp_path: Path) -> None:
        """--json outputs valid JSON matching existing schema."""
        area = tmp_path / "context" / "python"
        area.mkdir(parents=True)
        _write_topic(area, "error-handling")
        _write_overview(area, "python", ["error-handling"])

        result = _run_health_script_with_flags(str(tmp_path), "--json")
        report = json.loads(result.stdout)
        assert "status" in report
        assert "files_checked" in report
        assert "issues" in report
        assert "token_budget" in report

    def test_detailed_flag(self, tmp_path: Path) -> None:
        """--detailed outputs grouped text with suggestions."""
        area = tmp_path / "context" / "python"
        area.mkdir(parents=True)
        _write_topic(area, "error-handling")
        _write_overview(area, "python", ["error-handling"])

        result = _run_health_script_with_flags(str(tmp_path), "--detailed")
        assert result.stdout.startswith("Health:")
        assert "Token budget:" in result.stdout

    def test_no_color_flag(self, tmp_path: Path) -> None:
        """--no-color suppresses ANSI codes."""
        area = tmp_path / "context" / "python"
        area.mkdir(parents=True)
        _write_topic(area, "error-handling")
        _write_overview(area, "python", ["error-handling"])

        result = _run_health_script_with_flags(str(tmp_path), "--no-color")
        assert "\033[" not in result.stdout

    def test_exit_code_unchanged(self, tmp_path: Path) -> None:
        """Exit code 0 for pass, regardless of format."""
        area = tmp_path / "context" / "python"
        area.mkdir(parents=True)
        _write_topic(area, "error-handling")
        _write_overview(area, "python", ["error-handling"])

        text_result = _run_health_script_with_flags(str(tmp_path))
        json_result = _run_health_script_with_flags(str(tmp_path), "--json")
        assert text_result.returncode == 0
        assert json_result.returncode == 0
```

**Step 2: Run new tests to verify they fail**

Run: `python3 -m pytest tests/test_check_health_integration.py::TestHealthOutputFormats::test_default_is_text -v`
Expected: FAIL — default output is still JSON

**Step 3: Update check_health.py**

Add three new argparse arguments after the existing `--tier2`:

```python
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed output grouped by severity with suggestions",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON (machine-readable)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI color in text output",
    )
```

After `args = parser.parse_args()`, add:

```python
    if args.detailed and args.json:
        parser.error("--detailed and --json are mutually exclusive")
```

Replace the final output line (`print(json.dumps(report, indent=2))`) with:

```python
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        from wos.formatting import format_detailed, format_summary

        use_color = not args.no_color and sys.stdout.isatty()
        if args.detailed:
            print(format_detailed(report, color=use_color), end="")
        else:
            print(format_summary(report, color=use_color), end="")
```

**Step 4: Update `_run_health_script` to pass `--json`**

Change the existing helper so existing JSON-parsing tests still work:

```python
def _run_health_script(tmp_path: str) -> subprocess.CompletedProcess:
    """Run the health script as a subprocess with --json for backward compat."""
    env = os.environ.copy()
    env["PYTHONPATH"] = PROJECT_ROOT
    return subprocess.run(
        [
            sys.executable, "scripts/check_health.py",
            "--root", tmp_path, "--json",
        ],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        env=env,
    )
```

**Step 5: Run all tests to verify they pass**

Run: `python3 -m pytest tests/test_check_health_integration.py tests/test_formatting.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add scripts/check_health.py tests/test_check_health_integration.py
git commit -m "feat: wire formatters into CLI with --detailed, --json, --no-color (#15)"
```

---

### Task 6: Update Health Skill Workflows

**Files:**
- Modify: `skills/health/SKILL.md`
- Modify: `skills/health/references/health-check-workflow.md`
- Modify: `skills/health/references/health-audit-workflow.md`
- Modify: `skills/health/references/health-freshness-workflow.md`

**Context:** Now that Python renders human-readable text, skill workflows no
longer need to instruct the LLM to parse JSON and format results. Simplify
each workflow to run the command and show output.

**Step 1: Update SKILL.md**

Replace the Implementation section (lines 30-52) with:

```markdown
## Implementation

All validation runs through the CLI script:

```bash
# Tier 1 only (default, CI-friendly)
python3 scripts/check_health.py --root .

# Detailed output with suggestions
python3 scripts/check_health.py --root . --detailed

# Tier 1 + Tier 2 triggers
python3 scripts/check_health.py --root . --tier2

# JSON output for programmatic use
python3 scripts/check_health.py --root . --json
```

Default output is human-readable text. Use `--json` for machine-parseable output.

Exit code: 0 if no `severity: fail`, 1 otherwise.
```

**Step 2: Replace health-check-workflow.md**

```markdown
# Health Check Workflow (Tier 1)

Run deterministic validation across all documents.

## Steps

1. **Run the health check script**
   ```bash
   python3 scripts/check_health.py --root . --no-color
   ```

2. **Show the output** directly to the user — the script formats results as
   human-readable text with issues sorted by severity.

3. **If the user wants more detail**, re-run with `--detailed`:
   ```bash
   python3 scripts/check_health.py --root . --detailed --no-color
   ```

4. **Suggest next steps**:
   - If failures exist: recommend specific fixes or `/wos:maintain`
   - If warnings only: suggest reviewing and optionally fixing
   - If clean: congratulate and suggest `/wos:health audit` for deeper check
```

**Step 3: Replace health-audit-workflow.md**

```markdown
# Health Audit Workflow (Tier 1 + Tier 2)

Run deterministic checks plus LLM-assisted quality assessment.

## Steps

1. **Run the health check with tier 2 triggers**
   ```bash
   python3 scripts/check_health.py --root . --tier2 --json
   ```

2. **Show Tier 1 issues** — run the text formatter for human-readable output:
   ```bash
   python3 scripts/check_health.py --root . --detailed --no-color
   ```

3. **Evaluate Tier 2 triggers** — parse the JSON output's `triggers` list.
   For each trigger:
   - Read the context dict (document excerpt, section content, etc.)
   - Assess quality based on the trigger's question
   - Report findings with severity and specific suggestions

4. **Present combined results** — T1 text output + T2 assessments
```

**Step 4: Replace health-freshness-workflow.md**

```markdown
# Health Freshness Workflow

Report on document staleness based on `last_validated` dates.

## Thresholds

| Age | Severity | Label |
|-----|----------|-------|
| 30+ days | info | Getting stale |
| 60+ days | warn | Needs attention |
| 90+ days | stale | Overdue for review |

## Steps

1. **Run the health check script**
   ```bash
   python3 scripts/check_health.py --root . --detailed --no-color
   ```

2. **Filter the output** to only staleness-related findings
   (issues mentioning "validated" or "days ago")

3. **Group by urgency** — 90+ days first, then 60+, then 30+

4. **Present report** with suggested review priorities
```

**Step 5: Commit**

```bash
git add skills/health/SKILL.md skills/health/references/health-check-workflow.md skills/health/references/health-audit-workflow.md skills/health/references/health-freshness-workflow.md
git commit -m "docs: update health skill workflows for text output (#15)"
```

---

### Task 7: Version Bump and Changelog

**Files:**
- Modify: `pyproject.toml` (line 7)
- Modify: `.claude-plugin/plugin.json` (line 3)
- Modify: `.claude-plugin/marketplace.json` (line 14)
- Modify: `CHANGELOG.md`

**Context:** Bump version from 0.1.8 to 0.1.9. Add changelog entry.

**Step 1: Bump version in all three files**

`pyproject.toml` line 7: `version = "0.1.8"` → `version = "0.1.9"`
`.claude-plugin/plugin.json` line 3: `"version": "0.1.8"` → `"version": "0.1.9"`
`.claude-plugin/marketplace.json` line 14: `"version": "0.1.8"` → `"version": "0.1.9"`

**Step 2: Add changelog entry**

Add after the `## [Unreleased]` line:

```markdown
## [0.1.9] - 2026-02-19

### Changed

- **Human-readable health output** is now the default. `scripts/check_health.py`
  outputs formatted text with issues sorted by severity, one line per issue in
  summary mode, or grouped by severity with suggestions in `--detailed` mode.
  JSON output preserved via `--json` flag. Basic ANSI color auto-detected on
  TTY, disabled with `--no-color`.
  ([#15](https://github.com/bcbeidel/wos/issues/15))
- Health skill workflows simplified to show text output directly instead of
  instructing the LLM to parse and format JSON.
```

Add release link at the bottom:

```markdown
[0.1.9]: https://github.com/bcbeidel/wos/releases/tag/v0.1.9
```

**Step 3: Run full test suite**

Run: `python3 -m pytest tests/ -v`
Expected: All tests pass

**Step 4: Commit**

```bash
git add pyproject.toml .claude-plugin/plugin.json .claude-plugin/marketplace.json CHANGELOG.md
git commit -m "chore: bump version to 0.1.9 (#15)"
```
