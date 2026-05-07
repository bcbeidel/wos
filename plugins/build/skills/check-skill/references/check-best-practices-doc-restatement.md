---
name: Best-Practices-Doc Restatement
description: When a SKILL.md cites a `*-best-practices.md` (or comparable SSoT reference), the SKILL.md body must not duplicate that doc's named principles — link only.
paths:
  - "**/SKILL.md"
---

**Why:** A SKILL.md that links to `_shared/references/<topic>-best-practices.md` already carries the authoritative source — the link is the contract. When the body restates the linked doc's principles, the SKILL.md grows by 5–20 lines per section without adding signal: a reader who follows the link sees the canonical statement; a reader who doesn't sees a paraphrase that drifts on every edit. The cost surfaces when the source-of-truth doc evolves and the SKILL.md copy stays frozen, contradicting the link target. Source principle: skill-best-practices.md and skill-pair-best-practices.md ("If the SKILL.md cites a `*-best-practices.md`, the SKILL.md does not restate that doc's named principles.").

**How to apply:** When a SKILL.md links to a `*-best-practices.md` (or any comparable SSoT — `check-skill-pattern.md`, `primitive-routing.md`, `skill-pair-best-practices.md`), the SKILL.md cites the relevant section by anchor and proceeds. Skill-specific elaborations (a domain-specific example, a primitive-specific tiebreaker) are kept as standalone bullets adjacent to the citation. Verbatim duplicates of the linked doc's named principles are dropped. The Tier-1 helper `check_evaluator_policy_echo` covers one specific case (Evaluator-policy bullets); this Tier-2 dimension covers the broader pattern.

```markdown
## 3. Tier-2 Semantic Dimensions

Evaluator policy: see [check-skill-pattern.md §Evaluator policy](../../_shared/references/check-skill-pattern.md#evaluator-policy).

(No bullet list — the cited section IS the bullet list.)
```

**Common fail signals (audit guidance):**
- A `*-best-practices.md` link in the SKILL.md is followed by 4+ bullets that paraphrase the linked doc's named principles
- Authoring Principles section in a `build-*` SKILL.md restates the same shape rules already named in `<primitive>-best-practices.md`
- "Recovery if a script is written in error: `rm <path>` removes it…" or comparable universal-knowledge stanzas appearing in 3+ build-* SKILL.md
- `### Won't` bullets that restate the frontmatter `description:`'s "Not for…" clause without naming a primitive-specific failure mode

**Exception:** A SKILL.md may include a standalone bullet that elaborates on the linked principle with primitive-specific detail (e.g., a check-bash-script-only edge case). The dimension flags duplication of the doc's general statement, not domain-specific extensions.
