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

## 1. Initialize Project

Create directory structure and AGENTS.md:

```
context/
  _index.md
artifacts/
  _index.md
  research/
    _index.md
  plans/
    _index.md
AGENTS.md (with WOS section)
```

Run: `python3 scripts/reindex.py --root .`

Update AGENTS.md with the WOS section using markers.

## 2. Add Area

1. Ask for area name (lowercase-hyphenated)
2. Create `context/{area}/`
3. Run `python3 scripts/reindex.py --root .`
4. Update AGENTS.md areas table

## 3. Create Document

1. Ask the user what the document should cover
2. Determine appropriate location (`context/{area}/` or `artifacts/research/` or `artifacts/plans/`)
3. Generate YAML frontmatter:
   - `name` and `description` (required)
   - `type` if appropriate (research, plan, reference, etc.)
   - `sources` if type is research (verify URLs with `python3 -c "from wos.url_checker import check_url; print(check_url('URL'))"`)
   - `related` if sourced from other project documents
4. Write document content following the lost-in-the-middle convention:
   - Top: summary with key insights and actionable guidance
   - Middle: detailed explanation, examples, context for human readers
   - Bottom: key takeaways or quick-reference summary
5. Run `python3 scripts/reindex.py --root .`

## Document Structure Convention

**LLMs lose attention in the middle of long documents.** Structure files so that:
- The top contains a summary with key insights and actionable guidance
- The middle contains detailed explanation, examples, and context for human readers
- The bottom restates key takeaways or provides a quick-reference summary

The first and last sections are what an agent is most likely to retain. Write for that.
