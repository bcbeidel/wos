---
name: Latency
description: Synchronous hooks do not create session sluggishness that pressures bypass, and never recurse into `claude` itself.
paths:
  - "**/.claude/hooks/**/*.sh"
  - "**/.claude/hooks/**/*.bash"
  - "**/.claude/hooks/**/*.py"
---

Keep synchronous hooks under ~1 second in the hot path; move LLM calls, network requests, and slow subprocesses to `async: true`; never shell out to `claude` or `claude-code` from a hook.

**Why:** Synchronous hooks block Claude while running. A slow gate (LLM call, `curl` to a remote service, large Python import) creates session sluggishness, and the user response is to disable the hook — the gate that was supposed to protect the team becomes a bypass culture instead. Recursive invocation of `claude` / `claude-code` from inside a hook spawns compound exponentially: each Claude invocation runs the hook, which spawns Claude, which runs the hook. The spec warns explicitly against this. Severity: `fail` for recursive `claude` invocation; `warn` for suggested network/LLM in the hot path.

**How to apply:** move non-critical slow work to `"async": true` (accepts it cannot block — see async/blocking-coherence rule). For LLM-mediated decisions inside the hook path, use `"type": "prompt"` or `"type": "agent"` — not a shell-out to `claude`. Raise `timeout` only to accommodate realistic execution; a slow synchronous gate generates bypass pressure faster than it generates protection.

```json
// Non-critical observability — async, no blocking paths
{
  "type": "command",
  "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/observe.sh",
  "async": true
}
```

**Common fail signals (audit guidance):**
- Hook script invokes `claude` or `claude-code` (any subcommand) — recursive loop.
- Synchronous hook calls `curl` / `wget` / network tools without an explicit short timeout.
- Synchronous hook imports heavyweight Python libraries (e.g., `pandas`, `torch`) on every invocation.
- Synchronous hook shells out to a long-running subprocess (`docker build`, `pytest`, full `terraform plan`).
- Hook `timeout` raised above ~5s to "make it work" — bypass pressure incoming.
