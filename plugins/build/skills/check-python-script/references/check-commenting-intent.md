---
name: Commenting Intent
description: Use comments to explain *why* — constraints, trade-offs, workarounds — not to restate what the code already says, and tag every TODO with an owner or ticket.
paths:
  - "**/*.py"
---

**Why:** Comments that restate code rot alongside it: the code changes, the comment doesn't, and now the comment lies. Comments that explain *why* stay useful as the code evolves because the constraint they name outlives the implementation. Untagged TODOs become orphans — no one knows who owns them or why they're there. Source principle: *Document intent at the top* (inline-comment subset; Clean Code ch. 4).

**How to apply:** before writing a comment, ask "is this naming a constraint, trade-off, or workaround the code can't show?" If yes, write it. If it restates the next line, delete it (or refactor the code so it doesn't need the comment). Tag every TODO: `TODO(bbeidel)` or `TODO(WIKI-123)`. If a paragraph-long comment is needed to explain logic, the logic wants a named helper function instead.

```python
# Normalize Unicode before comparison — combining-character variants
# would otherwise miscount as distinct entries.
text = unicodedata.normalize("NFC", text)
```

**Common fail signals (audit guidance):** `# increment counter` above `counter += 1`; bare `# TODO: fix this` with no owner; a paragraph comment explaining logic that a helper function would name.
