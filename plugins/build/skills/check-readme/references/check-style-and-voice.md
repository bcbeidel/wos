---
name: Style and Voice
description: Instructions must read as imperative second-person commands; jargon must be defined on first use; headings must be plain ASCII without emoji; prose must be direct without hedging adverbs.
paths:
  - "**/README.md"
  - "**/Readme.md"
---

Write instructions in imperative mood and second person ("Run `npm install`"), define jargon on first use, keep headings ASCII-clean, and strip hedging adverbs ("simply", "just").

**Why:** Imperative + second person is the clearest instruction form; hedging reads as uncertainty and trains the reader to question every step. "You might want to consider running `npm install`" is longer, weaker, and ambiguous compared to "Run `npm install`". Emoji in headings (`## 🚀 Getting Started`) break grep, anchor slug generation, and screen readers. "Just" and "simply" insult readers who do not yet know what is being skipped past.
**How to apply:** Verify instructions are in imperative mood and second person. Verify jargon is defined on first appearance. Verify headings are plain text with no emoji. Verify language is direct — no "simply", "just", "obviously", or implicit assumption of expertise. If instructions use indicative or passive voice, jargon goes undefined, or headings carry emoji, convert to imperative ("Run X", not "You should run X"), define jargon on first use, and remove heading emoji.

```markdown
## Getting Started
Run `npm install` to fetch dependencies.
```

**Common fail signals (audit guidance):** "You might want to consider running `npm install`"; "## 🚀 Getting Started"; "Just run the bootstrap"; prose that assumes the reader already understands the domain.
