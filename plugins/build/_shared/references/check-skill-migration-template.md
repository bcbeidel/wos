---
name: Check-Skill Migration Template
description: Reusable plan template for migrating a `check-<primitive>` skill from the legacy monolithic shape (audit-dimensions.md + repair-playbook.md + lint-format scripts) to the unified single-artifact-per-rule pattern per check-skill-pattern.md. Copy into `.plans/YYYY-MM-DD-check-<primitive>-pattern-migration.plan.md`, fill placeholders (search "{{...}}"), get approval, then execute via `/work:start-work`. Pioneered with check-bash-script (PR #410, 2026-05); applied across the 13 remaining check-* skills under sweep #408.
---

# Check-Skill Migration Template

This file is a **reference**, not an executable plan. To use it:

1. Copy the entire "Plan body" section below into a new file at
   `.plans/YYYY-MM-DD-check-<primitive>-pattern-migration.plan.md`.
2. Search-and-replace `{{primitive}}` (e.g., `python-script`,
   `makefile`, `hook`) and any other `{{...}}` placeholders.
3. Fill in the **Phase 0 Audit** section with the actual rule
   classification matrix (one row per rule the skill currently enforces).
4. Adjust Phase 2's `N`, Phase 3's per-script tasks, and the optional
   Phase 4 new-detection tasks based on the audit's findings.
5. Get user approval, flip `status: draft` → `status: approved`,
   then run `/work:start-work .plans/<...>.plan.md`.

The template is calibrated for skills that sit at the legacy shape
(audit-dimensions.md + repair-playbook.md + scripts emitting lint format).
Pure-judgment skills (`check-skill-chain`, `check-skill-pair`,
`check-hook` — no detection scripts) skip Phases 3, 4, and the
`_common.py` step in Phase 1; the rest still applies.

External-linter wrappers (`check-makefile`, `check-python-script`,
`check-pre-commit-config`, `check-github-workflow`) follow
`check-bash-script`'s `check_shellcheck.py` pattern: a SC-code-to-rule_id
mapping dict + per-rule recipe constants in one wrapper script.

---

## Plan body — copy from here ⤵

```markdown
---
name: check-{{primitive}} Pattern Migration
description: Migrate `check-{{primitive}}` from the legacy monolithic shape (audit-dimensions.md + repair-playbook.md + lint-format scripts) to the unified single-artifact-per-rule pattern per `check-skill-pattern.md`. Scripts emit JSON envelopes with embedded recipes; judgment rules live as `references/check-*.md` files read inline by the primary agent during Tier-2.
type: plan
status: draft
related:
  - plugins/build/_shared/references/check-skill-pattern.md
  - plugins/build/_shared/references/check-skill-migration-template.md
  - plugins/build/_shared/references/{{primitive}}-best-practices.md
  - plugins/build/skills/check-{{primitive}}/SKILL.md
follow_ups:
  - https://github.com/bcbeidel/toolkit/issues/408  # sweep parent
---

# check-{{primitive}} Pattern Migration

## Goal

Bring `plugins/build/skills/check-{{primitive}}/` into compliance with the
unified pattern documented at
[`plugins/build/_shared/references/check-skill-pattern.md`](../../plugins/build/_shared/references/check-skill-pattern.md).
Every rule lives as **either** a Tier-1 detection script under
`scripts/check_*.{py,sh}` (when ≥70% mechanically detectable) **or** a
judgment-mode `references/check-*.md` file (LLM-judged dimensions),
never both. Scripts emit complete JSON envelopes with embedded
`recommended_changes` recipes; the primary agent reads check-*.md files
inline during Tier-2 — no subagent dispatch.

## Scope

### Must have

- **Decompose `references/audit-dimensions.md`** into per-dimension
  judgment files at `references/check-<dimension_id>.md` — one per
  LLM-judged dimension that survives Phase 0's audit.
- **Refactor each existing detection script** under `scripts/` to emit
  JSON envelopes via `_common.emit_rule_envelope`. Single-rule scripts
  emit one envelope; multi-rule scripts emit a JSON array. Every
  finding has a non-empty `recommended_changes` constant.
- **Migrate convention prose** from `audit-dimensions.md` and
  `repair-playbook.md` into either
  `_shared/references/{{primitive}}-best-practices.md` (where not
  already covered) or per-script recipe constants. Audit each before
  deletion; surgical sentence-level migrations only.
- **Delete** `references/audit-dimensions.md`,
  `references/repair-playbook.md`, and any `references/_hub.md` or
  `references/fixtures/` artifact.
- **Add `assets/output-example.json`** — copy from
  `plugins/build/skills/check-bash-script/assets/output-example.json`,
  swap the example `rule_id`.
- **Add `scripts/_common.py` + `scripts/tests/{__init__.py,
  test_common.py}`** — verbatim copy from `check-bash-script`. Required
  iff the skill has detection scripts.
- **Rewrite SKILL.md**:
  - Frontmatter `references[]` enumerates exactly the surviving
    `check-*.md` files plus `../../_shared/references/{{primitive}}-best-practices.md`.
  - Tier-1 section documents the JSON envelope shape; lists a
    Script-to-rules map enumerating each script's emitted `rule_id`s;
    names the Tier-2-exclusion list.
  - Tier-2 section: primary agent reads `references/check-*.md` inline;
    no subagent dispatch language. Includes the **Evaluator policy**
    subsection (RULERS single-call, default-closed, severity floor WARN,
    one finding per dimension).
  - Anti-Pattern Guards include the three pattern-mandatory ones
    (re-evaluating scripted rules in Tier-2; suppressing inapplicable;
    embellishing recommended_changes).
- **`bash plugins/build/_shared/scripts/check_skill_pattern.py
  plugins/build/skills/check-{{primitive}}` exits 0** with all envelopes
  passing.
- **All repo tests pass** (`python3 -m pytest`); **ruff clean** for the
  skill's directory.
- **One commit per logical unit** for granular revert. ~{{commit-count}} commits expected.

### Won't have

- **No new detection logic for unmapped rules** unless explicitly
  promoted via Phase 4 (default: keep them as judgment).
- **No subagent or orchestrator code.** Tier-2 runs inline.
- **No changes to other check-* skills.** Each skill migrates in its
  own PR.
- **No update to `build-skill` scaffolder** (#406 follow-up).
- **No update to `check-skill` audit beyond the structural script** that
  already exists at `_shared/scripts/check_skill_pattern.py`.

## Approach

### Phase 0 — Audit (no code; produces the rule classification matrix)

Read `references/audit-dimensions.md`, `references/repair-playbook.md`,
and every `scripts/check_*.{py,sh}` script. Produce a table classifying
each existing rule:

| Rule (current) | Source | Mechanical detectability | Decision | Notes |
|---|---|---|---|---|
| <fill-in-during-Phase-0> | audit-dim §X / script Y | ≥70% / <70% / unknown | judgment / scripted / promote | <gap notes> |

The decision column is the load-bearing call:
- **judgment** — keep as `references/check-<id>.md`. Used when the rule
  requires control-flow analysis, intent-naming judgment, or
  design-quality evaluation.
- **scripted** — script already exists or will be refactored. Used when
  detection is regex/AST/tool-wrappable at ≥70% recall.
- **promote** — currently judgment; Phase 4 will write a new detection
  script. Used only when (i) the rule is high-value to enforce
  mechanically AND (ii) the user explicitly approves Phase 4 work.

Capture the matrix in PILOT-NOTES at
`.plans/PILOT-NOTES-check-{{primitive}}-pattern-migration.md` (gitignored).
Get user approval on the classification before Phase 1.

### Phase 1 — Foundation

Mechanical setup. Most files copied verbatim from `check-bash-script`:
- `assets/output-example.json` — copy + swap example `rule_id`.
- `scripts/_common.py` — verbatim copy.
- `scripts/tests/__init__.py` + `scripts/tests/test_common.py` —
  verbatim copy.

After Phase 1: `python3 -m pytest plugins/build/skills/check-{{primitive}}/scripts/tests/`
passes (13 tests for `_common.py`).

### Phase 2 — Decompose audit-dimensions.md into judgment .md files

For each dimension classified as **judgment** in Phase 0, extract its
prose from `audit-dimensions.md` into a new file
`references/check-<dimension_id>.md` using the unified rule shape:

```markdown
---
name: <Human-Readable Title>
description: <One-sentence summary>
paths:                            # optional
  - "**/*.<ext>"
---

<One-line imperative statement>

**Why:** <reason — failure cost>

**How to apply:** <when/where, mechanics, edge cases>

```<lang>
<optional code example showing the compliant pattern>
```

**Exception:** <optional documented exemptions with rationale>
```

Don't paraphrase aggressively — preserve the original prose where it's
already crisp. The `audit-dimensions.md` file itself is deleted in
Phase 5.

### Phase 3 — Refactor each existing detection script

For every script in `scripts/check_*.{py,sh}`:

1. **Test fixture.** Build or reuse a fixture that triggers the
   script's checks. Capture pre-refactor stdout to
   `/tmp/<script>-baseline.txt`.
2. **Embed recipe constants.** For each rule the script handles, define
   a module-level `_RECIPE_<NAME>` (Python) or `RECIPE_<NAME>` (shell)
   constant containing the canonical repair guidance. Source from
   `repair-playbook.md`'s recipe for that rule. Concrete code example
   inside the constant when available.
3. **Refactor to emit JSON.** Import `_common.emit_json_finding`,
   `emit_rule_envelope`, `print_envelope`. Replace lint-format
   `printf`/`print` calls with finding accumulation; emit a single
   envelope (1-rule script) or JSON array (multi-rule). Multi-rule
   scripts emit one envelope per rule_id regardless of which fired
   (empty findings → `overall_status: pass`).
4. **Bash scripts emitting JSON.** Use the `python3 -c "$EMIT_PY"`
   pattern from `check-bash-script/scripts/check_shfmt.sh` — TSV
   collection in shell, JSON construction in inline Python, env vars
   for the recipe constants. Avoid the heredoc-as-stdin trap.
5. **Equivalence check.** Capture post-refactor JSON; verify same
   `rule_id`s firing, same severities, line numbers ±2, every finding
   has non-empty `recommended_changes`.
6. **`ruff check`** clean (Python) or **`bash -n`** clean (shell).
7. **Commit:** `refactor(check-{{primitive}}): check_<name>.{py,sh}
   emits JSON with embedded recipe[s]; equivalence verified`.

For external-linter wrappers (`ruff`, `actionlint`, `checkmake`,
etc.): follow `check_shellcheck.py`'s shape — module-level
`_LINT_TO_RULE: dict[str, tuple[str, str]]` mapping the linter's code →
`(rule_id, severity)`, plus a `_RECIPES: dict[str, str]` keyed by
`rule_id`. Emit one envelope per `rule_id` (empty findings for codes
that didn't fire). Missing-tool degradation: emit all envelopes with
`overall_status: inapplicable` and exit 0.

### Phase 4 — Promote judgment dimensions to scripts (OPTIONAL)

For each rule classified as **promote** in Phase 0, write a new
detection script following the same conventions as Phase 3. Document
the coverage gap in the script's docstring AND PILOT-NOTES (typically
20–40% of cases the heuristic misses; users accept the gap as the price
of mechanical detection). New scripts emit a single envelope.

If Phase 0 produced no **promote** rows, omit this phase entirely.

### Phase 5 — Prose migration + legacy doc deletion

1. **Audit `audit-dimensions.md` and `repair-playbook.md`** before
   deleting. Identify prose that is (a) already covered in
   `_shared/references/{{primitive}}-best-practices.md`, (b) needs
   migration there, (c) belongs in a script's recipe constant
   (already moved in Phase 3). Migrate (b) surgically — single
   sentences or short paragraphs, not wholesale dumps.
2. `git rm` `references/audit-dimensions.md` and
   `references/repair-playbook.md`.
3. Also `git rm` `references/_hub.md` and `references/fixtures/` if
   present (legacy artifacts).
4. **Commit:** `refactor(check-{{primitive}}): delete legacy
   audit-dimensions.md and repair-playbook.md; absorb convention prose`.

### Phase 6 — SKILL.md rewrite

Rewrite SKILL.md to match the pattern. Use
`plugins/build/skills/check-bash-script/SKILL.md` as the reference;
adapt domain-specific text (description, dimension table, anti-pattern
guards 4+ if any, handoff). The non-negotiables:

- **Frontmatter `references[]`** enumerates **only** the surviving
  `check-*.md` files plus
  `../../_shared/references/{{primitive}}-best-practices.md`. Sort
  alphabetically.
- **Frontmatter description** names the rule count (`N deterministic
  rules emitted as JSON envelopes plus M judgment dimensions`).
- **Tier-1 section** documents the JSON envelope shape verbatim (copy
  the block from check-bash-script SKILL.md). Lists a Script-to-rules
  map table enumerating each script's emitted `rule_id`s. Names the
  Tier-2-exclusion list (which FAILs short-circuit Tier-2).
- **Tier-2 section** says: "the primary agent reads each
  `references/check-*.md` and judges the artifact directly." Includes
  the **Evaluator policy** subsection verbatim (RULERS single-call,
  default-closed, severity floor WARN, one finding per dimension).
- **Anti-Pattern Guards** include the three pattern-mandatory ones:
  *Re-evaluating scripted rules in Tier-2*, *Suppressing the
  inapplicable envelope*, *Embellishing scripts' recommended_changes*.

### Phase 7 — Validation

- `python3 plugins/build/_shared/scripts/check_skill_pattern.py
  plugins/build/skills/check-{{primitive}} --human` — every envelope
  passes (`Summary: N pass, 0 warn, 0 fail`).
- `python3 -m pytest` — full repo suite, all green.
- `ruff check plugins/build/skills/check-{{primitive}}/` — clean.
- Spot-check one rule per script: run the script on a fixture; confirm
  JSON output, `recommended_changes` non-empty, severity matches the
  classification matrix from Phase 0.

## File Changes

**Create:**

- `plugins/build/skills/check-{{primitive}}/assets/output-example.json`
- `plugins/build/skills/check-{{primitive}}/scripts/_common.py`
- `plugins/build/skills/check-{{primitive}}/scripts/tests/__init__.py`
- `plugins/build/skills/check-{{primitive}}/scripts/tests/test_common.py`
- `plugins/build/skills/check-{{primitive}}/references/check-<dimension>.md` × M (one per judgment dimension surviving Phase 0)
- `plugins/build/skills/check-{{primitive}}/scripts/check_<rule>.{py,sh}` × P (only if Phase 4 promotes any rules)
- `.plans/PILOT-NOTES-check-{{primitive}}-pattern-migration.md` (gitignored)

**Modify:**

- `plugins/build/skills/check-{{primitive}}/SKILL.md`
- `plugins/build/skills/check-{{primitive}}/scripts/check_<existing>.{py,sh}` × Q (refactor each existing script to emit JSON)
- `plugins/build/_shared/references/{{primitive}}-best-practices.md` (absorb migrated prose)

**Delete:**

- `plugins/build/skills/check-{{primitive}}/references/audit-dimensions.md`
- `plugins/build/skills/check-{{primitive}}/references/repair-playbook.md`
- `plugins/build/skills/check-{{primitive}}/references/_hub.md` (if present)
- `plugins/build/skills/check-{{primitive}}/references/fixtures/` (if present)

## Tasks

Replace the placeholders below per the Phase 0 audit's results. Tasks
mirror the bash-script migration's task structure.

---

### Task 1: Phase 0 — Rule classification audit

**Files:**
- Create: `.plans/PILOT-NOTES-check-{{primitive}}-pattern-migration.md`

- [ ] **Step 1:** Read `references/audit-dimensions.md` and
      `references/repair-playbook.md` end to end. Note the dimensions /
      rules they enforce.
- [ ] **Step 2:** Read each `scripts/check_*.{py,sh}` and identify the
      rule_id(s) it emits in lint format.
- [ ] **Step 3:** Build the rule classification matrix in PILOT-NOTES:
      one row per rule, with columns `(rule, source, mechanical_pct,
      decision, notes)`. The decision column is `judgment` / `scripted`
      / `promote`.
- [ ] **Step 4:** Pause and request user approval on the matrix.
      Iteration here is cheap; iteration in later phases is expensive.

---

### Task 2: Phase 1 — Foundation (assets, _common.py, tests)

**Files:**
- Create: `plugins/build/skills/check-{{primitive}}/assets/output-example.json`
- Create: `plugins/build/skills/check-{{primitive}}/scripts/_common.py`
- Create: `plugins/build/skills/check-{{primitive}}/scripts/tests/__init__.py`
- Create: `plugins/build/skills/check-{{primitive}}/scripts/tests/test_common.py`

**Depends on:** Task 1

- [ ] **Step 1:** Copy `assets/output-example.json` from
      `check-bash-script`; swap the example `rule_id` to a {{primitive}}
      rule (e.g., shebang/strict-mode for shell, header-docstring for
      python).
- [ ] **Step 2:** Copy `scripts/_common.py` from `check-bash-script`
      verbatim.
- [ ] **Step 3:** Copy `scripts/tests/__init__.py` + `test_common.py`
      verbatim.
- [ ] **Step 4:** Run
      `python3 -m pytest plugins/build/skills/check-{{primitive}}/scripts/tests/`
      — 13 tests pass.
- [ ] **Step 5:** `ruff check
      plugins/build/skills/check-{{primitive}}/scripts/` clean.
- [ ] **Step 6:** Commit: `feat(check-{{primitive}}): add scripts/_common.py
      + assets/output-example.json (pattern foundation)`.

---

### Task 3: Phase 2 — Decompose audit-dimensions.md into check-*.md

**Files:**
- Create: `references/check-<dimension_id>.md` × M

**Depends on:** Task 1

- [ ] **Step 1..M:** For each dimension classified as `judgment`,
      extract its prose into `references/check-<id>.md` with the unified
      rule shape (frontmatter + imperative + Why + How to apply +
      example + Exception).
- [ ] **Step M+1:** Sanity check: `ls references/check-*.md | wc -l`
      matches the count of judgment-classified rules.
- [ ] **Step M+2:** Commit: `feat(check-{{primitive}}): decompose
      audit-dimensions.md into M per-dimension judgment rule files`.

---

### Task 4..(3+Q): Phase 3 — Refactor existing scripts to JSON

**(One task per existing detection script. Sequenced simplest-first.)**

For each existing `scripts/check_<existing>.{py,sh}`:

**Files:** Modify the script.

**Depends on:** Task 2

- [ ] **Step 1:** Test fixture (build or reuse). Capture pre-refactor
      stdout.
- [ ] **Step 2:** Embed recipe constant(s) sourced from `repair-playbook.md`.
- [ ] **Step 3:** Refactor to emit JSON envelope(s) via `_common`.
- [ ] **Step 4:** Capture post-refactor JSON; verify equivalence (same
      rule_ids, severities, lines ±2, recipes non-empty).
- [ ] **Step 5:** `ruff check` (py) or `bash -n` (sh) clean.
- [ ] **Step 6:** Commit: `refactor(check-{{primitive}}):
      check_<name>.{py,sh} emits JSON with embedded recipe[s]`.

---

### Task (4+Q)..(3+Q+P): Phase 4 — Promote judgment dimensions to scripts (OPTIONAL)

**(Skip if Phase 0 produced no `promote` rows.)**

**Files:**
- Create: `scripts/check_<promoted-rule>.{py,sh}`

**Depends on:** Task 2

For each promoted rule:

- [ ] **Step 1:** Hand-curated fixture exercising the rule's main detection cases.
- [ ] **Step 2:** Author the script. Embed recipe constant.
- [ ] **Step 3:** Emit JSON envelope via `_common`.
- [ ] **Step 4:** Document the coverage gap in the script's docstring +
      PILOT-NOTES (typically 20–40%).
- [ ] **Step 5:** `ruff check` clean.
- [ ] **Step 6:** Commit: `feat(check-{{primitive}}): add
      check_<rule>.{py,sh} — promote <rule> to scripted (~K% coverage;
      gaps documented)`.

---

### Task X: Phase 5 — Prose migration + legacy doc deletion

**Files:**
- Modify: `plugins/build/_shared/references/{{primitive}}-best-practices.md`
- Delete: `references/audit-dimensions.md`, `references/repair-playbook.md`
  (and `_hub.md`, `fixtures/` if present)

**Depends on:** Tasks 3–(3+Q+P)

- [ ] **Step 1:** Audit each legacy doc for prose not already covered
      in `{{primitive}}-best-practices.md`. List sentence-level
      additions in PILOT-NOTES.
- [ ] **Step 2:** Apply surgical migrations to the canonical doc.
- [ ] **Step 3:** `git rm` legacy artifacts.
- [ ] **Step 4:** Commit: `refactor(check-{{primitive}}): delete legacy
      audit-dimensions.md and repair-playbook.md; absorb convention
      prose into {{primitive}}-best-practices.md`.

---

### Task Y: Phase 6 — SKILL.md rewrite

**Files:**
- Modify: `plugins/build/skills/check-{{primitive}}/SKILL.md`

**Depends on:** Task X

- [ ] **Step 1:** Update frontmatter description (rule count + dimension
      list).
- [ ] **Step 2:** Update `references[]` to enumerate exactly the
      surviving `check-*.md` files plus
      `../../_shared/references/{{primitive}}-best-practices.md`.
- [ ] **Step 3:** Rewrite Tier-1 section with the JSON envelope shape
      block + Script-to-rules map.
- [ ] **Step 4:** Rewrite Tier-2 section with primary-agent inline
      reading + Evaluator policy subsection.
- [ ] **Step 5:** Update Anti-Pattern Guards to include the three
      pattern-mandatory ones.
- [ ] **Step 6:** Update Handoff to reflect JSON-envelope output.
- [ ] **Step 7:** Commit: `refactor(check-{{primitive}}): rewrite SKILL.md
      for unified pattern (primary-agent Tier-2; JSON envelopes;
      Script-to-rules map)`.

---

### Task Z: Phase 7 — Validation

**Depends on:** Task Y

- [ ] **Step 1:**
      `python3 plugins/build/_shared/scripts/check_skill_pattern.py
      plugins/build/skills/check-{{primitive}} --human` — every envelope
      passes.
- [ ] **Step 2:** Run all 9 (or however many) detection scripts on a
      representative artifact; verify each emits valid JSON; aggregate
      `recommended_changes` non-empty for every finding.
- [ ] **Step 3:** `python3 -m pytest` — full suite passes.
- [ ] **Step 4:** `ruff check plugins/build/skills/check-{{primitive}}/`
      clean.
- [ ] **Step 5:** Finalize PILOT-NOTES with per-script equivalence
      summaries, coverage gaps for promoted rules (if any), and any
      lessons learned for the sweep.
- [ ] **Step 6:** Open PR per `/work:finish-work`.

## Validation

- [ ] `python3 plugins/build/_shared/scripts/check_skill_pattern.py plugins/build/skills/check-{{primitive}}` exits 0.
- [ ] `ls plugins/build/skills/check-{{primitive}}/references/check-*.md | wc -l` equals the count of `judgment`-classified rules from Phase 0.
- [ ] `ls plugins/build/skills/check-{{primitive}}/references/rule-*.md` returns nothing.
- [ ] `ls plugins/build/skills/check-{{primitive}}/references/audit-dimensions.md plugins/build/skills/check-{{primitive}}/references/repair-playbook.md` — neither exists.
- [ ] `ls plugins/build/skills/check-{{primitive}}/assets/output-example.json` exists; valid JSON.
- [ ] `ls plugins/build/skills/check-{{primitive}}/scripts/_common.py plugins/build/skills/check-{{primitive}}/scripts/tests/test_common.py` — both exist (skip for pure-judgment skills).
- [ ] SKILL.md `references[]` enumerates exactly the surviving `check-*.md` files + `{{primitive}}-best-practices.md`.
- [ ] Each refactored script emits valid JSON with non-empty `recommended_changes`: spot-check 3 random scripts.
- [ ] `python3 -m pytest` — all green.
- [ ] `ruff check plugins/build/skills/check-{{primitive}}/` — clean.
- [ ] `git diff --stat main...HEAD -- plugins/build/skills/check-bash-script plugins/build/skills/check-other-skill plugins/wiki/ plugins/work/ plugins/consider/` — empty (only this skill changed).

## Notes

- **Coverage gaps are documented, not hidden.** Every promote-to-script
  rule names its missed cases in the script's docstring and in
  PILOT-NOTES. The 70% threshold accepts the gap as the price of
  architectural cleanliness.
- **The pattern doc is the authoritative reference.** When in doubt,
  read `plugins/build/_shared/references/check-skill-pattern.md`. This
  template is its operational companion; the pattern doc is its spec.
- **One commit per logical unit.** Granular reverts are the safety
  rail. ~{{commit-count}} commits expected. The validation script
  catches drift in any of them.
```

## Plan body — copy to here ⤴

---

## Per-skill calibration cheat sheet

For the 13 check-* skills, here are the rough commit-count estimates and
sequencing considerations:

| Skill | Profile | Detection scripts (now) | Est. commits | Notes |
|---|---|---|---|---|
| `check-skill-chain` | Pure-judgment, blank | 0 | ~3 | Simplest. No `_common.py`. |
| `check-skill-pair` | Pure-judgment | 0 | ~3 | Same as above; has audit-dim+repair to delete. |
| `check-hook` | Pure-judgment | 0 | ~3 | Same; the dimensions doc is comprehensive. |
| `check-help-skill` | Tiny | 1 | ~5 | One script to refactor. |
| `check-resolver` | Small | 3 | ~7 | Pure-judgment alternative if scripts are weak. |
| `check-rule` | Small | 4 | ~7 | |
| `check-skill` | Medium | 5 | ~10 | Will absorb `check_skill_pattern.py` per #407 — add as Phase 4 promotion. |
| `check-pre-commit-config` | Medium (wraps `pre-commit`) | 6 | ~10 | External-linter wrapper pattern. |
| `check-python-script` | Medium (wraps `ruff`) | 6 | ~10 | External-linter wrapper. |
| `check-readme` | Medium | 7 | ~10 | |
| `check-subagent` | Medium | 8 | ~12 | |
| `check-github-workflow` | Large (wraps `actionlint`/`zizmor`) | 9 | ~14 | External-linter wrapper. Largest SC-code-style mapping table. |
| `check-makefile` | Large (wraps `checkmake`) | 11 | ~16 | External-linter wrapper. |

**Recommended sweep order (easy-first):**

1. `check-skill-chain` (3 commits)
2. `check-skill-pair`
3. `check-hook`
4. `check-help-skill`
5. `check-resolver`
6. `check-rule`
7. `check-skill` (absorbs the pattern audit script via Phase 4)
8. `check-subagent`
9. `check-readme`
10. `check-pre-commit-config`
11. `check-python-script`
12. `check-github-workflow`
13. `check-makefile`

---

**Diagnostic when a per-skill migration stalls.** First check the
classification matrix: did Phase 0 produce a clean `judgment` /
`scripted` split, or are too many rules `unknown`? Then check the
prose-migration mapping: is `{{primitive}}-best-practices.md`
absorbing genuine convention deltas, or is it bloating with
quick-fix imports? Then re-read the pattern doc: most stalls are the
pattern's discipline asserting itself — the fix is to honor the
single-artifact-per-rule principle, not to work around it.
