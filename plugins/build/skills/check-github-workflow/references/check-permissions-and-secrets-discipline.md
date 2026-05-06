---
name: Permissions & Secrets Discipline
description: Declare top-level `permissions:` at least privilege, scope `env:` (and especially secrets) to the narrowest useful step, and prefer OIDC federation over long-lived static cloud credentials.
paths:
  - "**/.github/workflows/*.yml"
  - "**/.github/workflows/*.yaml"
---

Set top-level `permissions:` at the smallest scope the workflow needs (`contents: read` is the floor), elevate per-job only where a specific job justifies it, scope every secret reference to the step that uses it, and prefer OIDC federation over static cloud credentials wherever the cloud provider supports it.

**Why:** The default `GITHUB_TOKEN` scope is too broad — a compromised action inherits whatever the workflow grants. Least privilege at workflow level plus per-job elevation is OpenSSF's 2025 recommendation and the largest single defense against supply-chain compromise. Secrets exposed via workflow- or job-level `env:` reach every step, every action, and every transitive call — including third-party actions that don't need them. Static cloud credentials (long-lived AWS access keys, GCP service account keys) are the largest-blast-radius credentials most teams hold; OIDC short-lived tokens replace them with per-run federated identity that cannot be exfiltrated for later use.

**How to apply:** Verify the top-level `permissions:` block is at the narrowest useful scope. Confirm per-job `permissions:` elevations are justified by the work that job actually does (a release job needs `contents: write`; a lint job does not). Walk every `${{ secrets.* }}` reference and confirm it lives on the specific step that uses it, not on a job- or workflow-level `env:`. If the workflow authenticates to a cloud provider, check whether OIDC is in use (`id-token: write` + federated credentials); if static keys are used instead, flag the missing migration unless an inline comment justifies the choice. Verify `id-token: write` appears if and only if the workflow actually performs OIDC exchange.

```yaml
permissions:
  contents: read

jobs:
  release:
    permissions:
      contents: write
      id-token: write   # OIDC for cloud auth
    steps:
      - name: Publish
        env:
          GH_TOKEN: ${{ secrets.GH_TOKEN }}
        run: gh release create ...
```

**Common fail signals (audit guidance):** Permissions broader than needed, secrets referenced from job- or workflow-level `env:`, static cloud credentials used when OIDC is available.
