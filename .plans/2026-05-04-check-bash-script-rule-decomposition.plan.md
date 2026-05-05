---
name: check-bash-script Rule Decomposition (Pilot)
description: Pilot a unified per-rule documentation convention on check-bash-script — each rule becomes one flat `rule-*.md` file using the Claude-rule body shape (per `rule-best-practices.md`); the same file serves both Claude (ambient editing) and the audit dispatcher subagent.
type: plan
status: executing
branch: refactor/check-bash-script-rule-decomposition
related:
  - .plans/2026-05-02-reference-doc-splitting.plan.md
  - plugins/build/skills/check-bash-script/SKILL.md
  - plugins/build/_shared/references/rule-best-practices.md
  - AGENTS.md
follow_ups:
  - https://github.com/bcbeidel/toolkit/issues/406  # build-skill scaffolder update
  - https://github.com/bcbeidel/toolkit/issues/407  # check-skill audit update
  - https://github.com/bcbeidel/toolkit/issues/408  # sweep across remaining 11 check-* skills
---

# check-bash-script Rule Decomposition (Pilot)

## Goal

Pilot a unified per-rule documentation convention on a single check-* skill
(`check-bash-script`). Each rule today encoded as a row in
`audit-dimensions.md` and a recipe in `repair-playbook.md` becomes one
flat `references/rule-<id>.md` file. The file uses the **Claude-rule body
shape** specified in
[`plugins/build/_shared/references/rule-best-practices.md`](../plugins/build/_shared/references/rule-best-practices.md):
imperative statement + **Why** + **How to apply** + optional example.

Frontmatter is minimal — `name`, `description`, optional `paths` — matching
the spec in `rule-best-practices.md`. No invented fields (`tier`, `script`,
`severity`, `category`); their roles are filled by naming convention,
script logic, and finding-emission metadata.

The same file serves two consumers:
- **Claude (ambient editing)** loads it via `paths:` glob when editing
  bash scripts; uses the body as preemptive guidance.
- **Audit dispatcher subagent** loads it on-demand; uses the body as
  the rubric (judgment-based detection) or recipe (script-based
  finding repair).

After this pilot ships:
- `PILOT-NOTES.md` documents observed cross-skill rule duplication,
  recompose surprises, and rollout recommendations.
- Three filed follow-ups (#406, #407, #408) handle scaffolder update,
  audit recognition, and the sweep across the remaining 11 check-* skills.
- The Stage-2 dispatcher subagent (separate plan) consumes these
  per-rule files as input — this pilot is its enabler.

## Scope

### Must have

- **Per-rule files** — every rule documented today in
  `check-bash-script/references/audit-dimensions.md` (32 Tier-1 rules
  after splitting the 2 combined shellcheck entries into one file
  per SC code, 7 Tier-2 dimensions, 1 Tier-3 cross-entity) becomes a
  single flat file at `references/rule-<id>.md`. Total: 40 rule files.
- **Unified Claude-rule body shape** — every rule file body follows
  `rule-best-practices.md`: one-line imperative statement, **Why**
  paragraph, **How to apply** paragraph, optional example block,
  optional named exception. No `## Detection` / `## Repair` split.
- **Minimal frontmatter** — every file: `name` (human-readable title),
  `description` (one-sentence TOC entry), `paths` (optional — set to
  bash globs for rules where ambient Claude guidance applies; omitted
  for rules where on-demand audit-only consumption is the only consumer).
- **Substance preservation, not byte preservation** — the rule's
  *substance* (what to detect, what to fix, why it matters) must be
  preserved. The *framing* shifts from audit prose ("Signal X — fix by
  doing Y") to convention prose ("Do X. Why: ... How to apply: ...").
  This is a recompose, not a verbatim move.
- **Single hub** — `references/_hub.md` (hand-authored TOC), grouping
  rules with section headers (Deterministic / Judgment / Cross-Entity).
  Includes any cross-rule framing notes (RULERS guidance for judgment
  rules, evaluator-policy notes) that don't fit inside a single rule.
- **Filename convention** — `rule-<kebab-id>.md`. Human-readable
  kebab-case rule names, no SC-code prefix (SC code in body if relevant).
  Examples: `rule-strict-mode.md`, `rule-unquoted-variable-expansion.md`,
  `rule-cross-entity-collision.md`.
- **Combined shellcheck entries split** — the existing
  `repair-playbook.md` combines `SC2010 / SC2012 / SC2045` and
  `SC2013 / SC2162` into single sections; each SC code becomes its
  own file. Each split file's body adapts the original recipe to the
  specific SC code.
- **SKILL.md `references:` array updated** — enumerates the hub +
  every rule file + the existing
  `_shared/references/bash-script-best-practices.md`.
- **Old files deleted** — `audit-dimensions.md` and `repair-playbook.md`
  removed; their content has moved entirely.
- **Audit-run equivalence** — `scripts/*.{py,sh}` are untouched;
  running the audit produces the same findings before/after on a
  representative artifact. Per-rule files do not drive script logic;
  they are documentation consumed by humans, Claude, and the audit
  subagent — never by the detection scripts.
- **`PILOT-NOTES.md`** — captures: (a) the alignment audit table
  mapping each source row/section to its destination rule file, (b)
  observed cross-skill rule duplication (input to a future
  `_shared/references/` extraction decision), (c) recompose surprises
  (rules where translating audit prose to convention prose was awkward),
  (d) rollout recommendations for the sweep.
- **One commit per logical unit** (per rule file, hub, SKILL.md
  update, deletion, equivalence test, notes) for granular revert.
  ~40–50 commits expected.

### Won't have

- **No changes to other check-* skills.** The sweep is #408.
- **No update to `build-rule` scaffolder.** It still scaffolds Claude
  rules with the spec from `rule-best-practices.md`. The pilot's
  per-rule files happen to follow that same shape (which is the
  point), so no scaffolder change is needed for this pilot.
  A future scaffolder mode that knows about audit-rule conventions
  can be filed if hand-authoring is the pain point — not in scope.
- **No update to `check-skill` audit.** Today it expects
  `audit-dimensions.md` + `repair-playbook.md`; this pilot will
  produce a check-* skill that doesn't have those files. Acceptable
  for a single pilot; the audit may emit warnings on this skill until
  updated. Issue #407.
- **No dispatcher subagent.** Stage 2 (parameterized subagent
  producing structured `{rule_id, status, reasoning,
  recommended_changes}`) is a separate plan. The per-rule files
  this pilot creates are the substrate for that work but not
  consumed by it yet.
- **No `.claude/rules/` pointer file.** A toolkit-internal Claude
  rule that points at this skill's per-rule directory (so Claude
  ambient-loads them when editing bash scripts in the toolkit repo)
  is a follow-up — not in pilot scope.
- **No `_shared/references/` extraction.** Cross-skill rule
  duplication will become grep-able after this PR; PILOT-NOTES
  records observations; acting on them is a separate plan.
- **No invented frontmatter fields.** `name`, `description`, optional
  `paths` only. Discriminators that earlier drafts included (`tier`,
  `script`, `severity`, `category`, `type`, `related`,
  `shellcheck-code`) are dropped — their roles are recovered from
  filename convention, script source, and finding metadata.
- **No script changes.** `scripts/check_*.{py,sh}` stay byte-identical.
  The pilot tests that the audit run produces equivalent findings —
  if it doesn't, the per-rule file content is wrong, not the script.
- **No splits to non-check-bash-script files.** Even if scanner
  flags a sibling file as oversized, this PR doesn't touch it.

## Approach

### The convention

Each rule file matches the shape in `rule-best-practices.md`:

```markdown
---
name: <Human-Readable Title>
description: <One-sentence summary, suitable as TOC entry>
paths: ["**/*.sh", "**/*.bash"]   # optional; set for path-scoped rules
---

<One-line imperative statement of the rule.>

**Why:** <reason — failure cost, what breaks, why the convention exists.>

**How to apply:** <when/where, mechanics, edge cases, named exceptions.>

```bash
# <Optional: code example showing the compliant pattern.>
```

**Exception:** <Optional: documented exceptions with rationale.>
```

Filename: `rule-<kebab-id>.md`. The rule-id is human-readable kebab-case
matching the `name:` field in lower form. No tier prefix in filename
or frontmatter.

### Recovering metadata without dedicated frontmatter fields

| Lost field | How recovered |
|---|---|
| `tier` (1\|2\|3) | Lives in invocation context: scripts emit Tier-1 findings; the dispatcher invokes LLM judgment for Tier-2 (judgment) rules; cross-entity Tier-3 is dispatcher-orchestrated. The audit script knows which is which by which rules its checks fire against. |
| `script` (binding) | Naming convention: rule `name: Strict Mode` (filename `rule-strict-mode.md`) corresponds to `check_structure.py::check_strict_mode`. Scripts already enumerate the checks they implement. Binding by convention, not pointer. |
| `severity`, `category` | Property of the *finding* (emitted by the script), not of the rule. The hub TOC that wants severity/category columns reads the script source or is hand-maintained. |
| `related` | Body-level cross-references where useful ("see also: rule-shebang.md"). Frontmatter navigation isn't load-bearing. |

### Combined shellcheck entries

The current `repair-playbook.md` combines `SC2010 / SC2012 / SC2045`
(parsing ls output) and `SC2013 / SC2162` (`for line in $(cat file)`)
into single sections. Per the unified body shape, each SC code becomes
its own rule file. The combined recipe content is recomposed into
per-SC-code body prose; each file states its own one-line imperative
("Iterate filenames with globs, not by parsing `ls` output"), its own
Why, its own How-to-apply, with cross-references to the related
SC-code files.

### Hub shape

`references/_hub.md` — hand-authored TOC. Frontmatter:

```yaml
---
name: check-bash-script Rules
description: Index of all 40 rules check-bash-script enforces.
---
```

Body: section headers grouping rules logically. Suggested groupings:

```markdown
# check-bash-script Rules

## Cross-rule framing

- Bash scripts the audit reads use these rules as the convention spec.
- Tier-1 fail findings short-circuit Tier-2 (judgment skips when
  structural rules fail).
- Tier-2 evaluation: present all judgment rules in a single LLM call
  (Hong et al. 2026, RULERS — per-criterion separation scores 11.5pt
  lower). Default-closed: borderline → WARN.

## Deterministic Checks (32)

- [Strict Mode](rule-strict-mode.md) — `set -euo pipefail` required
- [Shebang](rule-shebang.md) — first line `#!/usr/bin/env bash`
- ... (rest of 32)

## Judgment Dimensions (7)

- [Output Discipline](rule-output-discipline.md)
- ... (rest of 7)

## Cross-Entity (1)

- [Cross-Entity Collision](rule-cross-entity-collision.md)
```

The hub provides at-a-glance navigation. Severity and script-binding
columns are omitted from the hub for the pilot (they're properties of
findings/scripts, not rules); a future scripted hub-renderer can derive
those if needed.

### Pilot mechanics

1. **Alignment audit + recompose mapping** — produce a side-by-side
   table mapping every source-file location (`audit-dimensions.md`
   row, `repair-playbook.md` section) to its destination rule file.
   For each rule, sketch the unified body shape: what's the imperative
   statement; what's the Why; what's the How-to-apply; is there an
   example; is there a named exception. Surface orphans (rule with no
   recipe, recipe with no rule) and resolve.
2. **Template lock** — author 3 representative rule files end-to-end:
   one Tier-1 (e.g., `rule-strict-mode.md`), one Tier-2 (e.g.,
   `rule-output-discipline.md`), one Tier-3 (`rule-cross-entity-collision.md`).
   Confirm the template fits before bulk authoring.
3. **Tier-1 sweep** — author the 31 remaining Tier-1 rule files, one
   commit each.
4. **Tier-2 sweep** — author the 6 remaining Tier-2 dimension files,
   one commit each.
5. **Hub + SKILL.md update + delete originals** — single commit.
6. **Equivalence test + PILOT-NOTES** — verify scripts produce same
   findings before/after; write up findings.

## File Changes

**Create (~42 new files):**

- `plugins/build/skills/check-bash-script/references/_hub.md`
- `plugins/build/skills/check-bash-script/references/rule-secret.md`
- `plugins/build/skills/check-bash-script/references/rule-shebang.md`
- `plugins/build/skills/check-bash-script/references/rule-strict-mode.md`
- `plugins/build/skills/check-bash-script/references/rule-header-comment.md`
- `plugins/build/skills/check-bash-script/references/rule-main-fn.md`
- `plugins/build/skills/check-bash-script/references/rule-main-guard.md`
- `plugins/build/skills/check-bash-script/references/rule-readonly-config.md`
- `plugins/build/skills/check-bash-script/references/rule-mktemp-trap-pairing.md`
- `plugins/build/skills/check-bash-script/references/rule-bracket-test.md`
- `plugins/build/skills/check-bash-script/references/rule-printf-over-echo.md`
- `plugins/build/skills/check-bash-script/references/rule-var-braces.md`
- `plugins/build/skills/check-bash-script/references/rule-eval.md`
- `plugins/build/skills/check-bash-script/references/rule-gnu-flags.md`
- `plugins/build/skills/check-bash-script/references/rule-tmp-literal.md`
- `plugins/build/skills/check-bash-script/references/rule-unquoted-variable-expansion.md` (SC2086)
- `plugins/build/skills/check-bash-script/references/rule-unquoted-command-substitution.md` (SC2046)
- `plugins/build/skills/check-bash-script/references/rule-unquoted-args-expansion.md` (SC2068)
- `plugins/build/skills/check-bash-script/references/rule-referenced-but-not-assigned.md` (SC2154)
- `plugins/build/skills/check-bash-script/references/rule-unscoped-function-variable.md` (SC2155)
- `plugins/build/skills/check-bash-script/references/rule-backtick-command-substitution.md` (SC2006)
- `plugins/build/skills/check-bash-script/references/rule-ls-grep-parsing.md` (SC2010 — split)
- `plugins/build/skills/check-bash-script/references/rule-ls-instead-of-find.md` (SC2012 — split)
- `plugins/build/skills/check-bash-script/references/rule-iterating-ls-output.md` (SC2045 — split)
- `plugins/build/skills/check-bash-script/references/rule-for-line-in-cat.md` (SC2013 — split)
- `plugins/build/skills/check-bash-script/references/rule-read-without-r.md` (SC2162 — split)
- `plugins/build/skills/check-bash-script/references/rule-find-xargs-without-print0.md` (SC2038)
- `plugins/build/skills/check-bash-script/references/rule-cd-without-exit-handling.md` (SC2164)
- `plugins/build/skills/check-bash-script/references/rule-useless-cat.md` (SC2002)
- `plugins/build/skills/check-bash-script/references/rule-eval-of-array.md` (SC2294)
- `plugins/build/skills/check-bash-script/references/rule-format.md`
- `plugins/build/skills/check-bash-script/references/rule-size.md`
- `plugins/build/skills/check-bash-script/references/rule-line-length.md`
- `plugins/build/skills/check-bash-script/references/rule-output-discipline.md` (D1)
- `plugins/build/skills/check-bash-script/references/rule-input-validation.md` (D2)
- `plugins/build/skills/check-bash-script/references/rule-subprocess-tool-hygiene.md` (D3)
- `plugins/build/skills/check-bash-script/references/rule-performance-intent.md` (D4)
- `plugins/build/skills/check-bash-script/references/rule-function-design.md` (D5)
- `plugins/build/skills/check-bash-script/references/rule-naming.md` (D6)
- `plugins/build/skills/check-bash-script/references/rule-commenting-intent.md` (D7)
- `plugins/build/skills/check-bash-script/references/rule-cross-entity-collision.md`
- `.plans/PILOT-NOTES-check-bash-script-decomposition.md`

**Modify:**

- `plugins/build/skills/check-bash-script/SKILL.md` — `references:` array

**Delete:**

- `plugins/build/skills/check-bash-script/references/audit-dimensions.md`
- `plugins/build/skills/check-bash-script/references/repair-playbook.md`

**Branch:** `refactor/check-bash-script-rule-decomposition` (cut from `main`)

## Tasks

Six tasks. Task 1 establishes the prerequisite mapping; Task 2 locks
the templates against real content; Tasks 3–4 are bulk authoring; Task
5 wires up the new structure; Task 6 verifies equivalence and captures
pilot learnings.

---

### Task 1: Alignment audit and recompose mapping

**Files:**
- Create: `.plans/PILOT-NOTES-check-bash-script-decomposition.md` (start the file)
- Reference (read-only): both source `references/*.md`

- [x] **Step 1:** Build the alignment table — every Tier-1 signal name in `repair-playbook.md` mapped to its row in the `audit-dimensions.md` Tier-1 table; every Tier-2 dimension cross-referenced 1:1; the Tier-3 entry mapped. <!-- sha:d6c53a4 -->
- [x] **Step 2:** Identify orphans (rule with no recipe, or recipe with no rule). For each orphan: write the missing half during the sweep, or document why intentional. <!-- sha:d6c53a4 -->
- [x] **Step 3:** Confirm the rule-id list — the canonical kebab-case id for each of the 40 destination files. Resolve any naming ambiguities; write the canonical id list into PILOT-NOTES. <!-- sha:d6c53a4 -->
- [x] **Step 4:** For each rule, sketch the unified body shape in 2–3 lines: what's the one-line imperative; what's the Why (failure cost + exception); what's the How-to-apply; is there an example. This is the recompose plan — no full prose yet, just enough to confirm the source content maps to the unified shape without losing substance. <!-- sha:d6c53a4 -->
- [x] **Step 5:** Verify each Tier-1 rule maps to a real function in `scripts/`. Use `grep -rn "def check_" plugins/build/skills/check-bash-script/scripts/` for Python and `grep -nE '^[a-z_]+\(\)' plugins/build/skills/check-bash-script/scripts/*.sh` for Bash. Record the script-binding (by convention, not frontmatter) in PILOT-NOTES alongside the rule-id list. This data informs follow-up #407. <!-- sha:d6c53a4 -->
- [x] **Step 6:** Commit: `docs(check-bash-script): record alignment audit and recompose plan for decomposition pilot`. <!-- sha:d6c53a4 -->

**Task 1 deliverables (PILOT-NOTES sections):**
- Alignment audit table — 40 rules, 0 orphans, 1:1 mapping confirmed
- Recompose sketches — 40 sketches confirming unified body shape fits all rules
- Script-binding inventory — bindings recorded; **finding for #407**: bindings NOT 1:1 by function name (e.g., `check_idioms.py::_check_file` emits 3 rules; `check_shellcheck.py::_check_file` delegates 12 rules; `check_size.sh::check_file` emits 2 rules)

---

### Task 2: Template lock with three representative rules

**Files:**
- Create: `references/rule-strict-mode.md` (Tier-1, simple convention)
- Create: `references/rule-output-discipline.md` (Tier-2, judgment dimension)
- Create: `references/rule-cross-entity-collision.md` (Tier-3)

**Depends on:** Task 1

- [x] **Step 1:** Write `rule-strict-mode.md` end-to-end using the `rule-best-practices.md` shape. Frontmatter: `name`, `description`, `paths: ["**/*.sh", "**/*.bash"]`. Body: imperative + Why + How to apply + bash code example + exception block. Verify substance is preserved against source files (no semantic drift). <!-- sha:40fa38f -->
- [x] **Step 2:** Write `rule-output-discipline.md` end-to-end. Tier-2 rule body has more rubric content (criteria for judging) — confirm the unified shape accommodates this without forcing a `## Detection` / `## Repair` split. The rubric IS the How-to-apply; the recipe IS the example/exception. <!-- sha:40fa38f -->
- [x] **Step 3:** Write `rule-cross-entity-collision.md` end-to-end. Tier-3 rules describe cross-script analysis; `paths:` may be broader (e.g., `["**/*.sh", "**/*.bash"]`) since the rule applies to bash files in aggregate. <!-- sha:40fa38f -->
- [x] **Step 4:** Self-review the three files for template fit. If anything doesn't generalize cleanly, revise the template definition in this plan's Approach section before continuing. Update the recompose plan in PILOT-NOTES if learnings shift it. <!-- sha:40fa38f -->
- [x] **Step 5:** Commit: `docs(check-bash-script): lock per-rule unified-shape templates with three pilot rules`. <!-- sha:40fa38f -->

**Task 2 deliverables:**
- 3 pilot rule files (`rule-strict-mode.md`, `rule-output-discipline.md`, `rule-cross-entity-collision.md`) — under 10K cap each (1.9K, 2.5K, 3.1K).
- PILOT-NOTES "Recompose surprises" populated with template-fit observations: Tier-2 rules want "Common fail signals" sub-list; Tier-3 rules want "Audit guidance" subsection. Unified body shape works for all three tiers.
- Recommended template extensions carried into rollout-sweep template (per-tier shape variants).

---

### Task 3: Tier-1 sweep — 31 remaining deterministic-rule files

**Files:** 31 new `references/rule-*.md` files (all Tier-1 rules except `strict-mode` from Task 2)

**Depends on:** Task 2

- [x] **Step 1:** Author each Tier-1 rule file using the locked template. Substance preserved from `audit-dimensions.md` (table row + relevant note) and `repair-playbook.md` (matching `### Signal:` section). Recompose into the unified body shape: imperative, Why, How to apply, optional example. **Combined-entry splits** (SC2010/2012/2045 → 3 files; SC2013/2162 → 2 files): each split file's body adapts the original combined recipe to the specific SC code; cross-references via body prose ("see also: rule-ls-instead-of-find.md"). <!-- sha:dfe1a8b -->
- [x] **Step 2:** One commit per file: `docs(check-bash-script): add rule file <rule-id>`. <!-- sha:dfe1a8b -->
- [x] **Step 3:** After all 31 written, sanity check: `ls plugins/build/skills/check-bash-script/references/rule-*.md | wc -l` returns 33 (32 Tier-1 + 1 Tier-3 from Task 2; Tier-2 not yet authored). Confirm no rule-id collisions. <!-- sha:dfe1a8b -->

---

### Task 4: Tier-2 sweep — 6 remaining judgment-dimension files

**Files:** 6 new `references/rule-*.md` files (D2 through D7)

**Depends on:** Task 3

- [x] **Step 1:** Author each Tier-2 dimension file using the locked template. Body content carries from `audit-dimensions.md` H3 sections under `## Tier-2` (rubric → How to apply / examples) and `repair-playbook.md` `### D{N}` sections (recipe → example/exception). Tier-2 rules have more body content because the LLM uses the body as the rubric — keep it focused but allow longer How-to-apply sections. <!-- sha:564c8ff -->
- [x] **Step 2:** One commit per file: `docs(check-bash-script): add rule file <dimension-id>`. <!-- sha:564c8ff -->
- [x] **Step 3:** After all 6 written, total `references/rule-*.md` count: 40 (32 Tier-1 + 7 Tier-2 + 1 Tier-3). <!-- sha:564c8ff -->

---

### Task 5: Hub, SKILL.md update, delete originals

**Files:**
- Create: `references/_hub.md`
- Modify: `SKILL.md`
- Delete: `references/audit-dimensions.md`
- Delete: `references/repair-playbook.md`

**Depends on:** Task 4

- [ ] **Step 1:** Author `_hub.md` — frontmatter (`name`, `description`); body groups rules under `## Deterministic Checks (32)`, `## Judgment Dimensions (7)`, `## Cross-Entity (1)` headers; one bullet per rule with a short description. Carries cross-rule framing notes (RULERS guidance, Tier-1 short-circuit on Tier-2, default-closed evaluator policy) at the top.
- [ ] **Step 2:** Update `SKILL.md` `references:` array to enumerate: existing `_shared/references/bash-script-best-practices.md` + `references/_hub.md` + every `references/rule-*.md`. Sort alphabetically for stability.
- [ ] **Step 3:** Delete `audit-dimensions.md` and `repair-playbook.md`.
- [ ] **Step 4:** Commit (single commit): `refactor(check-bash-script): add hub, update SKILL.md references, delete monolithic source files`.

---

### Task 6: Equivalence test, scanner re-run, PILOT-NOTES finalization

**Files:**
- Modify: `.plans/PILOT-NOTES-check-bash-script-decomposition.md`

**Depends on:** Task 5

- [ ] **Step 1:** Build a minimal purpose-built fixture at `/tmp/equiv-fixture.sh` — ~5–10 lines of bash with one intentional rule violation (e.g., shebang present but `set -euo pipefail` missing, so `strict-mode` fires; nothing else). Single-rule fixtures make the equivalence test trivially interpretable. Run the full audit on it from the pre-pilot state (clean worktree on `main` or `git stash` + checkout). Save JSON output to `/tmp/equiv-pre.json`.
- [ ] **Step 2:** Run the same audit on the same fixture post-pilot. Save JSON output to `/tmp/equiv-post.json`. Diff: `diff /tmp/equiv-pre.json /tmp/equiv-post.json` — empty. Findings must be identical (rule ids, severities, locations). If different, the per-rule files contain a bug; script logic was untouched, so divergence means content drift.
- [ ] **Step 3:** Run the scanner on `plugins/build/skills/check-bash-script/`. Confirm `LLM_CONTEXT_BUDGET_EXCEEDED` findings on `references/audit-dimensions.md` and `references/repair-playbook.md` are gone (files deleted). Confirm no new findings on the per-rule files (each is well under cap).
- [ ] **Step 4:** Finalize `PILOT-NOTES.md` with: (a) the alignment audit table from Task 1; (b) cross-skill rule duplication observations — which rules in this skill are obviously also present in `check-skill` / `check-python-script` based on rule name and topic (surface impressions, not a rigorous comparison); (c) recompose surprises encountered during Tasks 2–4 (rules where translating audit prose to convention prose was awkward; what the resolution was); (d) explicit recommendations for the rollout sweep (changes to template, ordering hints, gotchas); (e) script-binding inventory for follow-up #407.
- [ ] **Step 5:** Commit: `docs(check-bash-script): record pilot equivalence test and decomposition notes`.

---

## Validation

- [ ] `ls plugins/build/skills/check-bash-script/references/rule-*.md | wc -l` — 40 (32 Tier-1 + 7 Tier-2 + 1 Tier-3).
- [ ] `ls plugins/build/skills/check-bash-script/references/_hub.md` — exists.
- [ ] `ls plugins/build/skills/check-bash-script/references/audit-dimensions.md plugins/build/skills/check-bash-script/references/repair-playbook.md 2>&1 | grep -c 'No such file'` — 2 (both deleted).
- [ ] Every per-rule file under 10K chars: `find plugins/build/skills/check-bash-script/references -name 'rule-*.md' -exec wc -c {} \; | awk '$1 > 10000'` — empty.
- [ ] Frontmatter integrity: `python3 -c "import yaml,glob; [yaml.safe_load(open(p).read().split('---')[1]) for p in glob.glob('plugins/build/skills/check-bash-script/references/*.md')]"` — no parse errors.
- [ ] Every rule file has `name` and `description` non-empty: `python3 -c "import yaml,glob,sys; [sys.exit(f'missing fields: {p}') for p in glob.glob('plugins/build/skills/check-bash-script/references/rule-*.md') if not (lambda fm: fm.get('name') and fm.get('description'))(yaml.safe_load(open(p).read().split('---')[1]))]"`.
- [ ] Every rule file body has `**Why:**` and `**How to apply:**` markers: `for f in plugins/build/skills/check-bash-script/references/rule-*.md; do grep -q '**Why:**' "$f" && grep -q '**How to apply:**' "$f" || echo "MISSING SHAPE: $f"; done` — empty.
- [ ] SKILL.md `references:` array integrity: every enumerated path exists on disk: `python3 -c "import yaml,os,sys; fm=yaml.safe_load(open('plugins/build/skills/check-bash-script/SKILL.md').read().split('---')[1]); [sys.exit(f'missing: {r}') for r in fm['references'] if not os.path.exists(os.path.join('plugins/build/skills/check-bash-script', r))]"`.
- [ ] **Equivalence test** (Task 6 Step 2): pre-pilot and post-pilot audit-run JSON outputs are identical for the fixture artifact.
- [ ] Scanner re-run on `plugins/build/skills/check-bash-script/`: zero `LLM_CONTEXT_BUDGET_EXCEEDED` findings on `references/*`.
- [ ] `git diff --stat main...refactor/check-bash-script-rule-decomposition -- plugins/build/skills/check-skill plugins/build/skills/check-python-script plugins/build/skills/check-rule plugins/wiki/ plugins/work/ plugins/consider/` — empty (only check-bash-script touched).
- [ ] `git log --oneline refactor/check-bash-script-rule-decomposition ^main | wc -l` — between 40 and 50 commits.
- [ ] `PILOT-NOTES.md` exists and contains all five sections (alignment table, duplication observations, recompose notes, rollout recommendations, script-binding inventory).

## Notes

- **Why pilot one skill instead of sweeping all 12.** The convention
  shift is significant — file count grows ~20× and the body shape
  changes (audit prose → convention prose). A single-skill pilot tests
  the convention on a real skill with a real audit script and a real
  artifact-equivalence check, leaving room to revise the template
  before committing 11 more skills.

- **Why `check-bash-script` over alternatives.** It's in the original
  scanner-finding scope (clears 2 oversize findings as side-benefit);
  medium size (~33K combined source); cross-skill rule duplication
  with `check-skill` and `check-python-script` will surface in
  PILOT-NOTES — informs the next architectural decision
  (`_shared/references/` extraction) without acting on it.

- **Substance preservation, not byte preservation, is the discipline.**
  The original `## Detection` + `## Repair` split planned for verbatim
  byte-moves. The unified Claude-rule shape requires recomposing audit
  prose ("Signal X — fix by doing Y") into convention prose ("Do X.
  Why: ... How to apply: ..."). The substance — what to detect, what
  to fix, why it matters — must be preserved exactly. The framing is
  what shifts.

- **Audit-run equivalence is the load-bearing validation.** The
  pilot is wrong if the audit produces different findings before
  and after, because that means a per-rule file got the rule
  semantics wrong (the script logic didn't change). This is the
  test that catches recompose drift.

- **`check-skill` audit will warn on this skill until #407 lands.**
  The audit expects `audit-dimensions.md` and `repair-playbook.md`;
  this skill no longer has them. That warning is expected during the
  pilot window.

- **Stage-2 dispatcher subagent is a separate plan.** The per-rule
  files this pilot creates are the *substrate* for the parameterized
  subagent that takes `(rule_md, artifact)` and returns
  `{rule_id, status, reasoning, recommended_changes}`. With the
  unified shape, the subagent reads the rule body as both rubric (for
  judgment-based rules) and recipe (for finding-localization), with
  invocation context (presence of finding) determining mode. Stage 2
  depends on this pilot landing.

- **RULERS finding lives in the hub, not in any single rule.** The
  guidance "present all judgment dimensions in a single LLM call
  (Hong et al. 2026, RULERS — per-criterion separation scores 11.5pt
  lower)" is cross-rule framing — it belongs in the hub, not
  duplicated across 7 Tier-2 rule files. Whether RULERS applies to
  agentic dispatch (vs. in-prompt criterion separation) is the
  empirical question Stage 2 answers.

- **`paths:` rationale.** Tier-1 and Tier-2 rules use
  `paths: ["**/*.sh", "**/*.bash"]` — they apply when Claude is
  editing any bash script. Tier-3 (cross-entity collision) also uses
  bash globs since the rule is about cross-script analysis triggered
  by editing bash files. No rule omits `paths:` in this pilot; the
  optional-`paths` allowance in the spec applies to other contexts
  (e.g., rules consumed only on-demand by an audit invocation, never
  by ambient editing).

- **Naming convention for script binding (recovered from
  dropped `script:` field).** Rule `name: Strict Mode` (filename
  `rule-strict-mode.md`) corresponds to function `check_strict_mode`
  in `scripts/check_structure.py`. The convention is name-based; the
  scripts already enumerate the checks they implement; PILOT-NOTES
  records the inventory for follow-up #407 to formalize.
