---
document_type: plan
description: "Build the research skill with SIFT-based source evaluation, 8 investigation modes, and structured output as research documents"
last_updated: 2026-02-17
status: draft
related:
  - 2026-02-17-document-type-models.md
  - 2026-02-17-skill-curate.md
  - ../research/2026-02-17-skills-architecture-design.md
---

# Build Research Skill

## Objective

A `/dewey:research` skill exists that conducts deep investigations using the
SIFT framework (Stop, Investigate the source, Find better coverage, Trace
claims). It supports 8 research modes (deep dive, landscape, technical,
feasibility, competitive, options, historical, open source) that vary in
methodology intensity but all produce standard research documents.

Research documents created by this skill have verifiably higher source quality
than naive search-and-summarize: sources are authority-checked, claims are
traced to primary sources, and counter-evidence is actively sought.

## Context

- Skills architecture: `artifacts/research/2026-02-17-skills-architecture-design.md` §3.3
- Source evaluation reference: to be created as `skills/research/references/source-evaluation.md`
- SIFT framework: Mike Caulfield, University of Washington
- Source hierarchy: official docs > institutional > peer-reviewed > expert > community > AI-generated
- Produces `research` document type in `/artifacts/research/`

## Steps

1. Create `skills/research/SKILL.md` with skill description, conversational
   triggers ("investigate", "research", "look into", "what do we know about",
   "compare options for"), and mode detection from question framing

2. Create `skills/research/references/sift-framework.md`:
   - SIFT steps with agent-actionable guidance per step
   - Source hierarchy with examples
   - Counter-evidence search techniques
   - Claim tracing methodology

3. Create `skills/research/references/research-modes.md`:
   - 8 modes with question patterns, methodology intensity matrix
   - Source count expectations per mode
   - SIFT rigor level per mode
   - Counter-evidence requirements per mode

4. Create `skills/research/workflows/research-investigate.md`:
   - Phase 1: Frame the question (clarify scope, identify sub-questions)
   - Phase 2: Initial source gathering (breadth-first web search, 10-20 candidates)
   - Phase 3: Source evaluation per SIFT (intensity varies by mode)
     - Stop: flag each source as unverified
     - Investigate: check domain authority, author credentials
     - Find better: for key claims, search for more authoritative sources
     - Trace: follow citation chains to primary sources
   - Phase 4: Synthesis (organize by sub-question, note agreement/disagreement,
     rate evidence strength)
   - Phase 5: Implications (connect findings to decisions)
   - Phase 6: Produce research document via curate-add with type=research

5. Write tests: mode detection maps common question patterns correctly,
   SIFT steps are documented in reference files, research document template
   includes all required sections

## Verification

- "What do we know about X?" → deep dive mode detected
- "Should we use A or B?" → options mode detected
- "Can we do X with our constraints?" → feasibility mode detected
- Research output is a valid research document (passes `parse_document()`)
- Research document has sources with authority annotations
- Counter-evidence section is present when mode requires it
- Source hierarchy is referenced during source evaluation
