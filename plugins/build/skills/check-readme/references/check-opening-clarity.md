---
name: Opening Clarity
description: The README's H1, one-sentence description, and opening paragraph must let a stranger answer "what is this and should I care" in the top 30 seconds.
paths:
  - "**/README.md"
  - "**/Readme.md"
---

Open with the project name as H1, a one-sentence "what is this" statement immediately below, and 2-3 sentences naming the problem and audience — before any feature list, screenshot wall, or marketing copy.

**Why:** The top 30 seconds are the only bytes most readers see — package-index visitors, dependency-list browsers, and search-result skimmers bounce in seconds if they cannot answer "what is this and should I care". An H1 that is a tagline, an opening that leads with `Features:`, or a first content block that is a screenshot all fail that test. Source principles: *One-sentence "what is this" on line 2*; *Wall-of-features before "what is this"* (anti-pattern).

**How to apply:** Verify the H1 names the project (not marketing copy). Verify the next line or paragraph answers "what is this" in one sentence. Verify the next 2-3 sentences state the problem solved and the intended audience. If the opening is a feature list, screenshot, or implementation tour, rewrite the first three content lines: H1 (project name), one-sentence "what is this", 2-3 sentences stating the problem.

```markdown
# LFF
A Python web framework focused on low-latency request handling.

Built for teams running latency-sensitive APIs where request p99 matters more
than developer ergonomics. LFF trades framework richness for predictable
performance under load.
```

**Common fail signals (audit guidance):** H1 is a tagline ("Ship faster than light"); description leads with "Features:"; first content block is a screenshot; opening paragraph explains how the code works without saying what it is.
