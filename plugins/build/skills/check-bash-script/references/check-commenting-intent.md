---
name: Commenting Intent
description: Write a header comment naming purpose, usage, and dependencies. Inline comments explain *why*, not *what* — and TODOs carry an owner or ticket.
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Write a header comment in the first 10 lines naming purpose, usage signature, and external dependencies. Use inline comments to explain *why* a non-obvious choice was made — not to restate what the code already says. Tag TODOs with an owner or ticket number.

**Why:** comments that restate code rot alongside it — `# increment counter` above `((counter++))` adds nothing in the present and lies after the next refactor. Comments that explain *why* (constraints, workarounds, hidden invariants, performance reasons, security considerations) stay useful because they answer questions the code itself can't. The header serves a different role — it orients a reader who has never seen the file before, telling them what to expect in 10 seconds. TODOs without an owner accumulate as orphan maintenance debt; a tagged TODO has someone responsible for it (or a ticket where the work is tracked), making the backlog auditable.

**How to apply:** the header (in the first 10 lines, after the shebang) covers purpose, usage signature, and external dependencies — see `rule-header-comment.md` for the deterministic check. Inline comments answer questions the code can't: *why* this approach, *why* this workaround, *why* this seemingly-redundant check. Reserve comments for the non-obvious; obvious code doesn't need explanation. Tag every TODO with `TODO(<owner>):` or `TODO(<ticket>):` so it can be tracked or assigned.

```bash
# Header (first 10 lines)
#!/usr/bin/env bash
#
# rotate-logs — Compress logs older than 30 days.
#
# Usage: rotate-logs.sh [--dry-run] <log-dir>
# Dependencies: gzip, find
# Exit codes: 0 success, 1 failure, 64 usage error

# Inline why-comment
# We use --backup=none here because GNU and BSD sed disagree on how
# to handle backup suffixes; backups are managed by the caller's git.
sed -i 's/old/new/' "$file"

# Tagged TODO
# TODO(bbeidel): handle Unicode normalization before count
((counter++))
```

**Common fail signals (audit guidance):**
- No header comment in the first 10 lines — script's purpose is opaque to readers.
- `# increment counter` above `((counter++))` — restates code; rot risk; no value.
- `# this is a hack` with no explanation — what's the hack? what's it working around?
- `# TODO: fix this` with no owner or ticket — orphaned debt.
- Block comments that paraphrase the function below — the function name should already convey this; if it doesn't, fix the name.

**Exception:** trivial scripts (under ~20 lines, single self-evident purpose) may omit the header. The audit emits WARN at the dimension level; judgment-level coaching, not blocking. When in doubt, write the header.
