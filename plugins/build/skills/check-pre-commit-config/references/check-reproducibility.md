---
name: Reproducibility
description: Pin the pre-commit runner version, every `rev:`, and every language version so the config produces the same hooks on every machine and over time.
paths:
  - "**/.pre-commit-config.yaml"
  - "**/.pre-commit-config.yml"
---

**Why:** Reproducibility is the hook system's whole premise — *Framework over hand-rolled*, *Immutable `rev:` pins*, and *Pin `language_version`*. A floating `rev:` (`main`, partial tag like `v4`, 7-char SHA) produces different hook versions on different machines and at different times; an unpinned `language_version` runs hooks against whatever interpreter is first in `$PATH`. Both turn the config into a moving target — what passed yesterday fails today, and the failure is unattributable.

**How to apply:** Confirm `minimum_pre_commit_version` is set and matches the version CI tests. Verify every non-`local` `rev:` is a full semver tag (`vX.Y.Z`) or a 40-char SHA — reject `main`, `master`, `HEAD`, `latest`, `v4` (partial), `1234abc` (short SHA), or date-strings. Verify `default_language_version` (or per-hook `language_version`) covers every language-specific hook. Run `pre-commit autoupdate` to produce an auditable repin to current stable tags.

```yaml
minimum_pre_commit_version: "3.7.0"

default_language_version:
  python: python3.11

repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks:
      - id: ruff
```

**Common fail signals (audit guidance):** `rev: v4` (partial tag — not immutable across minor releases), `rev: 1234abc` (7-char SHA — not immutable across history rewrites), no `language_version` on a Python hook.
