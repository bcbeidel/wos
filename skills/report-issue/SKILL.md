---
name: report-issue
description: >
  This skill should be used when the user wants to "report a bug",
  "submit feedback", "request a feature", "file an issue",
  "something is broken", "I found a problem", "this doesn't work",
  "suggest an improvement", or any request to report issues or
  feedback about the wos plugin itself.
disable-model-invocation: true
argument-hint: "[describe the issue or feedback]"
---

# Report-Issue Skill

Submit bug reports, feature requests, and feedback to the wos
source repository via GitHub Issues.

## Workflow

This is a linear workflow — no routing needed. All requests follow
the same gather → classify → draft → preview → submit pipeline.

Follow the steps in `references/report-issue-submit.md`.

## Key Rules

- **Always preview before submitting.** Show the formatted issue draft
  and get explicit approval before running `gh issue create`.
- **Check `gh` first.** Verify the CLI is installed and authenticated
  before gathering details. If missing, show setup instructions.
- **Target repo is hardcoded:** `bcbeidel/wos`
- **Include context automatically:** wos version from plugin.json,
  Python version, platform info.
- **Never submit without approval.** The user must explicitly confirm.
