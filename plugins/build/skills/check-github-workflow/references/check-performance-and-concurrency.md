---
name: Performance & Concurrency
description: Define workflow-level `concurrency` with `cancel-in-progress: true` for PR/push (false for deploy/release), key caches on lockfile hashes, prefer `setup-*` `cache:` over hand-rolled `actions/cache`, gate costly jobs with `paths:` filters, and set explicit `fetch-depth: 1` on checkout.
paths:
  - "**/.github/workflows/*.yml"
  - "**/.github/workflows/*.yaml"
---

Define `concurrency` at workflow level with `cancel-in-progress: true` for PR/push workflows and `false` (or omitted) for deploy/release workflows, derive cache keys from a lockfile hash via `hashFiles(...)`, prefer the `cache:` option on `setup-node`/`setup-python`/`setup-java` over a hand-rolled `actions/cache` entry, gate costly jobs with `paths:` filters, and set an explicit `fetch-depth` (usually `1`) on `actions/checkout`.

**Why:** Without concurrency, force-pushes pile up queued runs and waste minutes; the `workflow + ref` group key is the standard, and `ref` isolates PR runs from branch pushes. Cancelling a deploy mid-run leaves systems in inconsistent states — deploys get serialization (the group) but never cancellation. Cache keys not derived from a lockfile hash are stale-by-default; the hash key invalidates exactly when dependencies change. The `setup-*` `cache:` option encodes the right cache path and key shape for each ecosystem and is less error-prone than a hand-rolled `actions/cache` block. `paths:` filters keep costly jobs from firing on documentation-only changes. The default checkout fetches full history; for most jobs `fetch-depth: 1` is sufficient and materially faster on large repos.

**How to apply:** Confirm a workflow-level `concurrency:` block exists with `group: ${{ github.workflow }}-${{ github.ref }}` (or equivalent) and `cancel-in-progress: true` for PR/push workflows; confirm deploy/release workflows omit cancellation or set it to `false`. Walk every dependency-install job and confirm a cache strategy is in place: prefer the `setup-*` `cache:` option; if `actions/cache` is used, confirm `key:` is derived from `hashFiles('**/package-lock.json')` / `hashFiles('**/poetry.lock')` / equivalent rather than a static string. Walk every `actions/checkout` and confirm `fetch-depth: 1` (unless the job genuinely needs history — releases, blame analysis). Flag costly jobs (build, e2e, integration) that lack `paths:` or conditional `if:` gating.

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@<SHA>
        with:
          persist-credentials: false
          fetch-depth: 1
      - uses: actions/setup-node@<SHA>
        with:
          node-version: "20"
          cache: npm
      - run: npm ci
```

**Common fail signals (audit guidance):** Missing or misconfigured `concurrency`, cache keys not keyed on lockfile hash, hand-rolled `actions/cache` where `setup-*` caching would do, missing `paths:` filters on costly jobs, `fetch-depth: 0` without a reason.
