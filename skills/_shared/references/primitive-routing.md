---
name: Primitive Routing Guide
description: Decision framework for choosing the right Claude Code primitive — rules, skills, hooks, subagents, CLAUDE.md, or permissions.deny. Referenced by all build-* skills as a shared routing gate.
---

# Primitive Routing Guide

Wrong primitive = reliability failure. The six Claude Code primitives are largely capability-equivalent for expressing many constraints. The failure is in the reliability guarantee each provides, not in what it can express.

## The Two Reliability Tiers

**Deterministic tier** — fires regardless of LLM judgment:
- **Hooks** — lifecycle-event triggered, no LLM decision-making
- **User-invoked skills** — fires when user explicitly types `/skill-name`
- **`permissions.deny`** — unconditional firewall, no runtime logic

**Probabilistic tier** — Claude decides whether and when to apply:
- **CLAUDE.md** — always-on context, advisory; Claude judges relevance per-turn
- **Model-invoked skills** — Claude matches description to task; may skip
- **Subagents** — Claude decides when to fork; isolated context window
- **Rules** — LLM evaluates file content for compliance; judgment required

**Core principle:** Use the deterministic tier for enforcement. Use the probabilistic tier for guidance and procedures where Claude's judgment adds value.

---

## Decision Matrix

| Primitive | Right when | Wrong when | Suggest instead |
|-----------|-----------|------------|-----------------|
| **Rule** | Enforcement requires LLM judgment on static file content; convention is too nuanced for grep or AST linter | Check is shell-expressible; must fire at a lifecycle event; it's procedural workflow guidance | Hook (lifecycle), linter (mechanical), Skill (procedural) |
| **Hook** | Must fire at a specific lifecycle event regardless of LLM judgment; enforcement is shell-expressible | Goal is advisory preference; block is unconditional with no exceptions ever | CLAUDE.md (advisory), Skill (procedural), permissions.deny (unconditional) |
| **Skill** | Multi-step procedural workflow invoked on demand; repeatable procedure with judgment steps | Must always fire at an event; needs context isolation; is advisory always-on content | Hook (always-fire), CLAUDE.md (always-on advisory), Subagent (isolated context) |
| **Subagent** | Work is genuinely isolated; different tool permissions required; intermediate work would clutter main context | Sequential dependent work where step N+1 needs full step N output; task fits naturally in main conversation | Skill (same-context procedure) |
| **CLAUDE.md** | Architectural context; implicit knowledge; conventions Claude should weigh contextually | Behavioral rule that must always fire; file exceeds ~150–200 lines (instruction density degrades uniformly) | Hook (always-enforce), Skill (demand-loaded procedure) |
| **permissions.deny** | Unconditional permanent block; no conditions, no exceptions, no logic | Block needs conditional logic; behavior is sometimes legitimate | Hook (conditional block) |

---

## Routing Tests

### Two questions that route most goals

1. **Must this fire at a specific lifecycle event (before/after a tool call, session start/stop) regardless of LLM judgment?** → Hook
2. **Should Claude decide whether this applies to the current task?** → Skill or CLAUDE.md

If neither resolves it:
- Is the target **static file content evaluated for semantic compliance**? → Rule
- Does the task need **context isolation or different tool permissions**? → Subagent
- Is this **advisory context Claude should always carry**? → CLAUDE.md
- Is this **unconditional with no exceptions, ever**? → `permissions.deny`

### Rule routing test

Use a rule when ALL hold:
- The check requires LLM judgment to evaluate (meaning, intent, architecture — not grep)
- The target is static file content that exists independently of any workflow step
- The convention is too nuanced for a grep or AST-level linter

Do NOT use a rule when:
- The check is shell-expressible → use a hook or linter
- Enforcement must fire at a lifecycle event → use a hook
- The convention is procedural guidance (multi-step workflow) → use a skill or CLAUDE.md

### Hook routing test

Use a hook when ALL hold:
- There is a specific lifecycle event (PreToolUse, PostToolUse, SessionStart…) that triggers it
- The enforcement must fire regardless of LLM judgment
- The check is expressible as a shell script (or HTTP/LLM prompt for complex cases)

Do NOT use a hook when:
- The goal is advisory ("prefer X") → CLAUDE.md or skill
- The block is unconditional with zero legitimate exceptions → `permissions.deny`

### Subagent routing test

A subagent is justified when at least one holds:
- **Parallelism or scope** — the task is genuinely isolated and the full context fork is justified by workstream size
- **Permission isolation** — the task requires tool access the parent agent should not hold
- **Context pressure** — intermediate work (search results, large file reads) would degrade the parent's reasoning quality

If none hold → recommend a skill instead.

---

## Wrong-Primitive Failure Modes

| Primitive | Failure pattern | Signal |
|-----------|----------------|--------|
| CLAUDE.md for enforcement | Rule followed most of the time; violated under context pressure or in long sessions | "Claude keeps violating this even though it's in CLAUDE.md" |
| Skills for always-on context | Behavior changes after auto-compaction | "This worked at session start but stopped working" |
| Hooks for advisory guidance | False positives generate bypass culture; users run with `--no-verify` | "Users are bypassing the hook" |
| Subagents for sequential dependent work | Latency grows; isolation provides no benefit | "The subagent approach is slow and hard to chain" |
| CLAUDE.md bloat >150–200 lines | Compliance degrades silently for all rules equally | "Rules that used to work are getting inconsistent" |

**Diagnostic:** Paste the failing rule as the first message (outside CLAUDE.md). If Claude follows it there but not in CLAUDE.md → primitive problem, change the primitive. If Claude still doesn't follow it → rule quality problem, rewrite the rule.
