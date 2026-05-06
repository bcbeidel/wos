---
name: Safety Posture
description: Catch indirect safety issues Tier-1 regex missed — HTTP libraries in scripts, `exec` of downloaded content, sourcing non-version-controlled config, `--no-verify`-defeating workarounds.
paths:
  - "**/.pre-commit-config.yaml"
  - "**/.pre-commit-config.yml"
---

Catch indirect safety issues Tier-1 regex missed — HTTP libraries in scripts, `exec` of downloaded content, sourcing non-version-controlled config, `--no-verify`-defeating workarounds.

**Why:** Commit-time is a sensitive moment — *No network I/O*, *No elevated privileges*, *Do not mutate files outside the staged set / auto-`git add` / rewrite history*, *No destructive shell commands*, *Leave `--no-verify` working*. Tier-1's regex catches surface patterns (`curl`, `pip install`, `git push`, `sudo`); judgment catches the indirect equivalents (a Python hook that imports `requests`, a shell hook that `source`s a file from `~/.config`). Quiet safety exceptions accumulate into real incidents.

**How to apply:** Inspect every local hook script for: HTTP-capable imports (`requests`, `urllib`, `httpx`, `fetch`); `exec`/`eval` of downloaded or untrusted content; sourcing files outside the repo (`~/.config`, `/etc`, `$HOME/...`); workarounds that re-trigger pre-commit when `--no-verify` was used. Escalate to FAIL when a clear safety bypass is found; otherwise WARN.

```yaml
      - id: custom-check
        name: validate config schema
        entry: scripts/hooks/check.py
        language: python
        language_version: python3.11
        additional_dependencies: [jsonschema==4.23.0]
        files: ^config/.*\.yaml$
```

**Common fail signals (audit guidance):** A Python hook script that imports `requests` and posts to a URL ("telemetry"); a shell script that sources a file from `~/.config` (which isn't under version control).
