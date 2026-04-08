---
name: Hook Setup Guide
description: How to wire check-rules into Claude Code hooks for automatic enforcement
---

# Hook Setup Guide

Hooks enable automatic rule enforcement — Claude evaluates rules against
changed files without the user manually invoking `/wos:check-rules`.

Start with on-demand checks. Graduate to hooks when your rules are
validated and you trust the signal.

## When to Use Hooks

Hooks are appropriate when:
- Your rules have been tested and produce reliable results
- False positive rate is low (rules are well-scoped with good examples)
- You want enforcement on every commit, not just when you remember

Hooks are NOT appropriate when:
- Rules are new and untested
- You're still iterating on rule wording or scope
- The rule set is large (many rule-file pairs = latency)

## Configuration

Add to your project's `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "command": "echo 'check-rules: run /wos:check-rules on changed files before committing'",
        "condition": "git commit"
      }
    ]
  }
}
```

This prompts Claude to run rule checks before git commits. The exact
hook configuration depends on your Claude Code version and workflow.

## Recommendations

- **Hook only `fail`-severity rules.** Warning-level rules are advisory
  and should not block commits. Reserve hooks for hard constraints.
- **Keep the active rule set small.** Each rule-file pair is an LLM
  evaluation. 5 rules on a 10-file commit = 50 evaluations (before
  scope filtering). Well-scoped rules reduce this significantly.
- **Test rules on-demand first.** Run `/wos:check-rules` manually on
  several changesets before enabling automatic enforcement. Verify the
  rules produce the verdicts you expect.
- **Start with pre-commit, not file-save.** File-save hooks fire
  frequently and add latency to the editing loop. Pre-commit runs
  once per commit cycle.

## Troubleshooting

**Too slow:** Narrow rule scopes. A rule scoped to `models/staging/**`
fires on fewer files than `**/*.sql`.

**Too noisy:** Review failing rules. If a rule produces false positives,
refine the examples or narrow the scope before disabling the hook.

**Unexpected passes:** Check that the scope glob actually matches the
files you expect. Test with `/wos:check-rules <specific-file>`.
