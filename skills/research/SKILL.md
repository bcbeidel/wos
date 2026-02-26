---
name: research
description: >
  This skill should be used when the user wants to "investigate",
  "research", "look into", "what do we know about", "compare options",
  "evaluate feasibility", "analyze the landscape", "find out about",
  "deep dive into", "explore alternatives", or any request to conduct
  a structured investigation and produce a research document.
argument-hint: "[topic or question to investigate]"
user-invocable: true
compatibility: "Requires Python 3, WOS plugin (url_checker, validate, reindex), WebSearch, WebFetch"
---

# Research Skill

Conduct structured investigations using the SIFT framework (Stop,
Investigate the source, Find better coverage, Trace claims). Produces
research documents in `/artifacts/research/` with verified sources
and structured findings.

## Mode Detection

Detect the research mode from the question framing:

| Question pattern | Mode | Intensity |
|-----------------|------|-----------|
| "What do we know about X?" | deep-dive | High |
| "What's the landscape for X?" | landscape | Medium |
| "How does X work technically?" | technical | High |
| "Can we do X with our constraints?" | feasibility | Medium |
| "How does X compare to competitors?" | competitive | Medium |
| "Should we use A or B?" | options | High |
| "How did X evolve / what's the history?" | historical | Low |
| "What open source options exist for X?" | open-source | Medium |

If ambiguous, ask: "What kind of investigation would be most useful?
A **deep dive** (comprehensive), **options comparison**, or
**feasibility study**?"

## Workflow

All modes follow the same workflow with varying SIFT intensity.
See `references/research-workflow.md` for the full 6-phase process.

## Output Document Format

The final research document is placed at `artifacts/research/{date}-{slug}.md`
with simplified YAML frontmatter:

```yaml
---
name: "Title of the investigation"
description: "One-sentence summary of findings"
type: research
sources:
  - https://example.com/primary-source
  - https://example.com/another-source
related:
  - artifacts/research/2026-01-15-related-topic.md
---
```

Write the document directly, then run reindex and validate
(see `references/python-utilities.md`).

## Document Structure Convention

**LLMs lose attention in the middle of long documents.** Structure the research
document so that:
- **Top:** Summary with key findings and actionable insights
- **Middle:** Detailed analysis, evidence, source evaluation, counter-evidence
- **Bottom:** Key takeaways, limitations, and suggested follow-up questions

The first and last sections are what an agent is most likely to retain. Write
for that.

## Key Rules

- **SIFT every source.** No source enters the document unverified.
  See `references/sift-framework.md`.
- **Source hierarchy matters.** Prefer official docs over blog posts.
  See `references/source-evaluation.md`.
- **Counter-evidence is required** for deep-dive, options, and technical modes.
  Actively search for disagreement.
- **Output is a research document.** Write the final artifact directly with
  `type: research` frontmatter, then run reindex and validate.
- **Authority annotations.** Each source in the final document should note
  its tier in the source hierarchy.
- **Challenge before synthesis.** Never skip the Challenge phase. Assumptions
  check and premortem run on every mode. ACH runs on deep-dive, options,
  competitive, and feasibility. See `references/challenge-phase.md`.
- **Log search protocol.** Record every search during Phase 2 (Gather).
  Format with `python3 -m wos.research_protocol format` and include in
  the final document. See `references/research-workflow.md` Phase 2.
- **Confidence levels on every finding.** Annotate each finding as HIGH,
  MODERATE, or LOW based on source convergence and tier. See
  `references/research-workflow.md` Phase 5.
