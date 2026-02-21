---
name: discover
description: >
  This skill should be used when the user asks to "find context",
  "what context do we have", "look up guidance on", "show me the pitfalls of",
  "what topics cover", "explore context", or "discover what we know about".
  Also use when an agent needs to find relevant context before starting work.
argument-hint: "[topic or question]"
---

# Discover Skill

Find and access project context efficiently using progressive drill-down.

## Routing

Use the progressive scanner to find context with minimal token cost.
Always start broad and narrow down — never read full files unless necessary.

| Agent intent | Action |
|---|---|
| "What context do we have?" | `index` (full listing) |
| "What do we have on X?" | `index --area X` or `index --type topic` |
| "What's in this file?" | `outline <file>` |
| "Show me the guidance on X" | `extract <file> "Guidance"` |
| "What are the pitfalls of X?" | `extract <file> "Pitfalls"` |

## Implementation

All discovery uses `scripts/scan_context.py` via Bash:

```bash
# Level 1: Index — list all documents (~1 line per file)
python3 scripts/scan_context.py index
python3 scripts/scan_context.py index --area python-basics
python3 scripts/scan_context.py index --type topic

# Level 2: Outline — section headings with word counts
python3 scripts/scan_context.py outline context/python-basics/error-handling.md

# Level 3: Extract — raw section content
python3 scripts/scan_context.py extract context/python-basics/error-handling.md "Guidance"
python3 scripts/scan_context.py extract context/python-basics/error-handling.md "Guidance" "Pitfalls"
```

## Canonical Sections

| Document type | Sections |
|---|---|
| topic | Guidance, Context, In Practice, Pitfalls, Go Deeper |
| overview | What This Covers, Topics, Key Sources |
| research | (numbered findings), Implications, Sources |
| plan | Objective, Context, Steps, Verification |

## Guidelines

- **Start with `index`** to find relevant files before reading anything
- **Use `outline`** to see what sections exist before extracting
- **Use `extract`** to get specific sections — cheaper than reading the full file
- **Never read full files** unless you need the complete content
- If no context exists on a topic, say so — don't fabricate guidance
