---
document_type: research
description: "Design principles for wos grounded in agent context research, cognitive science, and software engineering practice"
last_updated: 2026-02-17
sources:
  - url: https://www.anthropic.com/engineering/claude-code-best-practices
    title: "Claude Code Best Practices — Anthropic"
  - url: https://fs.blog/mental-models/
    title: "Mental Models — Farnam Street"
  - url: https://diataxis.fr/
    title: "Diataxis Documentation Framework"
  - url: https://docs.pydantic.dev/latest/
    title: "Pydantic v2 Documentation"
  - url: https://hapgood.us/2019/06/19/sift-the-four-moves/
    title: "SIFT: The Four Moves — Mike Caulfield"
---

# Design Principles

WOS exists to make human + AI collaboration more effective by structuring
knowledge, improving research quality, and validating work at every step.

These principles are organized in three layers: why the system exists (purpose),
how agents and humans work within it (collaboration), and what ensures quality
over time (rigor).

---

## Layer 1: Knowledge Amplifier

The system makes you more effective by structuring what you know.

**1. Source Primacy** — The knowledge base is a curated guide, not a replacement
for primary sources. Every entry points to one. When an agent or human needs to
go deeper, the path is always clear.

**2. Dual Audience** — Every entry serves the agent (structured, token-efficient
context) and the human (readable, navigable content). When these conflict, favor
human readability — agents are more adaptable readers.

**3. Domain-Shaped Organization** — Organized around the domain's natural
structure, not file types or technical categories. The taxonomy should feel
intuitive to a practitioner.

**4. Right-Sized Scope** — Contains what's needed to be effective, and no more.
The curation act is as much about what you exclude as what you include.

**5. Progressive Disclosure** — Layered access so agents can discover what's
available without loading everything. Descriptions before full content. Overviews
before topics. Context before artifacts.

---

## Layer 2: Agent Operating System

The system is the runtime environment for AI agents working alongside you.

**6. Schema-First Design** — Document type models are the single source of truth.
Templates, validators, sections, size bounds, and directory rules all derive from
the models. Adding a new document type means adding to dispatch tables — no
routing changes, no scattered conditionals.

**7. Separation of Observation and Action** — Health observes (read-only,
CI-friendly). Maintain acts (write, requires approval). This separation enables
different permission models and prevents accidental modification.

**8. Convention Over Configuration** — Adding a new mental model is adding a file.
Adding a new document type is adding to dispatch tables. The system should be
extended by following patterns, not by writing integration code.

**9. Derived Artifacts, Not Source-of-Truth Artifacts** — The CLAUDE.md manifest
is a cache regenerated from disk. The rules file is auto-generated from the
schema. Discovery artifacts are always derivable, never the canonical source.

**10. Free-Text Intake** — Users describe intent; the system classifies and
routes. No command memorization. The cost of misclassification is a redirect,
not a failure.

---

## Layer 3: Quality-First Workflow

The system exists because most AI-assisted work lacks rigor.

**11. SIFT at the Source** — Every piece of research passes through Stop,
Investigate, Find better, Trace claims. Sources are authority-checked before
inclusion. Claims are traced to primary sources, not secondary summaries.

**12. Structured Reasoning Before Action** — Mental models (first principles,
inversion, Occam's razor) are available as invocable tools, not afterthoughts.
Thinking clearly is a skill the system supports, not an assumption it makes.

**13. Three-Tier Validation** — Deterministic checks catch structural issues
(Python, fast, CI-friendly). LLM-assisted assessment catches quality issues
(Claude evaluates flagged items). Human judgment catches relevance and scope
issues. Each tier has a clear boundary.

**14. Empirical Feedback** — Observable signals about knowledge base health:
coverage gaps, stale entries, unused content, source drift. Proxy metrics
inform curation decisions. If it can't be measured, it can't be maintained.

**15. Provenance and Traceability** — Every piece of knowledge carries metadata
about where it came from, when it was last validated, and why it's in the
knowledge base. Research documents are the provenance trail for topics they
inform.

---

## From Cognitive Science

These principles apply to knowledge base content specifically.

**16. Explain the Why** — Causal explanations produce better comprehension and
retention than stating facts alone. Every topic explains not just what to do,
but why it works.

**17. Concrete Before Abstract** — Lead with examples and worked scenarios, then
build toward the abstraction. The In Practice section comes before the theory.

**18. Multiple Representations** — Important concepts exist at multiple levels
of depth (overview, topic). Material that helps novices can hinder experts —
label each level clearly so readers self-select.
