# Report-Issue Submit Workflow

Gather context, draft a GitHub issue, preview, and submit.

## Phase 1: Check Prerequisites

Before gathering details, verify `gh` is available:

```bash
gh auth status 2>&1
```

If `gh` is not installed or not authenticated, respond with:

> To file issues, you need the GitHub CLI installed and authenticated:
>
> 1. Install: `brew install gh` (macOS) or see https://cli.github.com
> 2. Authenticate: `gh auth login`
> 3. Try again after setup is complete.

Do NOT proceed until `gh auth status` succeeds.

## Phase 2: Gather Context

Ask the user what happened. Collect:

- **What happened** — the problem or idea
- **What was expected** (for bugs) — what should have happened
- **Steps to reproduce** (for bugs) — how to trigger it
- **Error messages** — any error output
- **Relevant files** — paths or document types involved

Auto-gather (do not ask the user for these):

```bash
# wos version
python3 -c "import json; print(json.load(open('.claude-plugin/plugin.json'))['version'])"

# Python version
python3 --version

# Platform
uname -s -r -m
```

## Phase 3: Classify Issue Type

Based on the user's description, classify as one of:

| Type | Label | Signal words |
|------|-------|-------------|
| Bug report | `bug` | "broken", "error", "crash", "doesn't work", "wrong" |
| Feature request | `enhancement` | "would be nice", "add", "support", "could we" |
| General feedback | `feedback` | "suggestion", "thought", "observation" |

If ambiguous, ask: "Should I file this as a **bug report** or a
**feature request**?"

## Phase 4: Draft the Issue

Use the appropriate template from `references/issue-templates.md`.

Fill in:
- **Title**: Concise summary (under 70 characters)
- **Body**: From the template, with gathered context
- **Labels**: From classification above

## Phase 5: Preview

Show the user the complete issue draft:

```
──────────────────────────────────────
Title: [issue title]
Labels: [labels]
Repo: bcbeidel/wos
──────────────────────────────────────
[full issue body]
──────────────────────────────────────
```

Ask: "Does this look right? I can edit any part before submitting."

Wait for explicit approval. If the user requests changes, apply them
and preview again.

## Phase 6: Submit

Only after explicit approval:

```bash
gh issue create \
  --repo bcbeidel/wos \
  --title "TITLE_HERE" \
  --body "BODY_HERE" \
  --label "LABEL_HERE"
```

On success, show the issue URL to the user.

On failure, show the error and suggest:
- Check `gh auth status`
- Try again with `gh issue create` manually
