---
name: check-rule
description: Check a Claude Code rule library under `.claude/rules/` for path-glob validity, vague phrasing, contradictions, and oversize files. Use when the user wants to "audit rules", "check rule quality", "find conflicting rules", "review my rules", or "are my rules well-formed".
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
argument-hint: "[path to rule file or directory — scans .claude/rules/ if omitted]"
user-invocable: true
references:
  - ../../_shared/references/rule-best-practices.md
  - references/check-cross-rule-conflict.md
  - references/check-example-realism.md
  - references/check-framing.md
  - references/check-judgment-not-linter.md
  - references/check-scope-tightness.md
  - references/check-single-concern.md
  - references/check-specificity.md
  - references/check-staleness.md
  - references/check-why-adequacy.md
license: MIT
---

# /build:check-rule

Evaluate the quality of an existing Claude Code rule library. Three tiers, in order: deterministic format checks (no LLM), per-rule semantic checks (eight always-on dimensions in a single locked-rubric call), then cross-rule conflict detection.

This skill follows the [check-skill pattern](../../_shared/references/check-skill-pattern.md). Tier-1 detection is in 5 scripts emitting JSON envelopes via `_common.py` (9 rule_ids total). Tier-2 has 8 judgment dimensions read inline by the primary agent. Tier-3 is the cross-rule-conflict judgment rule fired against rule pairs that could co-fire.

The audit rubric mirrors the authoring principles in [rule-best-practices.md](../../_shared/references/rule-best-practices.md). Each Tier-2 dimension cites its source principle. When the principles doc changes, the dimensions follow.

## Workflow

### 1. Discover Rules

Rule files live under `.claude/rules/**/*.md` (recursive). When `$ARGUMENTS` resolves to a path, scope discovery to that file or directory. When `$ARGUMENTS` is empty, scan `.claude/rules/` and (if the user maintains personal rules) `~/.claude/rules/`.

Reading `~/.claude/rules/` is intentional — a rule library spans both project rules and personal rules, and an audit that ignores the personal half misses real findings. Discovery and the audit phases (Tiers 1-3) are read-only; only the opt-in repair loop in Step 6 writes, and only after user confirmation per change. The home-directory scope is narrowed by passing an explicit path argument — e.g. `/build:check-rule .claude/rules/` to audit project rules only.

Report: "Found N rules. Auditing..."

### 2. Tier-1 Deterministic Format Checks

Invoke 5 detection scripts (`emit_shape_hints.sh` is an informational helper, not a check):

```bash
SCRIPTS="${SKILL_DIR}/scripts"
TARGETS="$ARGUMENTS"   # default .claude/rules/

python3 "$SCRIPTS/scan_secrets.py"     $TARGETS   # 1 rule:  secret (FAIL)
python3 "$SCRIPTS/check_structure.py"  $TARGETS   # 3 rules: location, extension, frontmatter-shape
python3 "$SCRIPTS/check_paths_glob.py" $TARGETS   # 1 rule:  paths-glob (FAIL)
bash    "$SCRIPTS/check_size.sh"       $TARGETS   # 1 rule:  size (warn >200; fail >500)
python3 "$SCRIPTS/check_prose.py"      $TARGETS   # 3 rules: hedge, prohibition-opener, synthetic-placeholder
bash    "$SCRIPTS/emit_shape_hints.sh" $TARGETS   # informational helper (not a check)
```

Each script emits a JSON array of envelopes: `{rule_id, overall_status, findings[]}`, with each finding carrying `{status, location, reasoning, recommended_changes}`. `recommended_changes` is canonical — copy through verbatim.

**Script-to-rules map** (9 Tier-1 rule_ids):

| Script | rule_ids | Severity |
|---|---|---|
| `scan_secrets.py` | `secret` | fail |
| `check_structure.py` | `location` | fail |
| `check_structure.py` | `extension` | fail |
| `check_structure.py` | `frontmatter-shape` | warn |
| `check_paths_glob.py` | `paths-glob` | fail |
| `check_size.sh` | `size` | warn (>200) / fail (>500) |
| `check_prose.py` | `hedge` | warn |
| `check_prose.py` | `prohibition-opener` | warn |
| `check_prose.py` | `synthetic-placeholder` | warn |

**Tier-2 exclusion list.** Any FAIL in `secret`, `location`, `extension`, `paths-glob`, or `size` (>500 line case) excludes the rule from Tier-2 — malformed rules don't reach the LLM step. WARN findings (and `frontmatter-shape`) do **not** exclude.

`emit_shape_hints.sh` collects keyword signals (`compliant`, `non-compliant`, `violation`, `exception`, `failure`, code-block presence) per file and supplies them as **prompt context** to Tier-2 — not as findings. The eight Tier-2 dimensions run on every rule regardless; the hints just inform the evaluator.

### 3. Tier-2 Semantic Dimensions (One LLM Call per Rule)

For each structurally valid rule, evaluate against the **8 judgment rules** at `references/check-*.md`:

| File | Dimension | Severity |
|---|---|---|
| [check-framing.md](references/check-framing.md) | D1 — positive framing over pure prohibition | warn |
| [check-specificity.md](references/check-specificity.md) | D2 — verifiable directives, no anchor-free terms | warn |
| [check-single-concern.md](references/check-single-concern.md) | D3 — one topic per file | warn |
| [check-why-adequacy.md](references/check-why-adequacy.md) | D4 — reasoning included; failure cost + exception for judgment-based rules | warn |
| [check-scope-tightness.md](references/check-scope-tightness.md) | D5 — `paths:` matches content breadth | warn |
| [check-staleness.md](references/check-staleness.md) | D6 — referenced paths/commands/imports still exist | warn |
| [check-judgment-not-linter.md](references/check-judgment-not-linter.md) | D7 — semantic conventions only; no formatter/linter overlap | warn |
| [check-example-realism.md](references/check-example-realism.md) | D8 — domain-specific identifiers, not synthetic placeholders | warn |

#### Evaluator policy

- **Single locked-rubric pass per rule.** Read all 8 rule files first, then evaluate each rule in turn against them. Don't re-decompose into sub-checks (RULERS, Hong et al. 2026 — per-dimension calls cost ~11.5 points of agreement).
- **Default-closed when borderline.** When evidence is ambiguous, return `warn`, not `pass`.
- **Severity floor: WARN.** All 8 Tier-2 dimensions are coaching, not blocking. Escalate to FAIL only for safety concerns Tier-1 missed.
- **One finding per dimension per rule maximum.** If a single rule trips one dimension at multiple locations, surface the highest-signal one with concrete excerpts.

Include the full rule file verbatim in the prompt — never summarize. Include the Tier-1 shape-hints keyword sniff as context. Dimensions that don't apply (e.g., D8 Example Realism on a rule with no examples) return `inapplicable` silently.

### 4. Tier-3 Cross-Rule Conflict Detection

Evaluate against [check-cross-rule-conflict.md](references/check-cross-rule-conflict.md). For each rule pair that could co-fire (both always-on, or `paths:` globs share at least one matching file), present both rule files verbatim and ask whether following one rule's directives violates the other.

This is the **load-bearing** Tier-3 dimension — Anthropic's own warning is the basis: *"if two rules contradict each other, Claude may pick one arbitrarily."* Severity: `fail`.

Tier-3 returns `inapplicable` silently when audit scope holds only a single rule (no pairs to compare).

### 5. Report Findings

Merge findings from all 3 tiers into a unified table:

```
| Tier | rule_id | Location | Status | Reasoning |
|------|---------|----------|--------|-----------|
```

Sort: `fail` before `warn` before `inapplicable`; Tier-1 before Tier-2 before Tier-3 within severity. Each finding's `Recommendation:` line copies through `recommended_changes` verbatim.

Close with: `N rules audited, M findings (X fail, Y warn)` or `N rules audited — no findings`.

### 6. Opt-In Repair Loop

Ask exactly once:

> "Apply fixes? Enter y (all), n (skip), or comma-separated numbers."

For each selected finding, route per the recipe in `recommended_changes`:

- **Direct edit** — frontmatter shape, paths-glob syntax, file location/extension, hedge/prohibition rewording, synthetic-placeholder substitution. Show diff; write on confirmation.
- **Routed to another skill** — substantial rule rewrites → `/build:build-rule` for scaffold-from-scratch.
- **Tier-2/3 judgment** — framing, specificity, single concern, etc. Ask the user; rewrite the section; show diff; write on confirmation.

After each applied fix, re-run the relevant Tier-1 script (or re-judge the Tier-2/3 dimension). Terminate when the user enters `n` or exhausts findings.

## Anti-Pattern Guards

1. **Per-dimension LLM call** — collapse into one locked-rubric call per rule (per-dimension splits degrade agreement by 11.5 points, RULERS).
2. **LLM-evaluating format compliance** — handle frontmatter / glob syntax / location / extension with deterministic Tier-1 scripts; send only structurally valid rules to the LLM.
3. **Ambiguous compliance reported as PASS** — surface as WARN (default-closed) so the user sees the borderline case.
4. **Vague finding text** — cite the specific rule file and the exact phrasing or field that triggered the finding.
5. **Conflict-comparing non-overlapping rules** — gate Tier-3 on co-fire potential (always-on pair, or overlapping `paths:`).
6. **Trigger-gating Tier-2 dimensions** — don't skip dimensions based on whether the rule "opts into" a shape; run all 8 always. Dimensions that don't apply return `inapplicable` silently.
7. **Re-evaluating scripted rules in Tier-2** — scripts are authoritative for the 9 Tier-1 rules; trust the `pass` envelope.
8. **Suppressing the inapplicable envelope** — D8 against a rule with no examples emits `inapplicable`; surface it; do not silently skip.
9. **Embellishing scripts' `recommended_changes`** — each rule's recipe constant is canonical guidance sourced from `rule-best-practices.md`. Copy it through; do not paraphrase.

## Key Instructions

- Run Tier-1 deterministic checks first; gate LLM evaluation on structural validity.
- Include the Tier-1 shape-hints keyword sniff as context in the Tier-2 prompt — it informs the evaluator, not the dimension set (all 8 dimensions always run).
- Present all 8 Tier-2 dimensions as a single locked-rubric call per rule.
- Include the full rule file verbatim in every LLM evaluation.
- Limit conflict comparison to rule pairs that could co-fire.
- Surface borderline evidence as WARN (default-closed).
- Recovery: read-only outside the Repair Loop; edits revertable via `git diff` / `git checkout`.

## Handoff

**Receives:** Path to a `.md` rule file or directory under `.claude/rules/`, or no argument (scans `.claude/rules/`).

**Produces:** A unified findings table merging the 9 Tier-1 envelopes (script JSON), 8 Tier-2 judgment findings per rule, and the Tier-3 cross-rule-conflict findings per rule pair. Each row: tier, rule_id, location, status, reasoning + `recommended_changes` excerpt. Optionally — per user confirmation in the Repair Loop — targeted edits to rule files.

**Chainable to:** `/build:build-rule` (rebuild non-compliant rules from scratch when targeted repair would exceed the rule's scope).
