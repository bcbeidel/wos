---
name: "--as-tool Scaffolding Recipe"
description: Template build-skill uses when `skill-invocable: true` is opted in during Interview. Documents what to generate for frontmatter, skill intro, workflow split, contract section, and Key Instructions. Paired with the shared authoritative spec at ../../_shared/references/as-tool-contract.md.
---

# `--as-tool` Scaffolding Recipe

This reference is loaded by `/build:build-skill` only when the user answered **yes** to the "should this skill be invocable by other skills via `--as-tool`?" intake question. It describes what the scaffolded SKILL.md must contain to conform to the shared contract at `../../_shared/references/as-tool-contract.md`.

For the authoritative mechanism (parsing rule, envelope shapes, emission rules), always consult the shared contract. This file is a **scaffolding checklist**, not the spec.

## Frontmatter additions

When opting in, generate the following on top of the standard frontmatter:

- `skill-invocable: true`
- Add `../../_shared/references/as-tool-contract.md` to the `references:` list.

If the author chose **DATA** return shape, no further frontmatter is needed. If **ARTIFACT**, the intake captured the artifact-type list — use it in the Contract section below; no frontmatter impact.

## Skill intro paragraph

Near the top of the body (right after the H1 or the one-line purpose), add a short "Two invocation modes" paragraph:

> Two invocation modes:
> - **Human** — prompts for missing info, shows the result, asks for approval.
> - **`--as-tool`** — structured emission per the shared contract. No prompts, no approval.

Exact wording can vary; the paragraph must name both modes and signal that the `--as-tool` mode emits structured output.

## Workflow split

The final user-facing step of the skill's Workflow branches into two sub-steps keyed on mode:

- **`§Xa. Human mode`** — present the result, ask for approval, save if applicable.
- **`§Xb. --as-tool mode`** — emit the structured return. The emission prose depends on the Return shape:

  - **DATA:** "Output **only** a JSON block — no prose, no preamble. One of three envelope shapes: `Success` with a `value` object, `NeedsMoreInfo` with `missing` + `hint`, or `Refusal` with `reason` + `category`."
  - **ARTIFACT:** "Output a JSON envelope followed by one or more fenced code blocks. The envelope declares `artifact_types` in the order the fenced blocks appear. Language tag per MIME: `text/x-shellscript` → ` ```bash `, `application/json` → ` ```json `, `text/markdown` → ` ```markdown `, etc. `NeedsMoreInfo` and `Refusal` are JSON-only (no fenced blocks) regardless of shape."

## `## --as-tool contract` section — mandatory

Every opted-in SKILL.md must include this H2 section. Populate from the Interview answers. Subsections (in this order):

- **`**Required fields:**`** — list each named field a caller must pre-fill (e.g., `name`, `path`, `target-shell`) with a one-line description. Use `none` if the skill takes no args under `--as-tool`.
- **`**Return shape:** DATA`** _or_ **`**Return shape:** ARTIFACT`** — the declared shape.
- For ARTIFACT only: **`**Artifact types:**`** — comma-separated MIME types in the order fenced blocks will appear (e.g., `text/x-shellscript, application/json`).
- Three bullets for the envelope cases. For each of `Success`, `NeedsMoreInfo`, `Refusal`, describe what its envelope carries:
  - DATA `Success` — schema of `value`.
  - ARTIFACT `Success` — metadata shape and which fenced block plays which role.
  - `NeedsMoreInfo` — always JSON only: `missing: [...]`, `hint: "..."`.
  - `Refusal` — always JSON only: `reason`, `category` (enumerate the category values the skill uses).
- **`**Side effects:**`** — list the files read, commands run, or other `--as-tool` skills invoked. Use `none` if the skill is pure.
- **`**Parallel-safe:**`** — `yes` (default) or `no — <reason>` (e.g., "no — acquires exclusive lock on `/tmp/x`").

## Key Instructions additions

Generate three entries under the existing `## Key Instructions` section (create the section if the scaffolded skill doesn't already have one):

- "Under `--as-tool`: emit per the contract (DATA: JSON only; ARTIFACT: JSON envelope + fenced blocks in declared order). No prose, no `input()`, no approval."
- "Under `--as-tool`: hard-fail with `NeedsMoreInfo` when any required field is missing. Do not prompt — the caller will retry."
- "`NeedsMoreInfo` and `Refusal` emit JSON only, regardless of return shape. Fenced blocks are never emitted on failure paths."

## Canonical examples

- **DATA:** `plugins/dummy/skills/greet/SKILL.md` — a minimal DATA-shape skill. Read it when in doubt.
- **ARTIFACT:** no canonical example exists yet; one will land with the hook/shell refactor (#327). Until then, refer to the ARTIFACT emission examples in `../../_shared/references/as-tool-contract.md`.
