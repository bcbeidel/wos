---
name: Trigger Discipline
description: Scope workflow triggers narrowly with `paths:`, `branches:`, and `types:` filters; choose `pull_request` over `pull_request_target` unless elevation is required; randomize `schedule` cron minutes; type `workflow_dispatch` inputs.
paths:
  - "**/.github/workflows/*.yml"
  - "**/.github/workflows/*.yaml"
---

Scope every workflow trigger to the smallest set of events that match the workflow's stated purpose, choose `pull_request` over `pull_request_target` unless elevated permissions or secrets are genuinely required, randomize `schedule` cron minutes, and type every `workflow_dispatch` input.

**Why:** Unfiltered triggers burn runner minutes, generate noisy required-check rows, and create surprise runs on unrelated changes. `pull_request_target` is the most-exploited trigger in the GitHub Actions ecosystem — choosing it without need expands the attack surface for no benefit. Cron expressions at minute 0 thunder-herd onto GitHub's runner pool every hour and queue. Untyped `workflow_dispatch` inputs leak free-form strings into shell contexts and produce unpredictable behavior across maintainer-vs-bot invocations. The trigger set is the workflow's first contract with the rest of the repo; sloppy triggers compound into all subsequent costs.

**How to apply:** Match the trigger set to the workflow's stated purpose — CI on `pull_request`, releases on tag push, scheduled audits on `schedule`, manual ops on `workflow_dispatch`. Narrow with `paths:`, `branches:`, and `types:` filters where they make sense. Switch `pull_request_target` to `pull_request` unless the workflow demonstrably needs secrets or elevated permissions on fork PRs. Randomize cron minutes (`17 3 * * *`, not `0 3 * * *`). Type every `workflow_dispatch` input (`type: choice`, `type: boolean`, `type: number`) and document each input's purpose. Flag mismatches between the trigger set and the workflow's name or job structure as evidence of trigger sprawl.

```yaml
on:
  pull_request:
    branches: [main]
    paths:
      - "src/**"
      - ".github/workflows/ci.yml"
  schedule:
    - cron: "17 3 * * *"
  workflow_dispatch:
    inputs:
      environment:
        description: Target environment
        type: choice
        options: [staging, production]
        required: true
```

**Common fail signals (audit guidance):** Trigger filters absent, `pull_request_target` used without clear justification, `schedule` cron at minute 0, or `workflow_dispatch` inputs untyped.
