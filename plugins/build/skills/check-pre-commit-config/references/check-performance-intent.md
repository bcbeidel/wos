---
name: Performance Intent
description: Keep commit-time hooks under ~2–5s — no test runners, no whole-repo type checkers — serialize file-mutators, and order formatters before linters.
paths:
  - "**/.pre-commit-config.yaml"
  - "**/.pre-commit-config.yml"
---

Keep commit-time hooks under ~2–5s — no test runners, no whole-repo type checkers — serialize file-mutators, and order formatters before linters.

**Why:** Slow pre-commit hooks get bypassed — *Target runtime under ~2–5s*, *Do not run full test suites / whole-repo type checkers*, *File-mutating hooks declare `require_serial: true`*, *Run formatters before linters*. A pytest hook turns every commit into a coffee break; a `mypy .` hook ignores the staged-files list and re-types-checks the world. File-mutators run in parallel race on shared files (intermittent corruption that surfaces only under load); linters run before formatters report issues the formatter would have fixed.

**How to apply:** Confirm no `pytest`, `go test`, `cargo test`, `npm test`, `mypy .` (whole-repo), `pyright`, `tsc` (whole-repo) appear in the commit stage — those belong in `pre-push` or CI. Confirm every formatter (Black, Prettier, gofmt, rustfmt, Ruff+`--fix`, ESLint+`--fix`, shfmt, clang-format, `terraform fmt`) declares `require_serial: true`. Confirm formatter hooks appear before linter hooks in the repos list.

```yaml
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks:
      - id: ruff-format          # formatter first
        require_serial: true
      - id: ruff                  # linter second, sees formatted code
```

**Common fail signals (audit guidance):** An `id: mypy` hook with `args: [.]` (whole repo); a `pytest` hook; Black / Ruff-format / Prettier without `require_serial: true`; `ruff` (lint) listed before `ruff-format`.
