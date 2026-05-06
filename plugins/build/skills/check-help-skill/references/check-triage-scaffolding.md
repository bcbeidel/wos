---
name: Triage Scaffolding
description: Task-to-skill mapping is actionable so a caller with a specific task can pick a sibling unambiguously, instead of being left to read every description.
paths:
  - "**/skills/help/SKILL.md"
---

Scaffold the choice between siblings — name the user task and point to the skill, not the reverse.

**Why:** A help-skill that lists skills without scaffolding the choice between them throws the disambiguation work back at the caller. The caller (human or agent) must read every sibling's description and infer which fits — at which point the help-skill added no value over a `ls skills/`. The point of triage is to convert a fuzzy intent ("I have requirements but don't know how to break them down") into a concrete next step ("start with `scope-work`"). Without that scaffolding, callers either pick wrong or load every sibling's full SKILL.md to decide, both of which the help-skill exists to prevent.

**How to apply:** Frame entries by user situation, not by skill function. The pattern is "When you have X — start with `<skill>`, then `<skill>`" rather than "<skill> — does X". A description-echo bullet (`- scope-work — explores requirements`) duplicates the table and adds no routing value; a task-keyed bullet (`- When you have requirements but don't know how to break them down — start with scope-work, then plan-work`) scaffolds the choice. Apply per workflow chain and per "where do I start" cue. Severity: `warn`.

```markdown
- **When you have requirements but don't know how to break them down** —
  start with `scope-work`, then `plan-work`.
- **When the spec is already approved and you need to execute** —
  jump straight to `start-work`.
```

**Common fail signals (audit guidance):**
- Bullets shaped `<skill> — <description>` (echoes the index table; no triage).
- No surface that distinguishes "I have requirements" from "I have a plan" from "I have a bug".
- Choice between two similar siblings is not named anywhere — caller must compare descriptions themselves.
- Workflow chains exist but the "when to enter" question routes to none of them.
