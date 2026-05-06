---
name: Maintainability
description: Keep workflows single-purpose, extract `run:` blocks past ~20 lines into `.github/scripts/`, consolidate duplicated logic into reusable workflows or composite actions, use kebab-case IDs, scope `env:` narrowly, and set explicit `name:` and `retention-days:` on every uploaded artifact.
paths:
  - "**/.github/workflows/*.yml"
  - "**/.github/workflows/*.yaml"
---

Keep each workflow single-purpose with a name and trigger set that tell a coherent story, extract any `run:` block longer than ~20 non-blank lines into `.github/scripts/<name>.sh`, consolidate logic duplicated across jobs into a reusable workflow (`workflow_call`) or composite action, use kebab-case for every job and step ID, scope `env:` blocks at the narrowest useful level (step > job > workflow), and set explicit `name:` and `retention-days:` on every `actions/upload-artifact`.

**Why:** Multi-purpose workflows accumulate unrelated triggers and jobs that drift independently — every change risks touching unrelated work, and the file becomes a maintenance tarpit. Past ~20 lines of YAML, embedded shell is the wrong place for code: `shellcheck` cannot see inside a heredoc, tests cannot exercise the logic, and diff review is painful. Copy-paste workflows drift between callers; reusable workflows and composite actions keep a single source of truth so bug fixes and pinning bumps apply atomically. Mixed-case IDs hurt readability and break downstream consumers (URLs, required-check names) that normalize case differently. Workflow-level `env:` blocks expose values to every step including third-party actions; step-scoping is the smallest blast radius. Artifacts without an explicit `retention-days:` use the repo default (often 90 days) and accumulate storage cost.

**How to apply:** Read the workflow's `name:` and trigger set together — does it tell one coherent story, or is it an omnibus file mixing CI, release, and scheduled audits? Count non-blank lines in every `run:` block and flag any over ~20 for extraction to `.github/scripts/<name>.sh`. Walk multiple jobs and look for duplicated step sequences (especially `harden-runner` + `checkout` + `setup-*` preambles) that warrant a composite action; look for duplicated job bodies that warrant a reusable workflow. Confirm every job and step ID matches `^[a-z][a-z0-9-]*$`. Confirm `env:` blocks live at the narrowest useful scope. Confirm every `actions/upload-artifact` step sets both `name:` and `retention-days:`.

```yaml
jobs:
  build-and-test:
    name: Build and test
    timeout-minutes: 20
    steps:
      - name: Build
        run: bash .github/scripts/build.sh
      - name: Run tests
        env:
          TEST_DB_URL: ${{ secrets.TEST_DB_URL }}
        run: bash .github/scripts/test.sh
      - name: Upload coverage report
        uses: actions/upload-artifact@<SHA>
        with:
          name: coverage-report
          path: coverage/
          retention-days: 14
```

**Common fail signals (audit guidance):** Workflow is multi-purpose, `run:` blocks exceed ~20 lines, logic duplicated across jobs, non-kebab-case IDs, broad `env:` scoping, artifacts missing `name`/`retention-days`.
