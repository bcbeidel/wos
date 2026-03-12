---
name: Research Agent Payload
description: Self-contained Phase 2-9 research instructions for background subagents dispatched by execute-plan
---

# Research Agent Payload

Self-contained instructions for executing a research investigation.
You have received an **approved research brief** containing:

- **Research question** — the precise question to investigate
- **Sub-questions** — 2-4 sub-questions that structure the investigation
- **Research mode** — one of 8 modes (see Mode Matrix below)
- **Search strategy** — initial search terms and source types
- **Output path** — where to save the research document (e.g., `docs/research/{date}-{slug}.md`)

Your job is to execute Phases 2-9 of the research workflow using these
pre-approved inputs. Do not re-frame the question or modify the sub-questions.

## Output Document Format

Save to the output path specified in your brief. Use this frontmatter:

```yaml
---
name: "Title of the investigation"
description: "One-sentence summary of findings"
type: research
sources:
  - https://example.com/primary-source
related:
  - docs/research/related-topic.md
---
```

Begin the document with the research brief text (provided to you),
followed by a `<!-- DRAFT -->` marker, then proceed through the phases.

---

## Phase 2: Gather and Extract

### Search Budgets by SIFT Rigor

| SIFT Rigor | Searches per sub-question | Total budget |
|------------|---------------------------|--------------|
| Low        | 2-3                       | 5-10         |
| Medium     | 3-5                       | 10-15        |
| High       | 5-8                       | 15-25        |

Process one sub-question at a time. For each sub-question, complete the
full gather-and-extract cycle before moving to the next:

### Per sub-question:

**Gather.** Repeat until coverage is sufficient or budget is exhausted:

1. Execute a search. Aim for 10-20 candidates total across all sub-questions.
2. For each candidate: record URL, title, publication date, author/org. Flag as **unverified**.
3. Log the search:

```json
{"query": "terms", "source": "google", "date_range": "2024-2026", "results_found": 12, "results_used": 3}
```

4. **Reflect.** After every 2-3 searches, assess: does this sub-question have
   coverage? Are results converging? Continue or stop.

> **Source diversity:** `WebSearch` routes through a single engine. Vary
> query terms to surface different source types. Fetch known database URLs
> directly when relevant. Log `"google"` as the source honestly.

> **Fetch failures:** Retry failed `WebFetch` calls individually. Retry
> 3xx with redirect URL. Keep 403 if from published venue. Retry timeouts
> once, then skip. Do not drop sources solely because fetching failed.

**Extract.** For each fetched source, extract relevant content verbatim and
discard boilerplate (navigation, ads, sidebars, unrelated content). This is
**lossless extraction**, not summarization — Phases 7-8 need original
source content for claim verification.

Format per source:

```markdown
### Source [1]: asyncio — Asynchronous I/O
- **URL:** https://docs.python.org/3/library/asyncio.html
- **Author/Org:** Python Software Foundation | **Date:** 2024

**Re: How does asyncio handle concurrency?**
> "The library provides a foundation for writing single-threaded concurrent
> code using coroutines, multiplexing I/O access over sockets and other
> resources, running network clients and servers, and other related
> primitives." (Introduction, para 1)
```

Each extract links to its sub-question, preserves exact wording, and
notes location within the source for later verification.

**Write to disk.** After extracting for the current sub-question, update
the DRAFT document on disk with the new sources and structured extracts.
This ensures fetched content from completed sub-questions is eligible for
context compression before starting the next sub-question.

**Deferred sources.** If a search for the current sub-question surfaces a
source relevant to a different sub-question, note it in a
`<!-- deferred-sources -->` comment in the DRAFT document with the URL and
which sub-question it applies to. Pick up deferred sources when processing
that sub-question.

### After all sub-questions:

5. Record skipped sources in `not_searched` with reasons.
6. **Verify DRAFT state.** The document should have `type: research`
   frontmatter, a `<!-- DRAFT -->` marker, a sources table
   (# | URL | Title | Author/Org | Date | Status), structured extracts
   for every sub-question, and a `<!-- search-protocol ... -->` comment
   containing the accumulated JSON.

### Phase Gate: Phase 2 → Phase 3

DRAFT file exists on disk with structured extracts for all sub-questions.

---

## Phase 3: Verify Sources

Collect URLs from frontmatter. Run URL verification:

```bash
uv run <plugin-scripts-dir>/check_url.py URL1 URL2 ...
```

Result handling:
- **404 or status 0 (DNS failure):** Drop from source list.
- **403 or 5xx:** Keep source, note access issue.
- **All sources removed:** Stop and gather new sources before proceeding.

Update document on disk: remove failed URLs from `sources:`, update
sources table statuses.

**Example — Phase 3→4 progression:**

| # | URL | Title | Status | Tier |
|---|-----|-------|--------|------|
| 1 | https://docs.python.org/... | asyncio docs | verified → | T1 |
| 2 | https://blog.example.com/... | My Tips | removed (404) → | — |
| 3 | https://realpython.com/... | Async Guide | verified (403) → | T3 |

Phase 3 updates the Status column. Phase 4 adds the Tier column.

### Phase Gate: Phase 3 → Phase 4

URLs checked, unreachable removed from frontmatter.

---

## Phase 4: Evaluate Sources (SIFT)

Apply SIFT (Stop, Investigate, Find better, Trace) to each source:

1. **Stop** — Flag as "unverified" until remaining steps complete.
2. **Investigate** — Check domain authority, author credentials, publication
   reliability. Classify into tier (see Source Hierarchy below).
3. **Find better** — For key claims, search for higher-tier sources. If
   found, upgrade. Note claims with limited sourcing.
4. **Trace** — For critical claims, follow citation chains to primary
   source. Verify claim matches original context.

After evaluation: drop sources below T5, never cite T6.

### SIFT Intensity by Mode

| Mode | Stop | Investigate | Find Better | Trace |
|------|------|-------------|-------------|-------|
| deep-dive | Always | Full | Full | Key claims |
| landscape | Always | Domain only | Top 3 claims | Skip |
| technical | Always | Full | Full | All claims |
| feasibility | Always | Domain only | Key claims | Skip |
| competitive | Always | Full | Key claims | Skip |
| options | Always | Full | Full | Key claims |
| historical | Always | Domain only | Key claims | Key claims |
| open-source | Always | Repo metrics | Key claims | Skip |

### Source Hierarchy (T1-T6)

- **T1 — Official docs:** Project documentation, standards bodies (W3C, IETF), original author writings
- **T2 — Institutional research:** University departments, think tanks, industry consortia (CNCF)
- **T3 — Peer-reviewed:** Journals, conference proceedings, published books by domain experts
- **T4 — Expert practitioners:** Recognized experts in their domain, core maintainer blogs, conference talks
- **T5 — Community content:** High-voted Stack Overflow, community blogs, forum consensus
- **T6 — AI-generated:** LLM outputs without primary source verification. Never cite as a source.

### Authority Annotation

Annotate tiers in the document body, not the frontmatter:

```
- https://docs.python.org/3/library/asyncio.html (T1: official docs)
- https://martinfowler.com/articles/microservices.html (T4: expert practitioner)
```

### Red Flags

- No author or organization identified
- Circular sourcing — multiple sources citing the same unverified origin
- Outdated information relative to domain currency
- Conflict of interest — vendor-sponsored research about own product
- Survivorship bias — only success stories, no failures

### Phase Gate: Phase 4 → Phase 5

Sources table has Tier + Status columns for all remaining sources.

---

## Phase 5: Challenge

Run challenge sub-steps based on mode:

| Mode | Assumptions | ACH | Premortem |
|------|-------------|-----|----------|
| deep-dive, feasibility, competitive, options | Yes | Yes | Yes |
| landscape, technical, historical, open-source | Yes | No | Yes |

### Assumptions Check (All Modes)

1. List 3-5 key assumptions underlying emerging findings
2. For each: what evidence supports it? contradicts it? impact if false?
3. Flag assumptions with weak or no supporting evidence

Output format:

| Assumption | Supporting Evidence | Counter-Evidence | Impact if False |
|------------|-------------------|------------------|-----------------|
| [assumption] | [evidence for] | [evidence against] | [impact] |

### Analysis of Competing Hypotheses (Mode-Conditional)

Triggered for: deep-dive, options, competitive, feasibility.

1. Generate 3+ hypotheses including at least one contradicting your
   emerging finding. Anti-anchoring: ask "What would someone who
   disagrees propose?" and add it.
2. Rate each evidence item against each hypothesis: **C** (consistent),
   **I** (inconsistent), **N** (neutral).
3. Select the hypothesis with fewest inconsistencies (not most
   consistencies).

Output format:

| Evidence | Hypothesis A | Hypothesis B | Hypothesis C |
|----------|-------------|-------------|-------------|
| [evidence] | C | I | N |
| Inconsistencies | 1 | 1 | 0 |

Selected: [Hypothesis] — fewest inconsistencies. Rationale: [why].

### Premortem (All Modes)

1. Assume the main conclusion is wrong
2. Generate 3 reasons why: overweighted evidence? missing perspective?
   what could change?
3. Assess plausibility (high/medium/low) and whether conclusion needs
   qualifying

Output format:

| Failure Reason | Plausibility | Impact on Conclusion |
|----------------|-------------|---------------------|
| [reason] | medium | Qualifies finding #2 |

Update document on disk with `## Challenge` section.

### Phase Gate: Phase 5 → Phase 6

`## Challenge` section exists on disk.

---

## Phase 6: Synthesize

Organize findings by sub-question. Annotate each finding with a
confidence level:

| Level | Criteria |
|-------|----------|
| HIGH | Multiple independent T1-T3 sources converge; methodology sound |
| MODERATE | Credible sources support; primary evidence not directly verified |
| LOW | Single source; unverified; some counter-evidence exists |

### Writing Constraints

- Every quote, statistic, attribution, and superlative must trace to a
  cited source. If no source supports a factual claim, do not include it.
- General observations and trend descriptions are fine without specific
  citations.
- If mode requires counter-evidence, dedicate a section to arguments and
  perspectives that challenge the main findings.

Connect findings to the user's context, identify gaps, suggest follow-ups.
Update document on disk with `## Findings` section. Update frontmatter
`description:` to reflect actual findings.

### Phase Gate: Phase 6 → Phase 7

`## Findings` section exists on disk.

---

## Phase 7: Self-Verify Claims (CoVe)

Extract every quote, statistic, attribution, and superlative from
Findings into a `## Claims` table.

### Claim Types

| Type | Example |
|------|---------|
| quote | "Software is eating the world" — Andreessen |
| statistic | "30+ integrations available" |
| attribution | "Chesky founded Airbnb" |
| superlative | "the first company to achieve..." |

General observations and methodology notes do not need registration.

### Claims Table Format

| # | Claim | Type | Source | Status |
|---|-------|------|--------|--------|
| 1 | "exact claim text" | quote | [1] | unverified |

Source references map to the numbered Sources table. All claims start as
`unverified`. Claims without a citeable source use `—` as source.

### CoVe Procedure

Chain-of-Verification catches fabrication from parametric knowledge.

1. Extract all quotes, statistics, attributions, and superlatives from
   Findings into the Claims Table.
2. For each claim, generate a verification question (e.g., "What exact
   words did [person] say about [topic]?").
3. Answer each question in a **separate context without the draft
   document**. This prevents confirmation bias — it is the reason
   Phase 7 is a distinct phase.
4. Compare: CoVe agrees → advance to Phase 8. CoVe contradicts → route
   through contradiction resolution. CoVe uncertain → advance to Phase 8.

### Contradiction Resolution

When CoVe contradicts a claim: if the claim has a cited source, escalate
to Phase 8 — the source is the tiebreaker between draft and CoVe. If no
source, assign `human-review`.

### Phase Gate: Phase 7 → Phase 8

`## Claims` table populated, CoVe complete.

---

## Phase 8: Citation Re-Verify

Re-fetch cited sources and verify each claim against the actual content.

1. Group remaining `unverified` claims by source URL.
2. Re-fetch each source via WebFetch.
3. Search fetched content for the specific fact asserted.
4. Assign status:

### Resolution Statuses

| Status | Meaning |
|--------|---------|
| verified | Passed CoVe AND citation re-verification confirmed |
| corrected | Didn't match source; updated to match (note original) |
| removed | Not found in source; deleted from document body |
| unverifiable | Source couldn't be fetched (403/timeout); flagged in document |
| human-review | Ambiguous result, or uncited claim that CoVe couldn't confirm |

### human-review Triggers

Always assign `human-review` regardless of other results:
- Direct quotes attributed to named individuals (highest fabrication risk)
- Statistics where the source contains a nearby but different number
- Attributions where the source describes a different role
- Any claim with no cited source that CoVe contradicts

**Example — Phase 7→8 flow:**

| # | Claim | Type | Source | Status |
|---|-------|------|--------|--------|
| 1 | "added in Python 3.4" | attribution | [1] | unverified → verified |
| 2 | "3x faster than threading" | statistic | [2] | unverified → corrected ("up to 2x") |
| 3 | "Guido designed asyncio" | attribution | — | unverified → human-review |

Update document on disk — no `unverified` claims remain.

### Phase Gate: Phase 8 → Phase 9

No `unverified` claims in Claims Table.

---

## Phase 9: Finalize

1. **Restructure** for lost-in-the-middle convention:
   - Top: summary with key findings (annotated with confidence) and
     search protocol summary
   - Middle: detailed analysis by sub-question, evidence, Challenge output
   - Bottom: key takeaways, limitations, follow-ups, full search protocol
     table

2. **Format search protocol.** Extract JSON from
   `<!-- search-protocol ... -->`, render as:

| Query | Source | Date Range | Found | Used |
|-------|--------|------------|-------|------|

Include summary line: `N searches across M sources, X found, Y used`.

3. **Remove `<!-- DRAFT -->`** marker.
4. **Verify claims.** No `unverified` in Claims Table. `unverifiable` and
   `human-review` annotated in body.
5. **Reindex and validate:**

```bash
uv run <plugin-scripts-dir>/reindex.py --root .
uv run <plugin-scripts-dir>/audit.py <file> --root . --no-urls
```

### Phase Gate: Phase 9 → Done

`<!-- DRAFT -->` removed, audit passes.

---

## Research Mode Matrix

| Mode | Min Sources | SIFT Rigor | Counter-Evidence | Challenge | Claim Verification |
|------|-------------|------------|------------------|-----------|-------------------|
| deep-dive | 8+ | High | Required | Full | Full |
| landscape | 6+ | Medium | Optional | Partial | Full |
| technical | 6+ | High | Required | Partial | Full |
| feasibility | 4+ | Medium | Required | Full | Full |
| competitive | 6+ | Medium | Optional | Full | Full |
| options | 6+ | High | Required | Full | Full |
| historical | 4+ | Low | Optional | Partial | Full |
| open-source | 4+ | Medium | Optional | Partial | Full |

**Full** challenge = Assumptions check + ACH + Premortem.
**Partial** challenge = Assumptions check + Premortem (no ACH).

### Mode Descriptions

- **deep-dive** ("What do we know about X?") — Comprehensive single-topic investigation. Cast wide net, narrow to highest-quality sources. Cover background, current state, key debates, implications.
- **landscape** ("What's the landscape for X?") — Broad domain survey. Map major players, trends, categories. Prioritize breadth over depth.
- **technical** ("How does X work technically?") — Deep technical investigation. Focus on architecture, implementation, performance, tradeoffs. Prefer official docs and expert practitioners.
- **feasibility** ("Can we do X given our constraints?") — Evaluate achievability given constraints. Identify blockers, risks, prerequisites. Actively search for reasons it might fail.
- **competitive** ("How does X compare to competitors?") — Systematic comparison across defined criteria. Watch for vendor bias in sources.
- **options** ("Should we use A or B?") — Structured comparison of alternatives. Each option gets equal investigation depth.
- **historical** ("How did X evolve?") — Trace development over time. Identify key inflection points, decisions, and consequences.
- **open-source** ("What open source options exist for X?") — Survey projects by stars, maintenance activity, community health, documentation quality, and license compatibility.

---

## Quality Checklist

Before removing `<!-- DRAFT -->`, verify each gate:

- [ ] Phase 2: DRAFT file on disk with structured extracts for all sub-questions
- [ ] Phase 3: URLs verified, unreachable removed
- [ ] Phase 4: Tiers assigned to all sources
- [ ] Phase 5: Challenge section written
- [ ] Phase 6: Findings section written
- [ ] Phase 7: Claims extracted, CoVe complete
- [ ] Phase 8: No unverified claims remain
- [ ] Phase 9: DRAFT removed, audit passes

---

## CLI Commands

`<plugin-scripts-dir>` refers to the `scripts/` directory at the root
of the WOS plugin.

### Validate a Document

```bash
uv run <plugin-scripts-dir>/audit.py <file> --root . [--no-urls]
```

### Regenerate Index Files

```bash
uv run <plugin-scripts-dir>/reindex.py --root .
```

### Check URL Reachability

```bash
uv run <plugin-scripts-dir>/check_url.py URL1 URL2 ...
```
