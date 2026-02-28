# Retrospective Workflow

Reflect on the session, gather observations, and submit feedback.

## Phase 1: Check Prerequisites

Verify `gh` is available:

```bash
gh auth status 2>&1
```

If `gh` is not installed or not authenticated, respond with:

> To submit retrospective feedback, you need the GitHub CLI installed and authenticated:
>
> 1. Install: `brew install gh` (macOS) or see https://cli.github.com
> 2. Authenticate: `gh auth login`
> 3. Try again after setup is complete.

Do NOT proceed until `gh auth status` succeeds.

## Phase 2: Reflect

Summarize what happened in this session, then ask the user three questions
(one at a time, not all at once):

1. **What worked well?** — Which WOS skills or workflows felt smooth?
   What saved you time or helped you think?
2. **What was frustrating?** — Where did WOS get in the way, produce
   poor results, or require workarounds?
3. **What was missing?** — What did you wish WOS could do that it can't?
   Any skills or features you wanted but didn't find?

For each answer, ask one brief follow-up if the response is vague
(e.g., "Can you give a specific example?"). Don't over-interrogate —
if the user gives a clear answer, move on.

If the user provided a focus area in the invocation, tailor the questions
to that area instead of using the generic three.

## Phase 3: Gather Context

Auto-gather (do not ask the user for these):

```bash
# wos version
uv run <plugin-scripts-dir>/get_version.py

# Python version
python3 --version

# Platform
uname -s -r -m
```

## Phase 4: Draft & Preview

Compose a GitHub issue using this template:

```markdown
## Session Retrospective

**Focus:** [focus area if provided, otherwise "General session review"]

### What Worked

[Bullet points from user's response to question 1]

### What Was Frustrating

[Bullet points from user's response to question 2]

### What Was Missing

[Bullet points from user's response to question 3]

### Session Context

[Brief, anonymized summary of what the session involved — e.g.,
"Research workflow on a new topic" or "Auditing and fixing a project".
Do NOT include repo names, file contents, or sensitive details.]

### Environment

- **wos version:** [version from plugin.json]
- **Python:** [python3 --version output]
- **Platform:** [uname output]
```

**Framing rule:** Write from the WOS tool author's perspective. Use
"a WOS user" instead of "I". Replace vault-specific details with
generic descriptions. Strip any repo names, file paths, or personal
information.

Show the draft to the user: "Here's the retrospective feedback I'd
submit. Want to change anything before I file it?"

Wait for explicit approval.

## Phase 5: Submit

Only after explicit approval:

```bash
gh issue create \
  --repo bcbeidel/wos \
  --title "Retrospective: [BRIEF_SUMMARY]" \
  --body "BODY_HERE" \
  --label "feedback"
```

On success, show the issue URL. On failure, show the error and suggest
checking `gh auth status`.
