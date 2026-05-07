---
name: check-subagent
description: >
  Audits Claude Code custom subagent definitions against deterministic
  Tier-1 checks (location, frontmatter shape, naming, `tools`
  hygiene, prompt size, body structure, secret patterns) and seven
  judgment dimensions (scope discipline, routing-description quality,
  tool proportionality, output contract, voice & framing, failure
  behavior, injection surface). Use when the user wants to "audit a
  subagent", "review agent permissions", or "validate a subagent
  definition". Not for skills (route to `/build:check-skill`), hooks
  (route to `/build:check-hook`), or rules (route to
  `/build:check-rule`).
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
argument-hint: "[path]"
user-invocable: true
references:
  - ../../_shared/references/subagent-best-practices.md
  - references/check-description-as-router-prompt.md
  - references/check-failure-behavior.md
  - references/check-injection-surface.md
  - references/check-output-contract.md
  - references/check-scope-discipline.md
  - references/check-tool-proportionality.md
  - references/check-voice-and-framing.md
license: MIT
---

# Check Subagent

Audit Claude Code custom subagent definitions for structural soundness, tool-scope hygiene, routing-contract clarity, and safety posture. The rubric — what makes a subagent load-bearing, the file anatomy, the patterns that work — lives in [subagent-best-practices.md](../../_shared/references/subagent-best-practices.md).

This skill follows the [check-skill pattern](../../_shared/references/check-skill-pattern.md). Tier-1 detection is in 8 scripts emitting JSON envelopes via `_common.py` (20 rule_ids total). Tier-2 has 7 judgment dimensions read inline by the primary agent. Tier-3 is `description-collision` (mechanically detected by `check_collision.sh`).

## When to use

Also fires when the user phrases the request as:

- "check my agents"
- "are my subagents well-formed"

## Workflow

### 1. Scope

Read `$ARGUMENTS`:

- **Single path to a subagent `.md` file** — audit that file.
- **Directory path** — walk top-level for subagent definitions (files at `.claude/agents/`, `~/.claude/agents/`, or `plugins/<plugin>/agents/`).
- **Empty** — refuse and explain.

Confirm the scope aloud before proceeding.

### 2. Tier-1 Deterministic Checks

Invoke 8 detection scripts:

```bash
SCRIPTS="${SKILL_DIR}/scripts"
TARGETS="$ARGUMENTS"

bash "$SCRIPTS/check_secrets.sh"     $TARGETS   # 1 rule:  secret (FAIL)
bash "$SCRIPTS/check_location.sh"    $TARGETS   # 2 rules: location-dir, location-ext (FAIL)
bash "$SCRIPTS/check_frontmatter.sh" $TARGETS   # 6 rules: fm-* + plugin-noop, memory-expansion
bash "$SCRIPTS/check_naming.sh"      $TARGETS   # 3 rules: name-kebab, name-stem-match, generic-filename
bash "$SCRIPTS/check_tools.sh"       $TARGETS   # 4 rules: tools-omitted, tools-wildcard, agent-listed, parallel-write-risk
bash "$SCRIPTS/check_size.sh"        $TARGETS   # 1 rule:  size (warn ≥6000 chars; fail ≥12000)
bash "$SCRIPTS/check_structure.sh"   $TARGETS   # 2 rules: no-headings, scope-absent
bash "$SCRIPTS/check_collision.sh"   $TARGETS   # 1 rule:  description-collision (Tier-3 mechanically detected)
```

Each script emits a JSON array of envelopes: `{rule_id, overall_status, findings[]}`. `recommended_changes` is canonical — copy through verbatim.

**Script-to-rules map** (20 Tier-1 rule_ids):

| Script | rule_ids | Severity |
|---|---|---|
| `check_secrets.sh` | `secret` | fail |
| `check_location.sh` | `location-dir` | fail |
| `check_location.sh` | `location-ext` | fail |
| `check_frontmatter.sh` | `fm-delimiter` | fail |
| `check_frontmatter.sh` | `fm-name` | fail |
| `check_frontmatter.sh` | `fm-description` | fail |
| `check_frontmatter.sh` | `fm-description-length` | fail |
| `check_frontmatter.sh` | `plugin-noop` | warn |
| `check_frontmatter.sh` | `memory-expansion` | warn |
| `check_naming.sh` | `name-kebab` | warn |
| `check_naming.sh` | `name-stem-match` | fail |
| `check_naming.sh` | `generic-filename` | warn |
| `check_tools.sh` | `tools-omitted` | warn |
| `check_tools.sh` | `tools-wildcard` | fail |
| `check_tools.sh` | `agent-listed` | warn |
| `check_tools.sh` | `parallel-write-risk` | warn |
| `check_size.sh` | `size` | warn (≥6000) / fail (≥12000) |
| `check_structure.sh` | `no-headings` | warn |
| `check_structure.sh` | `scope-absent` | warn |
| `check_collision.sh` | `description-collision` | warn (Tier-3) |

**Tier-2 exclusion list.** Any FAIL in `secret`, `location-dir`, `location-ext`, `fm-delimiter`, `fm-name`, `fm-description`, `fm-description-length`, `name-stem-match`, `tools-wildcard`, or `size` (>12000 char case) excludes the subagent from Tier-2 — malformed definitions don't reach the LLM step.

### 3. Tier-2 Semantic Dimensions (One LLM Call per Subagent)

For each structurally valid subagent, evaluate against the **7 judgment rules** at `references/check-*.md`:

| File | Dimension | Severity |
|---|---|---|
| [check-scope-discipline.md](references/check-scope-discipline.md) | D1 — clear in-scope / out-of-scope; out-of-scope refusals | warn |
| [check-description-as-router-prompt.md](references/check-description-as-router-prompt.md) | D2 — description leads with caller's situation, not subagent's function | warn |
| [check-tool-proportionality.md](references/check-tool-proportionality.md) | D3 — tools allowlist is the minimum needed | warn |
| [check-output-contract.md](references/check-output-contract.md) | D4 — output shape and termination explicit | warn |
| [check-voice-and-framing.md](references/check-voice-and-framing.md) | D5 — direct, definite voice; no marketing or hedging | warn |
| [check-failure-behavior.md](references/check-failure-behavior.md) | D6 — named failure modes with explicit recovery | warn |
| [check-injection-surface.md](references/check-injection-surface.md) | D7 — payload-derived input not exec'd or eval'd unsafely | warn |

**Evaluator policy:** see [check-skill-pattern.md §Evaluator policy](../../_shared/references/check-skill-pattern.md#evaluator-policy). Read all 7 rule files first, then evaluate each subagent in one LLM call.

Include the full subagent definition verbatim — never summarize. Dimensions that don't apply (e.g., D7 Injection Surface on a subagent that never reads input) return `inapplicable` silently.

### 4. Tier-3 Cross-Entity Collision

`description-collision` is mechanically detected at Tier-1 by `check_collision.sh` (pairwise token-set Jaccard ≥0.6). Returns `pass` (no collisions) or `warn` (collisions surfaced) per pair. Single-subagent scope returns `inapplicable`.

### 5. Report

Merge findings from all 3 tiers into a unified table:

```
| Tier | rule_id | Location | Status | Reasoning |
|------|---------|----------|--------|-----------|
```

Sort: `fail` before `warn` before `inapplicable`; Tier-1 before Tier-2 before Tier-3 within severity. Each finding's `Recommendation:` line copies through `recommended_changes` verbatim.

Close with: `N subagents audited, M findings (X fail, Y warn)` or `N subagents audited — no findings`.

### 6. Opt-In Repair Loop

Ask exactly once:

> "Apply fixes? Enter y (all), n (skip), or comma-separated numbers."

For each selected finding:

- **Direct edit** — frontmatter shape, name slug, kebab-case rename, tools allowlist correction. Show diff; write on confirmation.
- **Routed to another skill** — substantial rewrites → `/build:build-subagent`.
- **Tier-2/3 judgment** — scope discipline, description, tool proportionality, etc. Ask the user; rewrite the section; show diff; write on confirmation.

After each applied fix, re-run the relevant Tier-1 script (or re-judge the Tier-2/3 dimension). Terminate when the user enters `n` or exhausts findings.

## Anti-Pattern Guards

1. **Per-dimension LLM call.** Collapse into one locked-rubric call per subagent.
2. **LLM-evaluating format compliance.** Frontmatter shape, slug syntax, body length — handle deterministically in Tier-1.
3. **Ambiguous compliance reported as PASS.** Surface as WARN (default-closed).
4. **Vague finding text.** Cite the specific subagent file and exact phrasing.
5. **Bulk-applying fixes.** Per-finding confirmation required.
6. **Re-evaluating scripted rules in Tier-2.** Scripts are authoritative for the 20 Tier-1 rules; trust the `pass` envelope.
7. **Suppressing the inapplicable envelope.** When a dimension does not apply (e.g., D7 against a subagent that never reads input), surface `inapplicable`.
8. **Embellishing scripts' `recommended_changes`.** Each rule's recipe constant is canonical guidance sourced from `subagent-best-practices.md`. Copy through.

## Key Instructions

- Run Tier-1 deterministic checks first; gate LLM evaluation on structural validity.
- Present all 7 Tier-2 dimensions as a single locked-rubric call per subagent.
- Include the full subagent definition verbatim in every LLM evaluation.
- Description-collision is Tier-3 but mechanically detected by `check_collision.sh` — no LLM call needed.
- Recovery: read-only outside the Repair Loop; edits revertable via `git diff` / `git checkout`.

## Handoff

**Chainable to:** `/build:build-subagent` (rebuild non-compliant subagents); `/build:check-skill-pair subagent` (audit pair-level integrity for build/check pairs).
