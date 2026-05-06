---
name: CLAUDE.md Overlap
description: Hooks that duplicate CLAUDE.md instructions are surfaced for user judgment, not auto-removed.
paths:
  - "**/.claude/settings.json"
  - "**/.claude/settings.local.json"
  - "**/CLAUDE.md"
---

When a hook enforces something CLAUDE.md already advises, surface the overlap with both citations and let the user choose — never auto-resolve.

**Why:** Overlap between a hook and a CLAUDE.md instruction is not always wrong: belt-and-suspenders is a deliberate pattern when the cost of failure is high (the hook enforces deterministically; the advisory keeps the agent's reasoning aligned). But sometimes one of the two is stale — a CLAUDE.md line that predates the hook's introduction, or a hook that survived after the advisory was generalized. The audit cannot tell which without the user's intent. Severity: `warn` (always advisory).

**How to apply:** when a hook's enforcement maps to a CLAUDE.md line, surface both verbatim in the finding and present three options to the user: (1) keep both — document the intent in a comment or CONTRIBUTING; (2) drop the CLAUDE.md entry — the hook enforces deterministically; (3) drop the hook — if the advisory is sufficient and the hook generates false positives. Never apply automatically.

```markdown
Finding example (auditor output, not the hook itself):

Hook `block-direct-main-push.sh` (PreToolUse Bash) enforces:
  > Reject `git push origin main` from any non-CI invocation.

CLAUDE.md line 47:
  > Never push directly to main; use a PR.

Options:
  1. Keep both (belt-and-suspenders; document why).
  2. Drop CLAUDE.md line — hook enforces deterministically.
  3. Drop hook — advisory is sufficient.
```

**Common fail signals (audit guidance):**
- Hook matcher and CLAUDE.md instruction both name the same forbidden pattern (e.g., `git push --force` blocked in both).
- Hook scope and CLAUDE.md scope diverge subtly (hook checks file extension; CLAUDE.md checks directory) — likely one drifted.
- CLAUDE.md instruction phrased as "Claude should..." that a hook now enforces deterministically — advisory may be redundant.
- Hook that exists with no matching guidance in CLAUDE.md or CONTRIBUTING — opposite gap; intent not documented.
