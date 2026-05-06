---
name: Brief Content Quality
description: When `.briefs/<primitive>.brief.md` exists, the *So-what* paragraph names a specific gap / user / problem rather than reading as a category description, and *Scope boundaries* lists concrete in/out items rather than vague hedges.
paths:
  - "**/.briefs/*.brief.md"
---

When `.briefs/<primitive>.brief.md` exists, two qualities are LLM-judged: the *So-what* names a specific intent rather than a category description, and *Scope boundaries* lists concrete items rather than vague hedges.

**Why:** the brief is the trace of the build's original intent. Presence and section completeness are scripted (Tier-1 `brief-presence`); content quality is not — distinguishing a generic "this codifies best practices for X" from a specific "we need this because Y team kept hitting Z problem in PR review last quarter" requires reading both prose passages and judging whether they anchor in specifics. A brief that fails this rule still exists, has all sections, and parses cleanly — but the trace is decorative rather than load-bearing. Future readers cannot reconstruct *why* the build was scoped the way it was.

**How to apply:** read `.briefs/<primitive>.brief.md`. Judge two passages:

1. **`## So-what` paragraph.** Look for: a named user (or role / team / persona); a named gap, recurring problem, or constraint; specifics that could only apply to *this* primitive. Generic framing ("this codifies best practices for X", "captures conventions for Y", "improves the developer experience") fails — those sentences could apply to any build of any primitive. A retroactive brief authored after the fact is acceptable; what matters is that the paragraph anchors in specifics, not in category description.

2. **`## Scope boundaries` *In* and *Out* lists.** Look for: concrete file paths, named workflows, named audit dimensions, specific technologies. Vague hedges ("the usual stuff", "anything related to X", "everything we discussed") fail. Empty boundary lists fail outright — the build had no boundaries means the build had no scope.

A brief failing either passage is `warn`. Severity is always `warn` — the build still works; the trace just leaks intent. The user (not the audit) decides whether the brief is worth rewriting.

```markdown
# Failing So-what:

## So-what

This skill-pair codifies the conventions for authoring foo primitives,
making it easier for developers to follow established best practices
when working with foo across the toolkit.

# Better:

## So-what

The foo audit hand-rolled by the data team in Q1 caught two production
incidents but couldn't be reused outside their plugin. We need a
canonical foo audit that other plugins can route to, replacing the
N=3 partial copies currently in the codebase. Target audience: any
plugin author who needs to validate a foo before publishing.
```

**Common fail signals (audit guidance):**

- *So-what* uses the construction "this skill / this rubric / this codifies / this captures…" in its first sentence. A brief is about a *problem*, not a self-introduction.
- *Scope boundaries* in/out lists are bullets containing only the words "the usual" / "anything related" / "everything we discussed" / "you know, the standard things".
- *In* and *Out* lists are empty or each contains only one bullet.
- The brief reads as a project description (`*So-what*` is two paragraphs of feature lists) rather than a problem description (one paragraph naming a recurring pain point).

**Exception:** if the brief is documented as a deliberate placeholder ("see `.designs/foo.design.md` for full intent — brief is a stub"), the audit's role is to flag the placeholder once, not repeatedly. Surface as `warn` with a recommendation to either flesh out the brief or remove it; do not emit if both flesh-out and remove are explicitly declined upstream.
