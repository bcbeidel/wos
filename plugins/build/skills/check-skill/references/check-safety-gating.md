---
name: Safety Gating
description: When the skill contains destructive operations, an explicit approval gate must precede them — vague "confirm" language and ungated dry-run options do not count.
paths:
  - "**/SKILL.md"
---

Gate destructive operations on explicit confirmation — every `rm -rf`, `DROP TABLE`, force-push, production deploy, or secret rotation is preceded by an approval step the agent must pause on, with dry-run as the default and `disable-model-invocation: true` set when auto-invocation would be dangerous.

**Why:** Agents execute what they read. A destructive step with no preceding gate runs unconditionally on the next invocation — and skills are auto-routed, so "the user wouldn't ask for this" is not a defense. Vague approval language ("confirm with the user") collapses under model variation: some readings inject a prompt, some don't. An explicit gate (require an exact confirmation string, show the dry-run plan first, set `disable-model-invocation: true` for skills whose auto-invocation would be dangerous) leaves no room for that variation. Dry-run mentioned but not defaulted is failure-prone — the destructive variant runs whenever the agent skips the dry-run option.

**How to apply:** Add an explicit approval step before every destructive operation. Show a dry-run of what will change and require an exact confirmation string ("Require the exact string `drop staging`"). Make dry-run the default; require explicit opt-in for the destructive variant. Set `disable-model-invocation: true` on skills whose auto-invocation would be dangerous.

```markdown
---
disable-model-invocation: true
---

## Steps
1. Show a dry-run of the drop plan (tables, row counts, dependent views).
2. Ask the user to confirm. Require the exact string `drop staging`.
3. On confirmation, drop the staging schema and recreate it.
```

**Common fail signals (audit guidance):**
- Destructive step (`rm -rf`, `DROP TABLE`, force-push, production deploy, secret rotation) with no preceding approval step, dry-run, or confirmation prompt
- Approval language is vague ("confirm with the user") rather than an explicit gate
- Dry-run option mentioned but not made the default, or the destructive variant runs unconditionally
- `disable-model-invocation: true` missing on a skill whose Workflow is destructive by design

**Exception:** When the skill contains no destructive operations, this dimension returns N/A silently — Tier-1 feeds the destructive-command hit list to this dimension, and an empty list means there is nothing to gate.
