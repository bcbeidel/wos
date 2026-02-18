# Token Budget Estimation Design

**Issue:** [#7 — Token budget estimation in /wos:health](https://github.com/bcbeidel/wos/issues/7)
**Date:** 2026-02-18

## Problem

WOS produces context files loaded into agent context windows but has no
visibility into aggregate token cost. Users cannot tell when their context
system crosses the threshold where additional content degrades agent
performance.

## Decision

Add token budget estimation to `/wos:health` output via a new standalone
module.

## Approach: `wos/token_budget.py`

One public function:

```python
def estimate_token_budget(
    documents: list[Document],
    warning_threshold: int = 40_000,
) -> dict:
```

### Estimation

- `word_count × 1.3` per file (`len(raw_content.split()) * 1.3`, rounded to int)
- No tokenizer dependency — accurate within ~10% for English markdown

### Scope

- `context/` files only (topics + overviews)
- No baseline (CLAUDE.md, rules), no artifacts (research, plans)
- Caller (health script) filters documents before passing them in

### Output Structure

```json
{
  "total_estimated_tokens": 54100,
  "warning_threshold": 40000,
  "over_budget": true,
  "areas": [
    {"area": "python", "files": 5, "estimated_tokens": 7200},
    {"area": "git", "files": 5, "estimated_tokens": 7800}
  ]
}
```

### Issue Generation

If `over_budget` is true, return a single issue dict:

- `severity: warn`
- `validator: "token_budget"`
- Message: "Total context estimated at ~{N} tokens (threshold: {T}). Consider reducing content or splitting areas."

## Health Script Integration

In `scripts/check_health.py`:

1. Filter parsed documents to `context/` paths
2. Call `estimate_token_budget(context_docs)`
3. Add returned dict as `"token_budget"` key in top-level JSON
4. Append warn issue to issues list if over budget (participates in status determination)

Always runs. No new CLI flags.

## Testing

Unit tests in `tests/test_token_budget.py` using inline markdown strings:

- Basic estimation: verify `words × 1.3` math
- Per-area grouping: multiple docs across areas
- Under threshold: `over_budget: false`, no issue
- Over threshold: `over_budget: true`, one warn issue
- Empty input: zero tokens, empty areas
- Custom threshold: non-default threshold respected

## Non-Goals

- No tokenizer library (tiktoken, etc.)
- No baseline or artifact counting
- No per-file token issues (existing `check_size_bounds` covers file size)
- No maintain/trim recommendations
- No configurable threshold via frontmatter or config file
- No changes to health skill workflows (SKILL.md, references)
