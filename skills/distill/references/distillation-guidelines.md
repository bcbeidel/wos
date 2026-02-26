# Distillation Guidelines

## What Makes a Good Context File

A context file distilled from research should be:

1. **Atomic** — one concept per file (Zettelkasten principle)
2. **Actionable** — reader knows what to do after reading
3. **Traceable** — sources link back to evidence
4. **Concise** — 200-800 words targets optimal RAG retrieval
5. **Structured** — key insight top, detail middle, takeaway bottom

## Splitting Heuristics

Split a finding into multiple files when:
- It covers more than one distinct concept
- Different aspects serve different audiences
- The finding has both a "what" and a "how" that are independently useful

Merge findings into a single file when:
- They're tightly coupled and don't make sense independently
- Combined they still fit under 800 words
- They serve the same audience with the same purpose

## Word Count Rationale

| Range | Use Case |
|-------|----------|
| <200 words | Too thin — probably needs more context or should be merged |
| 200-500 words | Ideal for focused reference files |
| 500-800 words | Good for explanatory context with examples |
| >800 words | Consider splitting — RAG retrieval degrades, attention loss risk |

## Confidence Mapping

When distilling, map research confidence levels to context file framing:

- **HIGH confidence** — state directly: "X works because Y"
- **MODERATE confidence** — qualify: "Evidence suggests X, based on Y"
- **LOW confidence** — flag: "Early evidence indicates X, but Z remains uncertain"
