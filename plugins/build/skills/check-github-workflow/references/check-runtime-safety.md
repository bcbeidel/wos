---
name: Runtime Safety
description: Prepend `step-security/harden-runner` to every job, set `persist-credentials: false` on `actions/checkout`, route user-controlled context through `env:` before reaching `run:`, and never check out PR code under `pull_request_target`.
paths:
  - "**/.github/workflows/*.yml"
  - "**/.github/workflows/*.yaml"
---

Make `step-security/harden-runner` the first step of every job, set `persist-credentials: false` on every `actions/checkout` unless the job explicitly needs to push, route every `${{ github.event.* }}` / `${{ github.head_ref }}` / `${{ inputs.* }}` expression through a step-level `env:` block before any `run:` body sees it, and remove any PR-code checkout from a `pull_request_target` workflow.

**Why:** Static pinning catches known-bad SHAs; runtime defenses catch the novel compromise at the egress or injection point. `harden-runner` provides egress monitoring that surfaces unexpected outbound connections — the tj-actions compromise would have appeared in egress logs before secret exfiltration completed. The default `actions/checkout` leaves a usable `GITHUB_TOKEN` written to `.git/config` for the rest of the job, where every subsequent action can read it; `persist-credentials: false` reduces that blast radius. Direct `${{ }}` interpolation into `run:` text is shell injection — a PR title of `"; rm -rf / #` executes as shell. The `pull_request_target` + PR-checkout combination is the textbook GitHub Actions CVE vector and has no safe form.

**How to apply:** Walk every job and confirm the first step is `step-security/harden-runner` (SHA-pinned) with `egress-policy: audit` or `block`. Walk every `actions/checkout` step and confirm `persist-credentials: false` unless a subsequent `git push` or push-shaped action exists in the same job. Search every multi-line `run:` block for direct `${{ github.event.* }}`, `${{ github.head_ref }}`, `${{ inputs.* }}`, or `${{ github.ref_name }}` interpolations — these must instead live in a per-step `env:` block and be referenced via shell variable expansion (`"$VAR"`). For `pull_request_target` workflows, verify no `actions/checkout` step references the PR head ref (`github.event.pull_request.head.*`, `github.head_ref`).

```yaml
jobs:
  triage:
    steps:
      - name: Harden runner
        uses: step-security/harden-runner@<SHA>
        with:
          egress-policy: audit
      - uses: actions/checkout@<SHA>
        with:
          persist-credentials: false
          fetch-depth: 1
      - name: Echo title safely
        env:
          TITLE: ${{ github.event.issue.title }}
        run: |
          set -euo pipefail
          echo "Title: $TITLE"
```

**Common fail signals (audit guidance):** Missing `harden-runner`, `persist-credentials: true` (default), user-controlled context in `run:` bodies, or `pull_request_target` with PR-code checkout.
