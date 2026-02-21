---
name: preferences
description: >
  This skill should be used when the user asks to "set communication style",
  "configure how you talk to me", "set preferences", "be more direct",
  "be more concise", "adjust your tone", "change communication style",
  or "update my preferences".
disable-model-invocation: true
argument-hint: "[style description]"
---

# Preferences Skill

Capture user communication preferences and write them as structured LLM
instructions in CLAUDE.md.

## Workflow

Follow the capture workflow in `references/capture-workflow.md`.

## Quick Reference

Five dimensions, each with three levels:

| Dimension | Levels |
|-----------|--------|
| Directness | blunt, balanced, diplomatic |
| Verbosity | terse, moderate, thorough |
| Depth | just-answers, context-when-useful, teach-me |
| Expertise | beginner, intermediate, expert |
| Tone | casual, neutral, formal |

## Implementation

Preferences are stored in CLAUDE.md between communication markers:

```
<!-- wos:communication:begin -->
## Communication
- **Directness:** ...
- **Verbosity:** ...
<!-- wos:communication:end -->
```

The writer function handles create, replace, and partial updates.
