---
name: Check-Skill Pattern
description: Canonical structure and contracts for `check-*` skills under the single-artifact-per-rule discipline. Every rule lives as exactly one artifact — a script (when ≥70% mechanically detectable) or a `references/check-*.md` file (judgment-driven), never both. Scripts emit JSON envelopes with embedded `recommended_changes` recipes; judgment rules are read inline by the primary agent during Tier-2. Referenced by all `check-*` skills and by `build-skill` / `check-skill` when scaffolding or auditing them. Pioneered by `check-bash-script` (Stage-2 phase 1.5, 2026-05); sweep #408 applies this pattern to the remaining 13 `check-*` skills.
---

# Check-Skill Pattern

## What a Good `check-*` Skill Does

A `check-*` skill audits one artifact (or a directory of artifacts) of a single primitive type — a bash script, a Python script, a Makefile, a GitHub workflow, a hook, a rule, a skill, etc. It runs deterministic detection in **Tier-1** (scripts emit JSON envelopes), reads judgment rubrics in **Tier-2** (the primary agent evaluates the artifact against `references/check-*.md` files), surfaces structural duplication in **Tier-3** (when the scope holds multiple artifacts), and offers an opt-in repair loop with per-finding confirmation. Read-only by default.

The skill is not an orchestration framework. It does not spawn subagents, dispatch via SDK, or maintain its own state across invocations. It is a workflow recipe: scripts produce structured findings, the primary agent judges what scripts cannot, the user sees a unified report, repairs apply one-at-a-time. This is enough.

## Anatomy

```
plugins/build/skills/check-<primitive>/
├── SKILL.md                              # Single entry point
├── assets/
│   └── output-example.json               # Canonical envelope shape (with `_comment` schema)
├── references/
│   └── check-<rule_id>.md                # ONE FILE PER JUDGMENT-MODE RULE
└── scripts/
    ├── _common.py                        # Shared JSON-emit helpers (verbatim across skills)
    ├── check_<rule_id>.{py,sh}           # ONE PER SCRIPTED RULE (or one emitting an array of rule_ids)
    └── tests/
        ├── __init__.py
        └── test_common.py                # Verbatim across skills
```

The canonical convention doc lives outside the skill at `plugins/build/_shared/references/<primitive>-best-practices.md`. It is shared between the skill's `build-` half and `check-` half (the primitive-pair pattern), and it owns the "Why" for every rule the skill enforces.

## The Single-Artifact-Per-Rule Principle

Every rule has **exactly one** artifact. The choice is determined by mechanical detectability:

- **Script** at `scripts/check_<rule_id>.{py,sh}` — when ≥70% of the rule's violations are detectable by a deterministic check. Owns detection AND recipe. Emits a complete JSON envelope including `recommended_changes`. No corresponding `.md` file.
- **Markdown** at `references/check-<rule_id>.md` — when detection requires judgment (control-flow analysis, intent-naming weakness, design-quality dimensions). Owns the LLM-judged rubric. The primary agent reads it during Tier-2 and produces structured findings inline. No corresponding script.

There is **no overlap**. The orchestrator-free design uses filesystem layout as the discovery mechanism: the rule set is the union of `references/check-*.md` filenames + emitted `rule_id`s from `scripts/check_*.{py,sh}` outputs. If a rule_id appears in both, the discipline is broken — pick one home.

The 70% threshold is a judgment call. Below it, mechanical detection misses too much. Above it, the LLM's marginal value is small enough that judgment-mode invocation is not worth its cost. Borderline cases stay as markdown (conservative).

**Coverage gaps in scripted rules are documented, not hidden.** When a script catches ~70% of a rule's violations, the remaining ~30% is named in the script's docstring and in the skill's PILOT-NOTES. The user accepts the gap as the price of architectural cleanliness — the alternative was a parallel `.md` and the discipline forbids that.

## Detection Script Contract

Every Tier-1 script under `scripts/check_*.{py,sh}` honors the same contract:

- **JSON to stdout.** Emits a single envelope (single-rule script) or a JSON array of envelopes (multi-rule script). Nothing else on stdout. Errors and INFO messages go to stderr.
- **Envelope shape:**
  ```json
  {
    "rule_id": "<rule>",
    "overall_status": "pass" | "warn" | "fail" | "inapplicable",
    "findings": [
      {
        "status": "warn" | "fail",
        "location": {"line": int, "context": str} | null,
        "reasoning": "<≤2 sentences>",
        "recommended_changes": "<canonical repair recipe>"
      }
    ]
  }
  ```
- **`recommended_changes` is REQUIRED** — non-empty string, with concrete repair guidance the user (or a downstream tool) can apply directly. Embedded as a module-level constant in the script (`_RECIPE_<NAME>` in Python; `RECIPE_<NAME>` shell var in Bash). Sourced from the deleted `rule-*.md`'s `## How to apply` section + example. The script is self-sufficient — no LLM enrichment, no orchestrator post-processing.
- **Exit codes:** `0` for pass / warn / inapplicable; `1` for any `overall_status: fail`; `64` for argument errors; `69` for missing required dependencies (not optional tools — those degrade silently to `inapplicable`).
- **Missing-tool degradation.** When a wrapped external tool is absent (`shellcheck`, `shfmt`, `ruff`, `actionlint`, `checkmake`, etc.), emit envelope(s) with `overall_status: inapplicable` and exit `0`. Other Tier-1 scripts continue to run. The `inapplicable` envelope is the user's signal that coverage is reduced — surfacing it is the contract.
- **Bash scripts emitting JSON.** Collect findings inside the script as TSV (`rule_id\tfile\tline\tcontext`); pipe to a `python3 -c "$EMIT_PY"` block at the end that imports `_common` from `$SCRIPT_DIR` via env vars. Do **not** use `python3 <<'PY'` (heredoc-as-stdin trap — Python's `sys.stdin` would point at the heredoc content, not the pipe). Pass the script directory and recipe constants via environment variables (e.g., `CHECK_BASH_SCRIPT_DIR`, `CHECK_BASH_RECIPE_<NAME>`).

## `_common.py` — Shared JSON-Emit Helpers

`scripts/_common.py` is identical across every `check-*` skill. Three exports:

- `emit_json_finding(rule_id, status, location, reasoning, recommended_changes) -> dict`
  Validates `status in {"warn", "fail"}`. Raises `ValueError` if `recommended_changes` is empty or whitespace-only. The required-recipe guarantee is enforced here, not in the orchestrator — the script cannot produce a malformed finding even if the author tries.
- `emit_rule_envelope(rule_id, findings, inapplicable=False) -> dict`
  Derives `overall_status` from the findings list via the severity ladder: any `fail` → `fail`; else any `warn` → `warn`; else `pass`. The `inapplicable` flag overrides the ladder for missing-tool cases.
- `print_envelope(envelope: dict | list[dict])` — `json.dump(..., indent=2)` to stdout, trailing newline.

Companion: `scripts/tests/test_common.py` (13 tests). Copy verbatim.

The helper is small enough to live as a copy in each skill rather than as an installed package; the toolkit's "depend on nothing" design principle prefers stdlib + per-skill duplication over a shared package import path.

## Judgment Rule File Contract

A judgment rule lives at `references/check-<rule_id>.md` and follows the unified Claude-rule shape from `rule-best-practices.md`:

```markdown
---
name: <Human-Readable Title>
description: <One-line imperative statement of the rule>
paths:                            # optional
  - "**/*.<ext>"
---

**Why:** <reason — the failure cost>

**How to apply:** <when/where, mechanics, edge cases>

```<lang>
<optional code example showing the compliant pattern>
```

**Exception:** <optional documented exemptions with rationale>
```

Same shape as the deleted `rule-*.md` files — only the filename prefix changed (`rule-` → `check-`). The `paths:` glob, when present, lets Claude apply the rule ambiently when editing matching files; the audit reads it during Tier-2 regardless.

**Body lead.** The frontmatter `description:` carries the imperative — it is the retrieval anchor, the TOC line, and the rule itself. The body opens with `**Why:**`, not a paraphrase of the description. Restating the description as a body-lead paragraph adds tokens without adding signal: a reader who already saw the description sees the same claim again, and an LLM scoring against the rule double-counts the same content. The deterministic check is `plugins/build/_shared/scripts/check_reference_lead.py`, which flags references whose body lead covers ≥70% of the description's content tokens (rule_id `reference-lead-echo`, severity `warn`).

## `assets/output-example.json`

A concrete single-rule example showing the envelope shape. Includes a `_comment` field documenting the schema and noting that `recommended_changes` is REQUIRED. Update the example's `rule_id` and example finding per skill (e.g., `shebang` for `check-bash-script`, `header-docstring` for `check-python-script`); keep the structure identical.

The asset is what `_common.py`'s docstring points to as the canonical shape. It is also what `build-skill` should reference when scaffolding new `check-*` skills.

## SKILL.md

Three load-bearing sections shape the skill's behavior:

**Frontmatter `references[]`** enumerates **only** the surviving judgment-mode `check-*.md` files plus the shared `<primitive>-best-practices.md`. Not scripts (they're discovered by filesystem walk). Not the asset (it's documentation, not eager-load context). For a skill with N judgment dimensions, `references[]` has N + 1 entries.

**Tier-1 section** invokes scripts with `python3 path/script.py $TARGETS` and `bash path/script.sh $TARGETS`. Documents the JSON envelope shape inline (copy verbatim from this doc). Lists a **Script-to-rules map** table enumerating each script's emitted `rule_id`s — the table is the canonical TOC for the scripted half of the rule set. Names the Tier-2-exclusion-list (which FAILs short-circuit Tier-2; which do not).

**Tier-2 section** says: "the primary agent reads each `references/check-*.md` and judges the artifact directly." No subagent dispatch, no SDK calls, no API key. The dimensions table links each `.md` file. Cites the **Evaluator policy** below by anchor link to this section (`_shared/references/check-skill-pattern.md#evaluator-policy`); does not duplicate the bullets. Verbatim copies are flagged by `evaluator-policy-echo` (Tier-1) and `best-practices-doc-restatement` (Tier-2).

### Evaluator policy

This is the canonical statement. SKILL.md cites; does not restate.

- **Single locked-rubric pass per artifact.** Read all N files first, then evaluate each in turn against the unified rubric. A single locked-rubric pass stabilizes severity.
- **Default-closed when borderline.** When evidence is ambiguous, return `warn`, not `pass`.
- **Severity floor: WARN.** Judgment-mode findings default to WARN — coaching, not blocking. Escalate to FAIL only for safety concerns Tier-1 missed.
- **One finding per dimension maximum.** Surface the highest-signal location with concrete detail. Bulk findings train the user to disregard the audit.

**Tier-3 section** (cross-entity collision) fires only when the audit scope holds multiple artifacts. It is itself a judgment rule — usually `references/check-cross-entity-collision.md` — and follows the same Tier-2 contract. Single-artifact scope returns `inapplicable` silently.

**Anti-Pattern Guards** — at minimum these three are domain-independent and copy verbatim:
- *Re-evaluating scripted rules in Tier-2* — scripts are authoritative for the rules they cover; trust the `pass` envelope.
- *Suppressing the inapplicable envelope* — when a wrapped tool is absent, the `inapplicable` envelope is the user's signal that coverage is reduced.
- *Embellishing scripts' `recommended_changes`* — copy the field through; do not paraphrase or expand.

## Patterns That Work

These are the positive shapes a `check-*` skill takes. Each corresponds to a failure mode either sweep #408 caught in the original lint-format era or this pattern's authoring rubric will catch.

**One artifact per rule.** Detection AND recipe in the same place. No parallel `.md` for a scripted rule.

**JSON over lint format.** Structured envelope; `recommended_changes` mandatory; no regex-parsed text on the consumer side.

**`_common` as the recipe-required gate.** `emit_json_finding` raises on empty `recommended_changes`. The contract is enforced in the helper, not in the orchestrator.

**Filesystem as TOC.** No `_hub.md` listing all rules. The canonical TOC is `ls references/check-*.md` + the SKILL.md script-to-rules map. The filesystem cannot drift from the rule set.

**Inapplicable over silent skip.** Missing tools emit envelopes; do not silently exit 0 with no signal.

**Wrapped-linter scripts include an SC-code-to-rule_id mapping table.** When wrapping `shellcheck` / `ruff` / `actionlint` / similar, embed a module-level `dict[str, tuple[str, str]]` mapping the linter's code → `(rule_id, severity)`. Each rule_id gets a recipe constant; the wrapper emits one envelope per rule_id (empty findings for codes that didn't fire).

**Multi-rule scripts emit a JSON array.** When one script handles multiple `rule_id`s (e.g., `check_structure.py`'s 7 structural rules), it emits a JSON array of envelopes — one per rule_id — regardless of which rules fired. Empty findings → `overall_status: pass`. The orchestrator-free design treats this as the canonical multi-rule shape.

**Per-script docstrings document coverage gaps.** When a scripted rule's heuristic catches ~70% of violations, the docstring names the missing 30%. PILOT-NOTES carries the same gap inventory at the skill level.

## Safety

The same I/O safety posture applies to detection scripts as to any other script under `_shared/references/<primitive>-best-practices.md`:

- **Do not modify the artifact.** A check-* script is read-only by contract. The repair loop is in SKILL.md, not in the script.
- **Do not exec arbitrary user input.** Wrap external linter invocations in `subprocess.run([...], shell=False)`, not `shell=True` with string interpolation.
- **Honor the exit-code contract.** `0` for pass/warn/inapplicable; `1` for any fail; `64` for usage; `69` for missing required deps. The orchestrator-free design treats exit codes as the load-bearing signal.
- **Bound script runtime.** External linter invocations under `subprocess.run(..., timeout=60)`. Skills do not block users on a hung wrapper.

## Migration Workflow (per check-* skill)

For each rule the skill currently enforces, decide whether it belongs as a script or as `references/check-*.md`:

1. **Audit each existing `rule-*.md`** for mechanical detectability.
   - Mechanical regex-detectable check (existing or addable) → script.
   - Pure judgment, control-flow, or design-quality dimension → markdown.
   - Borderline (~70%) → markdown, conservative.

2. **For each rule becoming script-only:** read the `rule-*.md` body. Identify (a) prose already covered in `<primitive>-best-practices.md`; (b) prose needing migration to that doc; (c) prose belonging in the script's recipe constant. Migrate (b) surgically (sentence-level), embed (c) as `_RECIPE_*`.

3. **Rename surviving judgment files** `rule-<id>.md` → `check-<id>.md` via `git mv`.

4. **Delete the scripted-rule `.md` files** via `git rm`.

5. **Add `assets/output-example.json`** — copy the bash-script example, update `rule_id`.

6. **Add `scripts/_common.py` + tests** — verbatim copy.

7. **Refactor each existing detection script** to emit JSON via `_common`. Embed recipe constants. Verify equivalence: same `rule_id`s firing, same severities, line numbers ±2, every finding has non-empty `recommended_changes`.

8. **Update SKILL.md:** shrink `references[]` to N+1 entries; rewrite Tier-1 (JSON shape, script-to-rules map); rewrite Tier-2 (primary-agent reads check-*.md inline + Evaluator policy); update anti-pattern guards.

9. **Sanity-check:** `ls references/check-*.md | wc -l` matches the number of judgment rules; `grep "rule-" references/` returns nothing; running each script produces parseable JSON; `_common.py` tests pass; `ruff check plugins/<skill>/` clean.

10. **Document coverage gaps** in script docstrings + PILOT-NOTES per skill.

11. **One commit per logical unit** for granular revert. ~10–15 commits per skill expected (foundation rename + .md migration; `_common.py` install; one per script refactor; SKILL.md update; verification).

Three skills warrant separate handling because they may not have detection scripts at all (pure-judgment): `check-skill-chain`, `check-skill-pair`, `check-resolver`. For those, the migration is just `git mv rule-*.md check-*.md` and updating SKILL.md `references[]` — no `_common.py`, no script work.

Skills wrapping external linters follow `check_shellcheck.py`'s shape: SC-code-to-rule_id mapping dict + per-rule recipe constants. Examples: `check-makefile` (`checkmake`), `check-python-script` (`ruff`), `check-pre-commit-config` (`pre-commit`), `check-github-workflow` (`actionlint`/`zizmor`).

## Carve-Out: Design+Audit Hybrid Skills

Some `check-*` skills are **hybrids** — part design tool (generates a new artifact from a goal), part audit tool (validates an existing artifact). `check-skill-chain` is the canonical example: Goal mode designs a `*.chain.md` manifest from a workflow description; Manifest mode audits an existing manifest. Only the audit half fits this pattern.

For these skills:

- **The pattern applies to the audit half only.** Decompose its dimensions into `references/check-*.md` files; structure the audit-mode workflow as Tier-1/Tier-2/Tier-3; include the Evaluator policy subsection.
- **The design half stays unchanged.** Keep its existing prose in SKILL.md as a parallel section. Do not force it into the Tier-1/2/3 vocabulary — it is not auditing anything.
- **Cross-plugin tool delegation is allowed at Tier-1.** A skill can delegate structural checks to a script in another plugin (e.g., `check-skill-chain` invokes `plugins/wiki/scripts/lint.py`) when that script is the canonical authority for the artifact type. Do **not** wrap it in a thin local script just to satisfy "scripts/check_*.py owned by this skill" — duplication for compliance is the wrong tradeoff. SKILL.md documents the delegation explicitly so future readers see the reuse, not a missing script.
- **`scripts/_common.py` is optional** when no detection scripts are owned locally. The pattern audit script (`check_skill_pattern.py`) already treats `_common.py` as conditional on `_has_detection_scripts(skill_dir)`.

When a hybrid skill emerges that this carve-out doesn't cover, extend this section rather than weakening the main pattern.

## Review and Decay

A `check-*` skill ages when:

- The wrapped linter changes its output format. Wrappers should pin the linter's `--format` flag to a stable choice (e.g., `--format=json`) and assert on a stable subset of fields.
- The primitive's conventions shift. Convention prose lives in `<primitive>-best-practices.md`; per-rule recipes embed concrete guidance. Both can drift if the canonical doc updates.
- The 70% threshold flips for a rule. A judgment rule with a new lint catching most violations should migrate to a script. A scripted rule whose detection becomes too noisy (precision falls below ~70%) should retreat to judgment-mode markdown.

The audit-against-the-pattern is in `check-skill` (Tier-2 dimension F1: structural compliance with `check-skill-pattern.md`). Run it after editing any `check-*` skill.

---

**Diagnostic when a `check-*` skill misbehaves.** First check the rule set: `ls references/check-*.md` + script-emitted `rule_id` set — do they overlap? Then check the JSON: every script emits parseable JSON; every finding has non-empty `recommended_changes`; missing tools emit `inapplicable` envelopes, not silent exits. Then check the SKILL.md: `references[]` enumerates exactly the survivor `.md` files + the canonical doc; Tier-2 invokes the primary agent inline (no subagent talk); the script-to-rules map matches the actual emitted rule_ids. Most pathologies live in one of those three places.
