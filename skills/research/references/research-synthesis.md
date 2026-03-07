# Research Synthesis — Challenge, Synthesize & Finalize (Phases 4-6)

Phases 4-6 of the research workflow. For Phases 1-3 (framing, gathering,
verification), see `research-workflow.md`.

## Phase 4: Challenge

Stress-test reasoning before synthesis. See `references/challenge-phase.md`
for full procedures.

Three sub-steps, applied based on research mode (see research-modes.md):

1. **Assumptions check** (all modes) — List 3-5 key assumptions, check
   evidence for/against each, assess impact if false
2. **ACH** (deep-dive, options, competitive, feasibility) — Generate
   competing hypotheses, build evidence matrix, select hypothesis with
   fewest inconsistencies
3. **Premortem** (all modes) — Imagine main conclusion is wrong, generate
   3 failure reasons, assess plausibility

4. **Update the document on disk.** Append a `## Challenge` section with
   the assumptions check, ACH matrix (if applicable), and premortem results.

## Phase 5: Synthesize

1. Organize findings by sub-question
2. For each sub-question, note:
   - Points of agreement across sources (strong evidence)
   - Points of disagreement (contested or uncertain)
   - Gaps where evidence is missing
3. **Annotate each finding with a confidence level:**

| Level | Criteria |
|-------|----------|
| HIGH | Multiple independent T1-T3 sources converge; methodology sound |
| MODERATE | Credible sources support; primary evidence not directly verified |
| LOW | Single source; unverified; some counter-evidence exists |

4. If mode requires counter-evidence: dedicate a section to arguments,
   evidence, or perspectives that challenge the main findings
5. Connect findings to the user's context and decisions
6. Identify actionable insights
7. Note limitations — what couldn't be determined and why
8. Suggest follow-up questions if the investigation revealed new unknowns
9. **Writing constraint for claims:** When writing findings, ensure every
   quote, statistic, attribution, and superlative is traceable to a cited
   source. If you cannot point to a specific source for a factual claim,
   do not include it. General observations and trend descriptions are fine
   without specific citations.

10. **Update the document on disk.** Add a `## Findings` section organized
   by sub-question with confidence levels, counter-evidence (if applicable),
   and a connections/implications section. Update the `description:` in
   frontmatter to reflect actual findings.

## Phase 5.5a: Self-Verify Claims (CoVe)

Extract and self-verify all high-risk claims before citation re-checking.
See `references/claim-verification.md` for claim types, table format, and
full procedure.

1. Scan the Findings section. Extract every quote, statistic, attribution,
   and superlative into a `## Claims` table in the document. All statuses
   start as `unverified`.
2. For each claim, generate a verification question appropriate to its type.
3. Answer each verification question in a **separate LLM call without the
   draft in context** to prevent confirmation bias.
4. Compare CoVe answers to claims:
   - Agrees → advance to Phase 5.5b
   - Contradicts → route through contradiction resolution
     (see `references/claim-verification.md`)
   - Uncertain → advance to Phase 5.5b

5. **Update the document on disk.** The `## Claims` table should now exist
   with all claims extracted and CoVe-processed.

**Gate:** Claims Table populated. All claims processed through CoVe.
Contradictions routed or resolved.

## Phase 5.5b: Citation Re-Verify Claims

Cross-check claims against their cited sources. See
`references/claim-verification.md` for resolution statuses and procedure.

1. Group remaining `unverified` claims by source URL.
2. Re-fetch each source URL via WebFetch.
3. For each claim citing that source, search the fetched content for the
   specific fact. Assign final status: `verified`, `corrected`, `removed`,
   `unverifiable`, or `human-review`.
4. For `corrected` claims: update the claim text in the document body to
   match the source. Note the original wording in the Claims Table.
5. For `removed` claims: delete the claim from the document body. Keep the
   row in the Claims Table with `removed` status.

6. **Update the document on disk.** Claims Table should have no `unverified`
   statuses remaining.

**Gate:** No `unverified` claims remain. `unverifiable` and `human-review`
claims are annotated.

## Phase 6: Finalize Research Document

The document already exists on disk with content from Phases 2-5. This phase
restructures it for the final reader and runs validation.

1. **Restructure for lost-in-the-middle convention:**
   - **Top:** Summary with key findings (each annotated with confidence level)
     and search protocol summary line
   - **Middle:** Detailed analysis by sub-question, evidence, Challenge phase
     output (assumptions, ACH if applicable, premortem), counter-evidence
   - **Bottom:** Key takeaways, limitations, follow-up questions, and full
     search protocol table

2. **Format the search protocol.** Extract the search protocol JSON from
   the `<!-- search-protocol ... -->` comment in the document. Format it
   as a markdown table directly in the document. Use this format:

```markdown
| Query | Source | Date Range | Found | Used |
|-------|--------|------------|-------|------|
| search terms | google | 2024-2026 | 12 | 3 |
```

   Include a one-line summary near the top: `N searches across M sources, X results found, Y used`

   Replace the `## Search Protocol (WIP)` section and its
   `<!-- search-protocol ... -->` comment with the rendered markdown table
   under a final `## Search Protocol` heading (drop the "(WIP)" suffix).

3. **Remove the `<!-- DRAFT -->` marker** from the document.

4. **Verify claims status.** Check the `## Claims` table: no claims should
   have `unverified` status. Claims marked `unverifiable` or `human-review`
   must have annotations visible in the document body (e.g., "[unverifiable —
   source returned 403]" or "[human-review — CoVe contradicted, no source]").

5. **Regenerate index files:**

```bash
uv run <plugin-scripts-dir>/reindex.py --root .
```

6. **Validate the document:**

```bash
uv run <plugin-scripts-dir>/audit.py <file> --root . --no-urls
```

## Quality Checklist

Before removing the `<!-- DRAFT -->` marker, verify:
- [ ] All sources passed URL verification
- [ ] All sources have been SIFT-evaluated at the mode's intensity
- [ ] Sources are annotated with hierarchy tiers
- [ ] Challenge phase completed (assumptions + premortem at minimum)
- [ ] ACH included if mode requires it
- [ ] Every finding annotated with confidence level (HIGH/MODERATE/LOW)
- [ ] Counter-evidence section present (if mode requires it)
- [ ] No T6 (AI-generated) sources cited
- [ ] Search protocol section present with all searches logged
- [ ] All high-risk claims (quotes, statistics, attributions, superlatives) registered in Claims Table
- [ ] No claims with `unverified` status remain
- [ ] `unverifiable` and `human-review` claims annotated in document body
- [ ] Implications connected to the user's context
- [ ] Document passes validation:
  `uv run <plugin-scripts-dir>/audit.py <file> --root . --no-urls`
