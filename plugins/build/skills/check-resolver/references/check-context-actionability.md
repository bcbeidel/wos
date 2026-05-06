---
name: Context Actionability
description: Each context-table row must list 1–4 concrete entries (files or directories) that resolve, not vague prose like "the style guide".
paths:
  - "**/RESOLVER.md"
---

Each context-table row must name 1–4 concrete entries — files or directories — that resolve to real paths. No prose pointers; no empty bundles; no "look everywhere" lists.

**Why:** Prose pointers fail silently. A row that says "read the style guide" produces zero deterministic loads — the agent guesses, sometimes correctly, sometimes not, and no audit can tell. Empty bundles defeat the resolver's purpose: the row promises context and delivers none. Bundles approaching ">6 entries" degrade into "just look everywhere", which wastes context budget and trains Claude to skip the resolver entirely. The 1–4 range compresses the routing decision into something agents will actually use.

**How to apply:** For each context row, verify the right-hand column lists 1–4 entries, each a real file path or a directory. Directory entries are valid — the agent uses Glob on the directory's naming pattern and reads frontmatter to locate the right file (`.research/` counts as one entry). Bundle scope must match the named task: "authoring a hook" should point at hook + routing references, not the entire style guide. If a row currently reads as prose, replace with concrete paths. If a row exceeds 6 entries, narrow to the load-bearing subset. If a row is empty, either remove the row or fill with the actual references the task needs.

```markdown
| task | references |
|---|---|
| authoring a hook | [_shared/references/primitive-routing.md, _shared/references/hook-best-practices.md] |
| planning research | [.research/] |
```

**Common fail signals (audit guidance):**
- A context row's column contains prose ("the style guide") without a resolvable path.
- A bundle lists zero entries (empty right-hand column).
- A bundle lists >6 entries (approaching a "just look everywhere" pattern).

**Exception:** None. Every context row must list concrete paths; if no concrete paths apply, the row should not exist.
