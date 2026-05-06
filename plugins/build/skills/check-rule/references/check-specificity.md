---
name: Specificity
description: Write directives a reviewer can verify unambiguously — numeric thresholds, named tools, quoted patterns; no anchor-free terms.
paths:
  - "**/.claude/rules/*.md"
  - "**/.claude/rules/**/*.md"
---

Write each directive so a reviewer (or Claude) can verify compliance without subjective judgment — a numeric threshold, a named tool, a specific file path, or a quoted code pattern.

**Why:** Anchor-free directives ("good", "clean", "appropriate", "properly", "consistent") produce uneven adherence — two readers (or two Claude sessions) interpret them differently, so the rule fails to constrain behavior. Hedged phrasing ("prefer", "generally", "usually", "consider") pushes judgment back onto Claude at every invocation, defeating the point of writing the rule down. Reader-defers directives ("use your judgment", "as appropriate") with no fallback rule carry no information; they aren't rules at all.

**How to apply:** Replace anchor-free terms with verifiable directives — "Format code properly" becomes "Use 2-space indentation; run `prettier --check` before committing." If you keep the term, pair it with a behavioral definition ("clean code: no functions over 50 lines, no nested ternaries"). Commit hedged rules to a directive and move the hedge into a named exception. Either remove a reader-defers directive (it carries no information) or add the fallback rule.

```markdown
Use TypeScript strict mode in all files under `src/`. Exception: generated code in `src/codegen/`.
```

**Common fail signals (audit guidance):**
- Anchor-free terms as the directive: "good", "clean", "clear", "appropriate", "well-structured", "properly", "nice", "consistent" without a behavioral definition
- Directives that defer the decision back to the reader ("use your judgment", "as appropriate") without a fallback rule
- Hedged phrasing: "prefer", "generally", "usually", "consider"
