---
name: retrospective
description: >
  Use when the user wants to "run a retrospective", "review this session",
  "give feedback on WOS", "how did WOS do", "session review", or at the
  end of a session to capture what worked, what didn't, and improvement
  ideas for the WOS tool.
argument-hint: "[optional: specific focus area]"
user-invocable: true
references:
  - references/retrospective-workflow.md
---

# Retrospective Skill

Review the current session's use of WOS and submit structured feedback
to the WOS source repository via GitHub Issues.

## Purpose

Help the WOS maintainer understand how the tool is used in practice —
what works, what's painful, and what's missing. Feedback comes directly
from real sessions where the tool was exercised.

## Workflow

Follow the steps in `references/retrospective-workflow.md`.

## Key Rules

- **Session-grounded.** Base observations on what actually happened in
  this session, not hypothetical scenarios.
- **User-driven.** The user decides what to include. Ask questions to
  prompt reflection, but don't invent observations.
- **Never submit without approval.** Show the full draft and get explicit
  confirmation before filing.
- **Target repo is hardcoded:** `bcbeidel/wos`
- **One issue per retrospective.** Don't split into multiple issues.
