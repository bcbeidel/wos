---
name: Correctness & Error Handling
description: Set `timeout-minutes` on every job, prepend `set -euo pipefail` to every multi-line bash `run:`, set `defaults.run.shell: bash` at workflow level, justify any `continue-on-error: true`, and use `if: always() && needs.*.result` patterns instead of bare `if: failure()`.
paths:
  - "**/.github/workflows/*.yml"
  - "**/.github/workflows/*.yaml"
---

Give every job a deliberate `timeout-minutes:` value, prepend `set -euo pipefail` to every multi-line bash `run:` block, set `defaults.run.shell: bash` at workflow level, reserve `continue-on-error: true` for explicitly non-blocking steps with an inline justification, and prefer `if: always() && needs.<job>.result == '<val>'` over bare `if: failure()` in dependent jobs.

**Why:** The runner default `timeout-minutes` is 360 — a hung job at that ceiling burns $40+ of compute per incident and masks a hang you wanted to see fail fast. Bash defaults silently swallow pipeline failures and unset-variable typos; `set -euo pipefail` turns those into loud, early exits — the exact class of bug CI is supposed to catch. The default `run:` shell differs across runner OSes (bash on Linux/macOS, PowerShell on Windows), and the same `run:` body behaves differently across runners without `defaults.run.shell: bash`. Unjustified `continue-on-error: true` on test, build, deploy, or security-scan steps quietly demotes failures into green checks, eroding trust in every signal. Bare `if: failure()` is brittle across `needs:` chains — the explicit `needs.<job>.result` form is unambiguous.

**How to apply:** Walk every job and confirm `timeout-minutes:` is set to a deliberate value (not just a default, and not absurdly high). Walk every multi-line bash `run:` block and confirm it begins with `set -euo pipefail` (or equivalent — `set -e`, `set -u`, `set -o pipefail` separately). Confirm `defaults.run.shell: bash` is set at workflow level. Walk every `continue-on-error: true` and confirm an inline comment justifies use; flag any on test, build, deploy, or security-scan steps. Walk every conditional step in dependent jobs and prefer `if: always() && needs.<job>.result == 'failure'` over bare `if: failure()`. Confirm `needs:` relationships are declared explicitly.

```yaml
defaults:
  run:
    shell: bash

jobs:
  test:
    name: Unit tests
    timeout-minutes: 20
    steps:
      - name: Run tests
        run: |
          set -euo pipefail
          pytest -v
      - name: Upload coverage
        if: always()
        continue-on-error: true   # advisory: coverage upload must not fail the run
        uses: codecov/codecov-action@<SHA>

  notify:
    needs: test
    if: always() && needs.test.result == 'failure'
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: echo "test failed"
```

**Common fail signals (audit guidance):** Missing `timeout-minutes`, missing `set -euo pipefail`, missing `defaults.run.shell: bash`, unjustified `continue-on-error: true`, or brittle `if: failure()` patterns.
