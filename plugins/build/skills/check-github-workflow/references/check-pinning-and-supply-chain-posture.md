---
name: Pinning & Supply-Chain Posture
description: SHA-pin every `uses:` reference, document any first-party tag exemption with Dependabot coverage, pin Docker images to non-`latest` tags or `@sha256:` digests, and verify the repo carries a `github-actions` Dependabot config.
paths:
  - "**/.github/workflows/*.yml"
  - "**/.github/workflows/*.yaml"
---

Pin every third-party `uses:` to a 40-character commit SHA, gate first-party tag exemptions on a documented inline comment plus a `.github/dependabot.yml` covering the `github-actions` ecosystem, and pin every Docker image reference to a non-`latest` tag or `@sha256:` digest.

**Why:** The 2025 tj-actions (CVE-2025-30066) and reviewdog supply-chain compromises demonstrated that tag-pinning is not sufficient — tags are mutable, and a pushed tag silently changes what runs in your workflow. SHA-pinning makes the contents reproducible and auditable. Dependabot for the `github-actions` ecosystem is the second half of the contract: without it, SHAs rot into known-vulnerable versions. Docker image references with `:latest` or no tag share the same mutable-ref failure mode as `@main` on an action — the next run pulls a different image. First-party (`actions/*`, `github/*`) tag-pinning is the pragmatic exemption given Dependabot noise on patch bumps, but it requires explicit documentation so the auditor can distinguish a deliberate exemption from a missed pinning.

**How to apply:** Walk every `uses:` reference in the workflow. For third-party actions, confirm the ref is a 40-character SHA (typically with a trailing `# vN.N.N` comment for readability). For first-party (`actions/*`, `github/*`) actions, confirm either SHA-pinning or a major-tag pin paired with an inline `# dependabot-managed` (or equivalent) comment. Walk every Docker image reference (`uses: docker://...`, `jobs.*.container.image`, `services.*.image`) and confirm a non-`latest` tag or `@sha256:` digest. Check whether `.github/dependabot.yml` exists and includes `package-ecosystem: github-actions` — if absent, flag that the SHA-pinning strategy will rot. Note the absent Dependabot config as a separate guidance item; do not scaffold it inline (out of scope for this skill).

```yaml
jobs:
  build:
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2
      - uses: tj-actions/changed-files@2f7c5bfce28377bc069a65ba478de0a74aa0ca32  # v44
    container:
      image: node:20.11.1
```

**Common fail signals (audit guidance):** Non-SHA third-party `uses:`, first-party tag-pinning without Dependabot coverage, unpinned Docker images, missing `.github/dependabot.yml` for `github-actions`.
