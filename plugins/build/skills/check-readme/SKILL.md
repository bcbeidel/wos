---
name: check-readme
description: >
  Audits a project's top-level README.md against 28 deterministic
  checks across seven scripts (secret scanning, H1 uniqueness &
  position, heading-hierarchy skips, section presence & order, TOC
  threshold, line count & length, code-block language tags,
  shell-prompt prefixes, smart quotes in code, relative-link
  resolution, fragment-anchor resolution, image alt text,
  badge/image byte size, destructive-command flagging, pipe-to-shell
  patterns, TLS-disable instructions, non-reserved hostnames/IPs,
  emoji in headings, LICENSE file presence & link, CONTRIBUTING
  link, TODO/FIXME/XXX markers, README gitignore status) plus
  seven judgment dimensions and a Tier-3 cross-README collision
  check. Use when the user wants to "audit a README", "lint a
  README", or "run linters on README.md". Not for sub-package
  READMEs (different rubric) or docs-site pages (different
  toolchain).
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
argument-hint: "[path]"
user-invocable: true
references:
  - ../../_shared/references/readme-best-practices.md
  - references/check-collision.md
  - references/check-installation-correctness.md
  - references/check-maintenance-posture.md
  - references/check-opening-clarity.md
  - references/check-placeholder-discipline.md
  - references/check-quickstart-effectiveness.md
  - references/check-style-and-voice.md
  - references/check-warning-prominence.md
license: MIT
---

# Check README

Audit a project's top-level README.md for structural soundness, safety, prose quality, and freshness. The rubric — what makes a README load-bearing in the top 30 seconds — lives in [readme-best-practices.md](../../_shared/references/readme-best-practices.md).

This skill follows the [check-skill pattern](../../_shared/references/check-skill-pattern.md). Tier-1 detection is in 7 scripts emitting JSON envelopes via `_common.py` (28 rule_ids total). Tier-2 has 7 judgment dimensions read inline by the primary agent. Tier-3 is `collision` (cross-README duplication, judgment-driven).

## When to use

Also fires when the user phrases the request as:

- "check this README"
- "review my README"
- "is this README any good"
- "what's wrong with the README"

## Workflow

### 1. Scope

Read `$ARGUMENTS`:

- **Single path to a README.md** — audit that file.
- **Directory path** — find the top-level README.md (case-insensitive: README.md, Readme.md).
- **Empty** — refuse and explain.

Refuse on sub-package READMEs (under `packages/*/README.md`) — different rubric. Confirm scope aloud.

### 2. Tier-1 Deterministic Checks

Invoke 7 detection scripts:

```bash
SCRIPTS="${SKILL_DIR}/scripts"
TARGETS="$ARGUMENTS"

python3 "$SCRIPTS/check_secrets.py"      $TARGETS   # 1 rule:  secret (FAIL)
python3 "$SCRIPTS/check_structure.py"    $TARGETS   # 7 rules: h1-present (FAIL), heading-hierarchy, section-coverage, section-order, toc-threshold, size, prose-line-length
python3 "$SCRIPTS/check_codeblocks.py"   $TARGETS   # 4 rules: fence-language, shell-prompt, smart-quotes, code-line-length (all WARN)
python3 "$SCRIPTS/check_links.py"        $TARGETS   # 3 rules: broken-relative (FAIL), broken-anchor, broken-external
python3 "$SCRIPTS/check_images.py"       $TARGETS   # 3 rules: alt-text, image-size, badge-overload (all WARN)
python3 "$SCRIPTS/check_safety.py"       $TARGETS   # 5 rules: destructive (FAIL), pipe-to-shell (FAIL), tls-disable (FAIL), non-reserved-hosts (FAIL), emoji-headings
python3 "$SCRIPTS/check_completeness.py" $TARGETS   # 5 rules: license-file (FAIL), license-link, contributing-link, todo-markers, readme-gitignored
```

Each script emits a JSON array of envelopes. `recommended_changes` is canonical — copy through verbatim.

**Script-to-rules map** (28 Tier-1 rule_ids):

| Script | rule_ids | Severity |
|---|---|---|
| `check_secrets.py` | `secret` | fail |
| `check_structure.py` | `h1-present` | fail |
| `check_structure.py` | `heading-hierarchy`, `section-coverage`, `section-order`, `toc-threshold`, `size`, `prose-line-length` | warn |
| `check_codeblocks.py` | `fence-language`, `shell-prompt`, `smart-quotes`, `code-line-length` | warn |
| `check_links.py` | `broken-relative` | fail |
| `check_links.py` | `broken-anchor`, `broken-external` | warn |
| `check_images.py` | `alt-text`, `image-size`, `badge-overload` | warn |
| `check_safety.py` | `destructive`, `pipe-to-shell`, `tls-disable`, `non-reserved-hosts` | fail |
| `check_safety.py` | `emoji-headings` | warn |
| `check_completeness.py` | `license-file` | fail |
| `check_completeness.py` | `license-link`, `contributing-link`, `todo-markers`, `readme-gitignored` | warn |

**Tier-2 exclusion list.** Any FAIL in `secret`, `h1-present`, `broken-relative`, `destructive`, `pipe-to-shell`, `tls-disable`, `non-reserved-hosts`, or `license-file` excludes the README from Tier-2.

**Missing-tool degradation.** `check_links.py` requires `lychee` or `markdown-link-check` for the `broken-external` rule; when neither is installed, that envelope emits `overall_status: inapplicable` (other rule_ids continue).

### 3. Tier-2 Judgment Dimensions

For each README that passed the Tier-2 exclusion gate, evaluate against the **7 judgment rules** at `references/check-*.md`:

| File | Dimension | Severity |
|---|---|---|
| [check-opening-clarity.md](references/check-opening-clarity.md) | D1 — H1 + one-sentence problem statement orient in 5 seconds | warn |
| [check-installation-correctness.md](references/check-installation-correctness.md) | D2 — install steps are copy-pasteable and complete | warn |
| [check-quickstart-effectiveness.md](references/check-quickstart-effectiveness.md) | D3 — quickstart produces a runnable artifact in <10 minutes | warn |
| [check-placeholder-discipline.md](references/check-placeholder-discipline.md) | D4 — every `<placeholder>` is justified, not copy-paste padding | warn |
| [check-warning-prominence.md](references/check-warning-prominence.md) | D5 — destructive ops carry visible warnings | warn |
| [check-maintenance-posture.md](references/check-maintenance-posture.md) | D6 — README freshness signals (last-updated, contributor links) | warn |
| [check-style-and-voice.md](references/check-style-and-voice.md) | D7 — direct, plain English; no marketing prose | warn |

#### Evaluator policy

- **Single locked-rubric pass per README.** Read all 7 rule files first, then evaluate the README in one LLM call against the unified rubric. A single locked-rubric pass produces stable scoring.
- **Default-closed when borderline.** When evidence is ambiguous, return `warn`, not `pass`.
- **Severity floor: WARN.** All 7 Tier-2 dimensions are coaching, not blocking.
- **One finding per dimension maximum.** Surface the highest-signal location.

### 4. Tier-3 Cross-README Collision

Evaluate against [check-collision.md](references/check-collision.md). For multi-README scope (org-wide audits, monorepos), surface duplicate Installation / Contributing / License prose across sibling READMEs as `warn`. Single-README scope returns `inapplicable`.

### 5. Report

Merge Tier-1 (script JSON) + Tier-2 (judgment) + Tier-3 (collision) findings into a unified table:

```
| Tier | rule_id | Location | Status | Reasoning |
|------|---------|----------|--------|-----------|
```

Sort: `fail` before `warn` before `inapplicable`; Tier-1 before Tier-2 before Tier-3 within severity. Each `Recommendation:` line copies through `recommended_changes` verbatim.

### 6. Opt-In Repair Loop

Ask exactly once:

> "Apply fixes? Enter y (all), n (skip), or comma-separated numbers."

For each selected finding:

- **Direct edit** — H1 insertion, missing-section addition, code fence language tag, anchor correction. Show diff; write on confirmation.
- **Routed to another skill** — substantial rewrites → `/build:build-readme`.
- **Tier-2/3 judgment** — ask the user; rewrite the section; show diff; write on confirmation.

After each applied fix, re-run the relevant Tier-1 script. Terminate when the user enters `n` or exhausts findings.

## Anti-Pattern Guards

1. **Per-dimension LLM call.** Collapse into one locked-rubric call per README.
2. **LLM-evaluating format compliance.** Frontmatter shape, link resolution, line length — handle deterministically in Tier-1.
3. **Ambiguous compliance reported as PASS.** Surface as WARN (default-closed).
4. **Vague finding text.** Cite the specific README and exact phrasing.
5. **Bulk-applying fixes.** Per-finding confirmation required.
6. **Re-evaluating scripted rules in Tier-2.** Scripts are authoritative for the 28 Tier-1 rules.
7. **Suppressing the inapplicable envelope.** When `lychee`/`markdown-link-check` is absent, the `broken-external` envelope emits `inapplicable` — surface it.
8. **Embellishing scripts' `recommended_changes`.** Each rule's recipe constant is canonical guidance from `readme-best-practices.md`.

## Key Instructions

- Run Tier-1 deterministic checks first; gate LLM evaluation on structural validity.
- Present all 7 Tier-2 dimensions as a single locked-rubric call per README.
- Include the full README verbatim in every LLM evaluation.
- Tier-3 collision only fires on multi-README scope; single-README scope returns `inapplicable`.
- Recovery: read-only outside the Repair Loop.

## Handoff

**Receives:** Path to a README.md or a directory containing one (top-level only).

**Produces:** A unified findings table merging the 28 Tier-1 envelopes (script JSON), 7 Tier-2 judgment findings per README, and the Tier-3 cross-README collision findings (multi-scope only). Each row: tier, rule_id, location, status, reasoning + `recommended_changes` excerpt. Optionally — per user confirmation in the Repair Loop — targeted edits to README.md.

**Chainable to:** `/build:build-readme` (rebuild non-compliant README from scratch).
