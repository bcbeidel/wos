---
name: uv run Preflight Implementation Plan
description: Step-by-step implementation for reliable uv run invocation from skills
type: plan
related:
  - artifacts/plans/2026-02-26-uv-run-preflight-design.md
---

# uv run Preflight Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable WOS skills to reliably invoke `uv run` with PEP 723 scripts by providing a canary validation script and reusable preflight reference doc.

**Architecture:** A `scripts/check_runtime.py` PEP 723 canary tests the full uv pipeline. A shared `skills/_shared/references/preflight.md` reference doc gives any skill the preflight pattern. Skills include the reference and follow it before any `uv run` call.

**Tech Stack:** Python 3.9+, uv, PEP 723 inline metadata, httpx (canary dep)

**Issue:** [#70](https://github.com/bcbeidel/wos/issues/70)
**Branch:** `feat/70-uv-run-preflight`
**PR:** TBD

---

### Task 1: Canary Script

**Files:**
- Create: `scripts/check_runtime.py`
- Test: `tests/test_check_runtime.py`

**Step 1: Write the failing test**

```python
"""Tests for scripts/check_runtime.py — uv run canary."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


class TestCheckRuntimeDirect:
    """Test check_runtime.py when run directly with python3 (no uv)."""

    def test_fails_without_httpx(self, tmp_path: Path) -> None:
        """Without uv, httpx won't be available — script should fail."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "check_runtime.py")],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )
        # Should fail because httpx isn't installed in our test env
        output = json.loads(result.stdout)
        assert output["status"] == "fail"
        assert result.returncode == 1

    def test_output_is_valid_json(self, tmp_path: Path) -> None:
        """Output should always be valid JSON regardless of success/failure."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "check_runtime.py")],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )
        parsed = json.loads(result.stdout)
        assert "status" in parsed


class TestCheckRuntimeHelp:
    def test_help_flag(self, tmp_path: Path) -> None:
        """--help should work and exit 0."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "check_runtime.py"), "--help"],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )
        assert result.returncode == 0
        assert "canary" in result.stdout.lower() or "verify" in result.stdout.lower()
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_check_runtime.py -v`
Expected: FAIL — `scripts/check_runtime.py` does not exist yet

**Step 3: Write the canary script**

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["httpx"]
# ///
"""Canary: verify uv can run PEP 723 scripts with inline dependencies.

Usage:
    uv run scripts/check_runtime.py
    python3 scripts/check_runtime.py  (will fail without httpx — expected)
"""
from __future__ import annotations

import argparse
import json
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify uv + PEP 723 dependency resolution pipeline.",
    )
    parser.parse_args()

    try:
        import httpx

        print(
            json.dumps(
                {
                    "status": "ok",
                    "python": sys.version.split()[0],
                    "httpx": httpx.__version__,
                }
            )
        )
    except ImportError:
        print(
            json.dumps(
                {
                    "status": "fail",
                    "error": "httpx import failed — uv dependency resolution did not run",
                }
            )
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_check_runtime.py -v`
Expected: PASS — both tests should pass (script fails gracefully without httpx)

**Step 5: Commit**

```bash
git add scripts/check_runtime.py tests/test_check_runtime.py
git commit -m "feat: add check_runtime.py canary script for uv preflight (#70)"
```

---

### Task 2: Shared Preflight Reference Doc

**Files:**
- Create: `skills/_shared/references/preflight.md`

**Step 1: Create the shared references directory and preflight doc**

```markdown
# uv run Preflight Check

Skills that invoke `uv run` MUST run this preflight sequence before the
actual script. This catches missing tools early with actionable errors.

## Steps

### 1. Check uv availability

```bash
uv --version
```

If the command fails (not found):
- Tell the user: **"uv is required but not installed. Install it with:
  `curl -LsSf https://astral.sh/uv/install.sh | sh` — then restart your
  terminal."**
- **STOP.** Do not attempt to run the script.

### 2. Run the canary script

```bash
uv run <plugin-scripts-dir>/check_runtime.py
```

Where `<plugin-scripts-dir>` is the `scripts/` directory at the root of this
plugin (sibling to the `skills/` directory containing this reference file).

Parse the JSON output:
- If `"status": "ok"` — proceed to step 3.
- If `"status": "fail"` or non-zero exit — tell the user:
  **"uv cannot resolve PEP 723 inline dependencies. Check your network
  connection and proxy settings."** Then show the error from the JSON output.
  **STOP.**

### 3. Run the actual script

```bash
uv run <plugin-scripts-dir>/<script-name>.py [arguments]
```

If the script itself fails (non-zero exit), show stderr to the user.

## Error Reference

| Failure | User Message |
|---------|-------------|
| `uv` not in PATH | "uv is required but not installed. Install: `curl -LsSf https://astral.sh/uv/install.sh \| sh`" |
| Canary returns `"fail"` | "uv cannot resolve PEP 723 dependencies. Check network/proxy settings." |
| Canary non-zero exit | Show stderr output from the canary |
| Target script fails | Show stderr output from the target script |

## Skill Integration

Add this reference to any skill that uses `uv run`:

```yaml
references:
  - ../_shared/references/preflight.md
```

Then in the skill's instructions, reference the preflight steps:
"Before running any `uv run` command, follow the preflight check in the
preflight reference."
```

**Step 2: Verify the file exists and is well-formed**

Run: `cat skills/_shared/references/preflight.md | head -5`
Expected: Shows the title line

**Step 3: Commit**

```bash
git add skills/_shared/references/preflight.md
git commit -m "docs: add shared preflight reference for uv run skills (#70)"
```

---

### Task 3: Verify End-to-End (Manual)

**This task validates the full pipeline if `uv` is installed locally.**

**Step 1: Check if uv is available**

Run: `uv --version`
Expected: Version string (e.g., `uv 0.6.x`) or "command not found"

**Step 2: If uv is available, run the canary**

Run: `uv run scripts/check_runtime.py`
Expected: `{"status": "ok", "python": "3.x.x", "httpx": "0.x.x"}`

**Step 3: If uv is NOT available, verify graceful failure**

Run: `python3 scripts/check_runtime.py`
Expected: `{"status": "fail", "error": "httpx import failed — uv dependency resolution did not run"}` + exit code 1

**Step 4: Commit any fixes needed**

If anything broke, fix and commit.

---

### Task 4: Update Design Doc and Run Full Tests

**Files:**
- Modify: `artifacts/plans/2026-02-26-uv-run-preflight-design.md` (check off acceptance criteria)

**Step 1: Run full test suite**

Run: `python3 -m pytest tests/ -v`
Expected: All tests pass

**Step 2: Run linter (if available)**

Run: `ruff check wos/ tests/ scripts/`
Expected: No errors (ruff may not be installed locally)

**Step 3: Update design doc — check off completed criteria**

Mark acceptance criteria as done in the design doc.

**Step 4: Final commit**

```bash
git add artifacts/plans/2026-02-26-uv-run-preflight-design.md
git commit -m "docs: mark preflight acceptance criteria complete (#70)"
```
