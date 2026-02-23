# Research Investigate Workflow

Multi-phase investigation process. All research modes follow these phases,
with SIFT intensity varying by mode (see research-modes.md).

## Phase 1: Frame the Question

1. Restate the user's question in a precise, answerable form
2. Identify the research mode from question framing (see SKILL.md)
3. Break the question into 2-4 sub-questions
4. Confirm scope with the user: "I'll investigate [question] by looking at
   [sub-questions]. Sound right?"
5. Note any constraints (time period, domain, technology stack)

## Phase 2: Initial Source Gathering

1. Conduct breadth-first web searches across the sub-questions
2. Aim for 10-20 candidate sources (more for deep-dive, fewer for historical)
3. For each candidate, record: URL, title, publication date, author/org
4. Flag all sources as **unverified** at this stage
5. Prioritize diversity — different organizations, perspectives, source types

## Phase 3: Verify Sources

Run mechanical URL verification on all gathered sources before SIFT evaluation.
See `references/source-verification.md` for full instructions.

1. Format all gathered sources as JSON: `[{"url": "...", "title": "..."}, ...]`
2. Run: `echo '<json>' | python3 -m wos.source_verification`
3. Review the results:
   - Remove sources with action `removed` from your list
   - For sources with action `flagged`: update cited titles if mismatched,
     note access issues for paywalled sources
4. If all sources were removed, gather new sources before proceeding
5. Report verification results to the user before continuing

## Phase 4: Source Evaluation (SIFT)

Apply SIFT framework (see sift-framework.md) at the mode's intensity level.

For each source:

1. **Stop** — Is this source known to me? Flag as unverified if not.
2. **Investigate** — Check domain authority, author credentials, potential bias.
   Classify into source hierarchy tier (T1-T6, see source-evaluation.md).
3. **Find better** — For key claims, search for the same information from a
   higher-tier source. Upgrade when found.
4. **Trace** — For critical claims, follow the citation chain to the primary
   source. Verify the claim matches the original context.

After evaluation:
- Drop sources below T5 unless no better source exists
- Never cite T6 (AI-generated) as a source
- Annotate remaining sources with their tier

## Phase 5: Synthesis

1. Organize findings by sub-question
2. For each sub-question, note:
   - Points of agreement across sources (strong evidence)
   - Points of disagreement (contested or uncertain)
   - Gaps where evidence is missing
3. Rate overall evidence strength: strong / moderate / weak / insufficient
4. If mode requires counter-evidence: dedicate a section to arguments,
   evidence, or perspectives that challenge the main findings

## Phase 6: Implications

1. Connect findings to the user's context and decisions
2. Identify actionable insights (what should change based on these findings?)
3. Note limitations — what couldn't be determined and why
4. Suggest follow-up questions if the investigation revealed new unknowns

## Phase 7: Produce Research Document

Create the research document via `/wos:create` with the following frontmatter:

```yaml
---
name: "Concise summary of the investigation"
description: "One-sentence summary of findings"
type: research
sources:
  - https://verified-source-1.example.com
  - https://verified-source-2.example.com
related:
  - artifacts/research/related-doc.md
---
```

Structure the document for LLM consumption (lost-in-the-middle convention):

1. **Top:** Summary with key findings and actionable insights
2. **Middle:** Detailed analysis by sub-question, evidence, counter-evidence
3. **Bottom:** Key takeaways, limitations, and follow-up questions

The document will be placed at `artifacts/research/{date}-{slug}.md`.

## Quality Checklist

Before finalizing, verify:
- [ ] All sources passed URL verification (Phase 3)
- [ ] All sources have been SIFT-evaluated at the mode's intensity
- [ ] Sources are annotated with hierarchy tiers
- [ ] Counter-evidence section present (if mode requires it)
- [ ] No T6 (AI-generated) sources cited
- [ ] Findings distinguish between strong and weak evidence
- [ ] Implications are connected to the user's context
- [ ] Document passes `parse_document()` validation
