---
name: Static Analysis
description: Hook scripts are covered by ShellCheck and shfmt, with false positives suppressed inline rather than wholesale.
paths:
  - "**/.claude/hooks/**/*.sh"
  - "**/.claude/hooks/**/*.bash"
  - "**/.claude/hooks/**/*.py"
---

Run ShellCheck and `shfmt -i 2` on every hook shell script via CI or pre-commit, and suppress false positives inline with the rule number — never disable wholesale.

**Why:** Static analysis catches quoting, deprecated syntax, and command misuse — bugs dynamic testing misses because the hook only fires on rare matcher hits. A hook that worked on the author's machine breaks on a collaborator's because of an unquoted expansion ShellCheck would have flagged. `# shellcheck disable` without a rule number disables the entire file's checking — the next bug rides through with the original. Severity: `warn`.

**How to apply:** add ShellCheck + `shfmt` to CI or pre-commit (the toolkit's `.pre-commit-config.yaml` is a starting point). Suppress real false positives inline: `# shellcheck disable=SC2034` (with the rule number, on the line above the offending statement) or via `.shellcheckrc`. Common hook-script false positives: SC2034 (jq-assigned vars used later), SC2016 (intentional single-quoted JSON inside `jq` args).

```bash
# Inline suppression (correct shape — names the rule)
# shellcheck disable=SC2034
JQ_OUTPUT=$(echo "$INPUT" | jq -r '.tool_input.command')

# .shellcheckrc — repo-level suppression with rationale
disable=SC2016  # intentional single-quoted JSON in jq calls
```

**Common fail signals (audit guidance):**
- `# shellcheck disable` with no rule number — disables everything below.
- No ShellCheck step in `.github/workflows/` or `.pre-commit-config.yaml` covering `.claude/hooks/**/*.sh`.
- No `shfmt` step alongside ShellCheck — formatting drift across contributors.
- ShellCheck pinned to a very old version (< 0.9) — recent rules absent.
- Comments saying "shellcheck reports false positive" with no actual `disable=` directive.
