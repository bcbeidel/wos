# Claim Verification Reference

Lookup reference for claim types, table format, resolution statuses, and edge
cases. The step-by-step verification procedure lives in `research-workflow.md`
Phases 5.5a and 5.5b.

## Claim Types (4)

Register these claim types — they map to observed fabrication failure modes.

| Type | Definition | Example |
|------|-----------|---------|
| quote | Verbatim text attributed to a person/source | "Software is eating the world" — Andreessen |
| statistic | Specific number, percentage, or quantity | "30+ integrations available" |
| attribution | Action or role attributed to a person/org | "Chesky founded Airbnb" |
| superlative | Claim of primacy, extremity, or uniqueness | "the first company to achieve..." |

General observations, trend descriptions, and methodology notes do NOT need
registration. Only register claims that assert a specific, verifiable fact.

## Claims Table Format

| # | Claim | Type | Source | Status |
|---|-------|------|--------|--------|
| 1 | "Software is eating the world" | quote | [1] | unverified |
| 2 | 30+ integrations | statistic | [3] | unverified |

- `Source` references map to the numbered Sources table (e.g., `[1]` = first source)
- All claims start as `unverified`
- Claims without a citeable source should still be registered with source marked `—`

## Resolution Statuses (5)

| Status | Meaning |
|--------|---------|
| verified | Passed CoVe self-check AND citation re-verification confirmed source support |
| corrected | Didn't match source; updated to match (note original claim in parentheses) |
| removed | Not found in source; claim removed from document body |
| unverifiable | Source couldn't be fetched (403/timeout); claim kept but flagged in document |
| human-review | Ambiguous automated result, or uncited claim that CoVe couldn't confirm |

## Verification Questions by Type

When generating CoVe verification questions, use these type-specific patterns:
- quote: "What exact words did [person] say about [topic]?"
- statistic: "What is the actual number for [metric]?"
- attribution: "What role did [person] play in [event]?"
- superlative: "Which [entity] was actually the first/largest/most [claim]?"

## Contradiction Resolution

When CoVe contradicts a claim:

```
CoVe contradicts claim
  → Does the claim have a cited source?
    → YES: Escalate to Phase 5.5b (citation re-verification)
           Source confirms CoVe answer → corrected, update claim, note diff
           Source confirms original claim → verified
           Source is ambiguous → human-review
           Source can't be fetched → human-review
    → NO: human-review
```

The source is always the tiebreaker between the draft and CoVe. When there
is no source, escalate to the human.

## human-review Triggers

These cases always get `human-review` regardless of CoVe/citation results:
- Direct quotes attributed to named individuals (highest fabrication risk)
- Statistics where the source contains a nearby but different number
- Attributions where the source describes a different role or action
- Any claim with no cited source that CoVe contradicts
