# Research Workflow

Six-phase investigation process. All research modes follow these phases,
with SIFT intensity and Challenge sub-steps varying by mode (see
research-modes.md).

## Phase 1: Frame the Question

1. Restate the user's question in a precise, answerable form
2. Identify the research mode from question framing (see SKILL.md)
3. Break the question into 2-4 sub-questions
4. Confirm scope with the user: "I'll investigate [question] by looking at
   [sub-questions]. Sound right?"
5. Note any constraints (time period, domain, technology stack)
6. **Declare search protocol:** State which sources you plan to search
   (e.g., Google, Google Scholar, GitHub, specific documentation sites)
   and what terms you'll use. Initialize the search protocol JSON:

```json
{"entries": [], "not_searched": []}
```

> **Source diversity:** `WebSearch` routes through a single search engine. To
> improve source diversity: (1) vary query terms to surface different source
> types, (2) fetch known database URLs directly (e.g., PubMed, Semantic
> Scholar) when relevant, (3) log `"google"` as the source honestly — this is
> expected. The `not_searched` field should list sources you chose not to
> search, not sources the tool can't access.

## Phase 2: Gather Sources

1. Conduct breadth-first web searches across the sub-questions
2. Aim for 10-20 candidate sources (more for deep-dive, fewer for historical)
3. For each candidate, record: URL, title, publication date, author/org
4. Flag all sources as **unverified** at this stage
5. Prioritize diversity — different organizations, perspectives, source types
6. **Log each search** — after every web search, append to the protocol:

```json
{
  "query": "the search terms used",
  "source": "google|scholar|github|docs|...",
  "date_range": "2024-2026 or null",
  "results_found": 12,
  "results_used": 3
}
```

7. After gathering is complete, record sources you considered but did
   not search in `not_searched` as strings with a brief reason:

```json
"not_searched": [
  "Google Scholar - covered by direct source fetching",
  "PubMed - topic is not biomedical"
]
```

> **Handling fetch failures:** When parallel `WebFetch` calls fail, a single
> failure can cascade to sibling calls ("Sibling tool call errored"). Retry
> failed URLs individually. Common failure modes:
> - **403** — bot protection; source exists but can't be fetched. Retain if
>   from a published venue.
> - **303/301** — redirect; retry with the redirect URL.
> - **Timeout** — retry once, then skip. Do not drop sources solely because
>   fetching failed — assess based on URL verification status.

## Phase 3: Verify & Evaluate

Mechanical URL verification followed by SIFT evaluation in a single phase.

### URL Verification

1. Collect all source URLs into a list
2. Use `wos.url_checker.check_urls()` to verify reachability
   (see `references/source-verification.md`)
3. Review the results:
   - Remove sources where `reachable=False` with status 404 or 0
   - Keep sources where `reachable=False` with status 403/5xx but note issues
4. If all sources removed, gather new sources before proceeding
5. Report verification results to the user before continuing

### SIFT Evaluation

Apply SIFT framework (see `references/sift-framework.md`) at the mode's
intensity level.

For each source:

1. **Stop** — Is this source known to me? Flag as unverified if not.
2. **Investigate** — Check domain authority, author credentials, bias.
   Classify into source hierarchy tier (T1-T6, see `references/source-evaluation.md`).
3. **Find better** — For key claims, search for the same information from a
   higher-tier source. Upgrade when found.
4. **Trace** — For critical claims, follow the citation chain to the primary
   source. Verify the claim matches the original context.

After evaluation:
- Drop sources below T5 unless no better source exists
- Never cite T6 (AI-generated) as a source
- Annotate remaining sources with their tier

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

## Phase 6: Produce Research Document

Create the research document via `/wos:create` with frontmatter:

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

1. **Top:** Summary with key findings (each annotated with confidence level)
   and search protocol summary line
2. **Middle:** Detailed analysis by sub-question, evidence, Challenge phase
   output (assumptions, ACH if applicable, premortem), counter-evidence
3. **Bottom:** Key takeaways, limitations, follow-up questions, and full
   search protocol table

### Inserting the Search Protocol

Format the accumulated search protocol JSON using the CLI:

```bash
echo '<protocol_json>' | python3 -m wos.research_protocol format
```

Insert the rendered table into the **Search Protocol** section at the
bottom of the document. Add the summary line (using `--summary` flag)
near the top of the document.

The document will be placed at `artifacts/research/{date}-{slug}.md`.

## Quality Checklist

Before finalizing, verify:
- [ ] All sources passed URL verification
- [ ] All sources have been SIFT-evaluated at the mode's intensity
- [ ] Sources are annotated with hierarchy tiers
- [ ] Challenge phase completed (assumptions + premortem at minimum)
- [ ] ACH included if mode requires it
- [ ] Every finding annotated with confidence level (HIGH/MODERATE/LOW)
- [ ] Counter-evidence section present (if mode requires it)
- [ ] No T6 (AI-generated) sources cited
- [ ] Search protocol section present with all searches logged
- [ ] Implications connected to the user's context
- [ ] Document passes validation: `python3 scripts/validate.py <file> --no-urls`
