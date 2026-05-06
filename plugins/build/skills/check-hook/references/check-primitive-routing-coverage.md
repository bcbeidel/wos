---
name: Primitive Routing Coverage
description: CLAUDE.md instructions that exhibit hook conversion signals (recurring violation, shell-expressible, lifecycle-bound) should be promoted to PreToolUse hooks rather than left as advisories.
paths:
  - "**/CLAUDE.md"
---

When a CLAUDE.md instruction matches all three hook-conversion signals, surface the rule as a `warn` finding recommending promotion to a `PreToolUse` hook — never auto-convert.

**Why:** advisory rules in CLAUDE.md depend on the agent reading and following them. Under time pressure, mid-multi-step task, or in a long context window where the rule has scrolled out, advisories are routinely violated. A hook intercepts at the lifecycle moment the rule is meant to enforce — `PreToolUse` blocks deterministically before the action runs. The conversion is not always desirable (some rules are intentionally advisory; some are too contextual to express mechanically), so the audit flags candidates for user judgment rather than rewriting CLAUDE.md silently. Severity: `warn`.

**How to apply:** scan `CLAUDE.md` (if present at the project root) for instructions that match **all three** signals. For each match, surface a finding citing the CLAUDE.md line, naming the lifecycle event the hook would target, and listing what the matcher and exit-code shape would look like. Recommend the conversion; do not edit the file.

```markdown
# Audit output (illustrative — not the rule itself):

CLAUDE.md line 47:
  > Never commit files containing `TODO(ME)` markers.

Conversion signals matched:
  - Recurring violation: yes (commits flagged in last 30 days)
  - Shell-expressible: yes (grep for the marker; exit non-zero)
  - Lifecycle-bound: yes (PreToolUse on `Bash` matching `git commit`)

Recommendation:
  Convert to PreToolUse Bash hook at .claude/hooks/block-todo-me.sh.
  Run `/build:build-hook` to scaffold; SKILL.md describes the shape.
```

**Common fail signals (audit guidance):**

- CLAUDE.md instruction phrased as "Claude should never X" / "Always do Y before Z" where X or Y is a specific shell-expressible pattern (file content, command argument, path).
- Instruction recurring across multiple sessions in the team's history (the team has hit this rule repeatedly in commits / PRs / incident notes).
- Instruction tied to a Claude Code lifecycle moment (before edit, before commit, before push, on session start).
- The advisory has a documented near-miss or incident in the brief, the changelog, or the team's runbook — strong evidence that the deterministic block is worth the friction.

**Exception:** rules that are deliberately advisory because the right action depends on context (e.g., "prefer X but exceptions exist when Y") should not be promoted to hooks — surface the rule, note the contextual nature, and recommend keeping it advisory. The audit's role is to identify mechanical-block candidates, not to flatten judgment into enforcement.
