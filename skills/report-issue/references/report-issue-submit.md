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

### Framing Rule

Write issues from the WOS tool author's perspective, not the consumer's.
The reader is the WOS maintainer who needs to understand, reproduce, and
fix the issue.

- Replace vault-specific details with generic examples
- Use "a WOS user" or "a project with N context files" instead of "I"
  or "my vault"
- Describe solutions in terms of WOS's internal architecture (scripts,
  validators, skills)
- If the user provides consumer-specific context, extract the generic
  pattern

**Consumer-specific details to catch and generalize:**
- References to specific vault files or directory structures
- Exact file counts or token numbers from a specific deployment
- "During my recent X" narratives tied to a particular workflow
- Vault-specific template names, area names, or project structures

## Phase 5: Preview and Quality Check

Before showing the preview, evaluate the draft against the quality
checklist below. Show results alongside the draft.

### Quality Checklist

Apply the checks relevant to the issue type:

| Check | Applies to | Pass criteria |
|---|---|---|
| Generic framing | All types | No vault-specific paths, file counts, or "my vault" language |
| Self-contained | All types | Understandable without reading prior conversations or external context |
| Has evaluation criteria | Feature requests | Test fixtures table and pass criteria table are present and filled in |
| Has MRE | Bug reports | Minimum reproducible example section is present with fixture + command + error |
| Has before/after examples | Features changing existing behavior | Current vs proposed output shown |
| Has scope/non-goals | Feature requests | Scope and Non-Goals subsections are present and filled in |

### Preview Format

Show the user the complete issue draft with quality check results:

```
──────────────────────────────────────
Title: [issue title]
Labels: [labels]
Repo: bcbeidel/wos
──────────────────────────────────────
[full issue body]
──────────────────────────────────────

Quality Checks:
  ✓ Generic framing
  ✓ Self-contained
  ⚠ [any checks that didn't fully pass — explain briefly]
```

All checks are **advisory**. The user can approve and submit even if
some checks show warnings.

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
