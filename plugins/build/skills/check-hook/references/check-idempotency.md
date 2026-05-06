---
name: Idempotency
description: Running the hook twice produces the same outcome — no unbounded state accumulation.
paths:
  - "**/.claude/hooks/**/*.sh"
  - "**/.claude/hooks/**/*.bash"
  - "**/.claude/hooks/**/*.py"
---

Hook bodies must not accumulate state — no unbounded log appending, no unreset counters, no orphan temp files.

**Why:** Hooks fire repeatedly across a session — every matched tool call, every retry, every Stop loop iteration. A pattern that appends to a log without rotation grows until disk fills. A counter that increments without a reset path skews behavior asymptotically. A temp file written without an `EXIT` trap leaves orphans that the next invocation has to disambiguate. Each individual run looks fine; the hook degrades over weeks until it silently breaks. Severity: `warn`.

**How to apply:** log to `>>` only when external rotation (`logrotate`, log shipper) is in place; otherwise prefer event-sourced logs you derive at read time. Replace counters with append-only event records and compute the count when consumed. Clean up temp files via an EXIT trap so partial runs don't leak.

```bash
trap 'rm -f "${TMPFILE:-}"' EXIT
TMPFILE=$(mktemp)
# ... use TMPFILE; trap removes it on any exit path
```

**Common fail signals (audit guidance):**
- `echo ... >> /some/path/log.txt` with no rotation policy nearby (cron, logrotate, log shipper).
- Persistent counter file incremented but never reset (`echo $((COUNT+1)) > /tmp/count`).
- `mktemp` / `> /tmp/...` write without an `EXIT` trap removing it.
- Database `INSERT` from a hook with no de-duplication key — repeated runs duplicate records.
- Hook that "remembers" state in a file under `.claude/` without a session-scoped key (`session_id`).
