---
name: Cross-Rule Conflict
description: No two co-fireable rules contradict each other — following Rule A must not violate Rule B (and vice versa).
paths:
  - "**/.claude/rules/*.md"
  - "**/.claude/rules/**/*.md"
---

For every pair of rules that could co-fire on the same file, verify that following one rule's directives as written does not cause a developer (or Claude) to violate the other. This is a Tier-3 rule — it applies to *pairs* of rules, not to any single rule, and runs only when the audit scope holds multiple rules.

**Why:** Anthropic's guidance is explicit: *"if two rules contradict each other, Claude may pick one arbitrarily."* Arbitrary picking produces inconsistent behavior across sessions and silent regressions when the picked rule changes. Unlike a single-rule defect, a contradiction is invisible from inside either rule — both can be well-formed in isolation yet collide when both load. Severity is `fail`, not `warn`: an arbitrarily-applied rule is worse than no rule because it masquerades as guidance.

**How to apply:** Compute the **co-fire predicate** first — a pair can co-fire when both rules are always-on (no `paths:`), or when their `paths:` globs share at least one matching file. Pairs that cannot co-fire are skipped. For every co-fireable pair, run the **conflict test**: present Rule A verbatim, present Rule B verbatim, and ask "If a developer follows Rule A's directives exactly, does Rule B's guidance contradict?" Then ask the reverse. If either answer is yes, emit a FAIL finding for both rules. Resolution preference: narrow scope so the pair no longer co-fires; merge into one rule with both directives; add an explicit boundary exception ("in files covered by `[other-rule.md]`, [behavior] is acceptable"); or deprecate the older rule.

```
FAIL  .claude/rules/rule-a.md — Conflicts with rule-b.md
  "Rule A says X; Rule B says not-X"
FAIL  .claude/rules/rule-b.md — Conflicts with rule-a.md
  "Rule B says not-X; Rule A says X"
```

**Common fail signals (audit guidance):**
- Two co-fireable rules where following one's directives violates the other's
- Rules whose `paths:` globs overlap on at least one file and whose directives contradict on that file's content
- Two always-on rules issuing opposing guidance on the same topic

**Exception:** Intentionally-overlapping rules where one explicitly dispatches to the other (e.g., a general rule deferring to a specialized rule via "Exception: in files covered by `[other-rule.md]`, follow that rule instead"), or where one rule is a documented generalization of the other and the boundary is named in both. The exception must be explicit in the rule text — implicit overlap still earns a FAIL.
