---
name: Developer Experience
description: Mirror enforcement in CI, document bootstrap, and keep `rev:` pins fresh via a regular `pre-commit autoupdate` cadence.
paths:
  - "**/.pre-commit-config.yaml"
  - "**/.pre-commit-config.yml"
---

**Why:** A hook config without these supports rots — *Mirror enforcement in CI*, *Document bootstrap in README*, *Run `pre-commit autoupdate` on a regular cadence*, *Leave `--no-verify` working*. Without a CI mirror, local pre-commit and CI diverge — what passes one fails the other, producing unreproducible failures. Without README bootstrap, new contributors don't run `pre-commit install`, hooks never fire, the gate is theatre. Without an autoupdate cadence, `rev:` pins drift 18+ months stale, missing security fixes and breaking against newer language versions.

**How to apply:** Confirm a CI workflow exists (`.github/workflows/*.yml` running `pre-commit run --all-files`, or a `pre-commit.ci` badge / config). Confirm bootstrap is documented (README mentions `pre-commit install`, or `make setup` / `husky install` includes it). Confirm autoupdate cadence is visible — a recent dated commit, a scheduled workflow, or an external service like `pre-commit.ci` running it.

```yaml
# .github/workflows/pre-commit.yml
name: pre-commit
on: [pull_request]
jobs:
  pre-commit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - uses: pre-commit/action@v3.0.1
```

**Common fail signals (audit guidance):** Config exists, no CI mirror (local / CI divergence risk); no README mention of `pre-commit install` (new contributor won't know to enable it); `rev:` pins untouched for 18+ months.
