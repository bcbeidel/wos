---
name: create
description: Create project context, areas, or documents
user-invocable: true
---

# Create

Create and initialize structured project context.

## Routing

Determine user intent from their message:

1. **Initialize project** -- "set up context", "initialize", "create context"
2. **Add area** -- "add area for X", "new area", "create area"
3. **Create document** -- "create a doc about X", "write about X", "new document"

**Prerequisite:** Before running any `uv run` command below, follow the preflight check in the [preflight reference](../_shared/references/preflight.md).

## 1. Initialize Project

Create directory structure and AGENTS.md:

```
docs/
  context/
    _index.md
  research/
    _index.md
  plans/
    _index.md
AGENTS.md (with WOS section)
```

Run: `uv run <plugin-scripts-dir>/reindex.py --root .`

Update AGENTS.md with the WOS section wrapped in `<!-- wos:begin -->` /
`<!-- wos:end -->` markers. These markers are required — they enable
automated navigation updates via `agents_md.py`. Never place WOS-managed
content outside these markers.

## 2. Add Area

1. Ask for area name (lowercase-hyphenated)
2. Create `docs/context/{area}/`
3. Ask the user for a 1-2 sentence area description. Write it as the preamble in `_index.md` above the file table.
4. Run `uv run <plugin-scripts-dir>/reindex.py --root .` (also auto-updates AGENTS.md areas table)

## 3. Create Document

1. Ask the user what the document should cover
2. Determine appropriate location (`docs/context/{area}/` or `docs/research/` or `docs/plans/`)
3. Generate YAML frontmatter:
   - `name` and `description` (required)
   - `type` if appropriate (research, plan, reference, etc.)
   - `sources` if type is research (verify URLs with `uv run <plugin-scripts-dir>/check_url.py URL`)
   - `related` if sourced from other project documents
4. Write document content following the lost-in-the-middle convention:
   - Top: summary with key insights and actionable guidance
   - Middle: detailed explanation, examples, context for human readers
   - Bottom: key takeaways or quick-reference summary
5. **Word count check** — Count words in the generated content. If the context file exceeds 800 words, note the count and suggest splitting into multiple focused files. This is advisory, not blocking.
6. **Related fields** — Scan existing files in the target area for potential `related:` candidates. Present suggestions to the user. If they confirm, add `related:` entries to the frontmatter. Ask whether referenced files should also link back (bidirectional linking).
7. Run `uv run <plugin-scripts-dir>/reindex.py --root .`

## Document Structure Convention

**LLMs lose attention in the middle of long documents.** Structure files so that:
- The top contains a summary with key insights and actionable guidance
- The middle contains detailed explanation, examples, and context for human readers
- The bottom restates key takeaways or provides a quick-reference summary

The first and last sections are what an agent is most likely to retain. Write for that.
