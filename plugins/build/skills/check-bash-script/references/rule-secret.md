---
name: Secret Embedding
description: Read API keys, tokens, private URLs, and other credentials from environment variables — never embed them in script source.
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Read API keys, tokens, private URLs, and other credentials from environment variables (or a secret manager) — never embed them as literals in script source.

**Why:** secrets in committed source leak through git history, build logs, error messages, backups, and shoulder-surfed terminal sessions. Once a secret is in `git log`, it's effectively public; rotation across every dependent system is the only remediation. Externalizing to the environment is the minimum bar — the script declares what it needs at the top, the secret value lives in the operator's secret store, and the script fails fast when the variable is unset rather than running with a missing credential.

**How to apply:** at the top of the script, declare each required secret with `${VAR:?MESSAGE}` so the script fails immediately if the variable is unset. Reference the variable everywhere downstream — never inline the literal. When a secret manager is available (`vault`, `aws secretsmanager`, `pass`), prefer fetching from there over plain env vars.

```bash
#!/usr/bin/env bash
set -euo pipefail

readonly API_KEY="${OPENAI_API_KEY:?OPENAI_API_KEY env var required}"
readonly DB_URL="${DATABASE_URL:?DATABASE_URL env var required}"

main() {
  curl -H "Authorization: Bearer $API_KEY" "$DB_URL/health"
}
```

**Exception:** none. Secrets in source are always wrong, regardless of intent. Test fixtures with placeholder values (`API_KEY="test-key-not-real"`) are not secrets and not flagged. The detector distinguishes by pattern, not by intent — if the audit fires, rotate the credential and externalize.
