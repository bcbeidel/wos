# Research Workflow — Gather & Verify (Phases 1-3)

Eight-phase investigation process. All research modes follow these phases,
with SIFT intensity and Challenge sub-steps varying by mode (see
research-modes.md).

The research document is created in Phase 2 and built progressively —
each phase writes its output to disk so work survives context resets.

For Phases 4-6 (analysis, synthesis, finalization), see
`references/research-synthesis.md`.

## Resuming After Context Reset

If a document already exists at `docs/research/{date}-{slug}.md` with
`<!-- DRAFT -->` near the top, a previous session started this investigation.
Read the document to determine which phases are complete:

- Has `sources:` in frontmatter but no tier annotations in body → resume at Phase 3
- Has tier annotations but no `## Challenge` section → resume at Phase 4 (see `references/research-synthesis.md`)
- Has `## Challenge` section but no `## Findings` section → resume at Phase 5 (see `references/research-synthesis.md`)
- Has `## Findings` section but no `## Claims` section → resume at Phase 5.5a (see `references/research-synthesis.md`)
- Has `## Claims` section with `unverified` entries → resume at Phase 5.5b (see `references/research-synthesis.md`)
- Has `## Claims` section with no `unverified` entries but still has `<!-- DRAFT -->` → resume at Phase 6 (see `references/research-synthesis.md`)

When resuming, read the document fully to recover context before continuing.

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

8. **Write the initial document to disk.** Create the file at
   `docs/research/{date}-{slug}.md` with a `<!-- DRAFT -->` marker,
   frontmatter containing all gathered source URLs, and a sources table:

```yaml
---
name: "Concise summary of the investigation"
description: "One-sentence summary (update in Phase 5)"
type: research
sources:
  - https://gathered-source-1.example.com
  - https://gathered-source-2.example.com
related: []
---
<!-- DRAFT — investigation in progress -->

# [Title]

## Sources

| # | URL | Title | Author/Org | Date | Status |
|---|-----|-------|-----------|------|--------|
| 1 | ... | ...   | ...       | ...  | unverified |

## Search Protocol (WIP)

<!-- search-protocol
{"entries": [], "not_searched": []}
-->

Update this section after each search. Replace the JSON in the comment
above with the current accumulated protocol.
```

The search protocol JSON lives in the `<!-- search-protocol ... -->` comment
(not in memory or frontmatter) so it survives context resets. After each
search, update the comment with the accumulated JSON.

## Phase 3: Verify & Evaluate

Mechanical URL verification followed by SIFT evaluation in a single phase.

### URL Verification

1. Collect all source URLs from the document's frontmatter
2. Use `wos.url_checker.check_urls()` to verify reachability:

   ```bash
   uv run <plugin-scripts-dir>/check_url.py \
       'https://example.com/source-1' \
       'https://example.com/source-2'
   ```

   (Full reference: `references/source-verification.md`)
3. Review the results:
   - Remove sources where `reachable=False` with status 404 or 0
   - Keep sources where `reachable=False` with status 403/5xx but note issues
4. If all sources removed, gather new sources before proceeding
5. Report verification results to the user before continuing

### SIFT Evaluation

Apply SIFT framework (see `references/sift-framework.md`) at the mode's
intensity level. Classify each source into a tier (T1-T6, see
`references/source-evaluation.md`).

After evaluation:
- Drop sources below T5 unless no better source exists
- Never cite T6 (AI-generated) as a source
- Annotate remaining sources with their tier

5. **Update the document on disk.** Remove failed URLs from the `sources:`
   frontmatter list. Update the sources table with verification status and
   tier annotations:

```
| # | URL | Title | Author/Org | Date | Tier | Status |
|---|-----|-------|-----------|------|------|--------|
| 1 | ... | ...   | ...       | ...  | T2   | verified |
| 2 | ... | ...   | ...       | ...  | T4   | verified (403) |
```
