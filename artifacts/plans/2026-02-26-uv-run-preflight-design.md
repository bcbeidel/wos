---
name: uv run Preflight Design
description: Design for reliable uv run invocation from WOS skills
type: plan
related:
  - artifacts/plans/2026-02-26-google-docs-read-design.md
---

# Reliable `uv run` Invocation from Skills

**Issue:** [#70](https://github.com/bcbeidel/wos/issues/70)
**Branch:** `feat/70-uv-run-preflight`
**Status:** Implementation complete

## Problem

Skills that need to run Python scripts with external dependencies (via `uv run`
+ PEP 723 inline metadata) have no reliable invocation pattern. Three problems:

1. **`uv` availability** — `uv` may not be installed or in PATH
2. **Script path resolution** — WOS plugin is installed to a cache directory;
   skills need to resolve the absolute path to `scripts/`
3. **PEP 723 dep resolution** — No verification that `uv run` can actually
   install inline dependencies

This blocks #41 (Google Docs read) and any future integration needing external
Python dependencies.

## Design Decisions

- **Approach:** Canary script + reusable skill reference doc (vs shell wrapper
  or Python preflight module)
- **Path resolution:** Claude infers plugin root from cache location when
  loading SKILL.md — no env var needed (`CLAUDE_PLUGIN_ROOT` doesn't exist)
- **Failure mode:** Actionable error message + stop (no auto-install, no
  fallback to pip/venv)
- **Canary dependency:** `httpx` — real dependency that integrations will use
- **Shared references:** New `skills/_shared/references/` directory for
  cross-skill reference docs

## Components

### 1. Canary Script: `scripts/check_runtime.py`

Minimal PEP 723 script that validates the full pipeline: uv availability,
dependency resolution, and import success.

```python
# /// script
# requires-python = ">=3.9"
# dependencies = ["httpx"]
# ///
```

- Imports `httpx`, outputs JSON: `{"status": "ok", "python": "3.x.x", "httpx": "0.x.x"}`
- On failure: `{"status": "fail", "error": "..."}` + exit code 1
- Tests: verify JSON output format, verify exit codes

### 2. Preflight Reference Doc: `skills/_shared/references/preflight.md`

Reusable reference doc that any skill needing `uv run` includes. Tells Claude:

1. Check `uv --version` — if missing, show install instructions and STOP
2. Run canary `uv run <plugin-scripts-dir>/check_runtime.py` — if fails, STOP
3. Proceed with actual `uv run <plugin-scripts-dir>/<script>.py`

Error messages:

| Failure | Message |
|---------|---------|
| uv not found | "uv is required. Install: `curl -LsSf https://astral.sh/uv/install.sh | sh`" |
| Canary fails | "uv cannot resolve PEP 723 dependencies. Check network/proxy settings." |
| Script fails | Show the script's stderr output to the user |

### 3. Skill Integration Pattern

Skills that need `uv run` add the reference:

```yaml
references:
  - ../_shared/references/preflight.md
```

Then follow the preflight steps before any `uv run` invocation.

## What We're NOT Building

- No shell wrapper script
- No Python preflight module in `wos/`
- No auto-install of uv
- No fallback to pip/venv
- No changes to existing skills (they don't use `uv run`)

## Acceptance Criteria

- [x] `scripts/check_runtime.py` exists and validates uv + PEP 723 deps
- [x] `skills/_shared/references/preflight.md` documents the preflight pattern
- [x] Pattern is documented for skill authors
- [x] Tests for canary script output format
- [x] Works on macOS and Linux
