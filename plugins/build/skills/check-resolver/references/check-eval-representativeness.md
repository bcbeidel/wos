---
name: Eval Representativeness
description: Trigger evals must exercise both filing and context routing — at least 1 case per filing row and at least 15% negative cases.
paths:
  - "**/.resolver/evals.yml"
---

The eval set in `.resolver/evals.yml` must include at least one positive case per filing row, at least 15% negative cases, and a mix of filing and context cases proportional to the respective table sizes.

**Why:** Untested routing is unproven routing. Pure positive-case evals can't detect overlap drift — when two filing rows accept similar content, the resolver silently routes the wrong way, and a positive-only eval suite passes regardless. Negative cases ("X does NOT route to Z") are the only mechanism that catches the false-positive failure mode. Coverage gaps hide routing defects in the uncovered table: filing-only evals leave context rows unproven, and vice versa. The 15% negative threshold and per-row coverage are baseline; the resolver only earns trust by surviving them.

**How to apply:** Count filing rows and context rows in `RESOLVER.md`. For each filing row, verify ≥1 positive eval case names that row's location in `expected_filing`. Add 1–2 negative cases per overlap-prone filing row (e.g., "save this stripe config" → NOT `.research/`). Compute the negative-case ratio across the full eval set; if below 15%, add negative cases proportional to the overlap risk. Verify context cases exist for each context row, sized roughly proportional to the table. Detect duplicates — same prompt with same expected outcome — and remove them.

```yaml
cases:
  - prompt: save this research investigation
    expected_filing: .research/
  - prompt: save this raw webhook payload
    expected_filing: .raw/
  - prompt: save this stripe config
    expected_filing_not: .research/   # negative case
  - prompt: authoring a hook
    expected_context: [_shared/references/hook-best-practices.md]
```

**Common fail signals (audit guidance):**
- Fewer than 1 eval case per filing row.
- Zero negative cases (every case is "X routes to Y"; none are "X does NOT route to Z").
- All cases are filing; none are context (or vice versa).
- Cases duplicate (same prompt tested twice with the same expected outcome).

**Exception:** None. Every filing row needs at least one positive case; the 15% negative-case floor applies to any non-trivial eval set.
