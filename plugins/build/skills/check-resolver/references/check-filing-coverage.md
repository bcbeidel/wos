---
name: Filing Coverage
description: Every depth-1 directory on disk must be classified — filing row, context row, out-of-scope entry, ambient default, or delegated to a nested RESOLVER.md.
paths:
  - "**/RESOLVER.md"
---

Classify every depth-1 directory on disk explicitly: as a filing row, a context-row entry, an out-of-scope entry, an ambient default (`.git/`, `node_modules/`, `dist/`, `build/`, `.cache/`, `.venv/`, `target/`, `__pycache__/`, `.resolver/`), or a directory containing its own nested `RESOLVER.md` (delegated).

**Why:** Unclassified directories are "dark capabilities" — reachable on disk but invisible to Claude's filing decisions. The failure mode is the surgeon the hospital can't find: the right destination exists, but the routing layer never points at it, so new content drifts into wrong locations and accumulates silently. Silence in the resolver is ambiguous; explicit classification is load-bearing.

**How to apply:** Walk every depth-1 directory and verify each appears in exactly one bucket. A filing row that names "research" but only points at `.research/public/` when `.research/private/` also holds research is incomplete — widen with a glob-style location or add the sibling row. Out-of-scope must be non-empty when ambient directories like `.git/` or `node_modules/` are present. Filing rows must match the directory's frontmatter `type:` or naming-pattern purpose (don't route hooks at a research directory). Subdirectories of a filing dir are not auto-classified — the filing rule names files directly inside, so a depth-2 directory still needs explicit classification or delegation.

```markdown
<!-- resolver:begin -->
## Filing
| content-type | location | naming pattern |
|---|---|---|
| research | .research/ (including subdirectories) | <slug>.md |
| inbox note | .inbox/ | <slug>.md |

## Out of scope
- .git/ — ambient
- node_modules/ — ambient
<!-- resolver:end -->
```

**Common fail signals (audit guidance):**
- A tracked directory (one with frontmatter-tagged contents or a consistent naming pattern) exists but no filing row names it.
- A filing row points at a directory type (e.g., "research") but multiple such directories exist and the row names only one.
- Out-of-scope list is empty despite `.git/`, `node_modules/`, or similar ambient directories present.

**Exception:** Directories matching the baked-in ambient set (`.git/`, `node_modules/`, `dist/`, `build/`, `.cache/`, `.venv/`, `target/`, `__pycache__/`, `.resolver/`) are auto-classified and need no explicit out-of-scope entry. Directories containing a nested `RESOLVER.md` are classified as delegated and need no row in the parent.
