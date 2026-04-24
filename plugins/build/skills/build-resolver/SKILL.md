---
name: build-resolver
description: Scaffold a root-level RESOLVER.md — a dual routing table (filing for writes, context for reads) plus an AGENTS.md pointer and a trigger-eval sidecar at `.resolver/evals.yml`. Use when the user wants to "create a resolver", "scaffold RESOLVER.md", "add a routing table for filing and context", or "set up dynamic context routing".
argument-hint: "[repo root path — defaults to CWD]"
user-invocable: true
references:
  - ../../_shared/references/resolver-best-practices.md
  - ../../_shared/references/primitive-routing.md
---

# /build:build-resolver

Scaffold the three linked artifacts that make a resolver work: `RESOLVER.md` at the target repo root with a machine-managed region, a one-line AGENTS.md pointer, and a seeded `.resolver/evals.yml`. The skill is the workflow; authoring principles live in [resolver-best-practices.md](../../_shared/references/resolver-best-practices.md).

## Workflow

### 0. Verify Primitive

A resolver is right when:
- The repo has ≥3 tracked directories with filing conventions (each typically marked by an `_index.md` or consistent naming pattern)
- OR the repo has ≥5 cross-skill reference docs worth bundling into task-based context entries
- AND dynamic context routing isn't already solved by skill-level `references:` alone

Redirect when:
- The repo has one or two directories with trivial conventions → AGENTS.md already suffices
- The user wants skill-dispatch routing (intent → which skill runs) → that's handled by SKILL.md `description`; not a resolver concern
- The user wants per-skill hygiene for `_shared/references/` wiring → separate problem; not this pair

### 1. Detect Existing Resolver

Check `RESOLVER.md` and `.resolver/evals.yml` at the target root. If either exists, switch to regenerate mode:

- Preserve human prose outside `<!-- resolver:begin -->` / `<!-- resolver:end -->` markers
- Preserve existing context-table rows and out-of-scope list
- Rebuild the filing table from a fresh disk scan
- Re-run evals after writing

Announce the mode and what will change before proceeding.

### 2. Scan Target Repo

Walk the repo root and collect:

- **Directories with `_index.md`** — primary filing targets. Read each `_index.md`'s frontmatter `name` and `description`.
- **Directories without `_index.md` but with frontmatter-tagged files** (e.g., `type: research` across files in `.research/`) — secondary filing candidates.
- **Directories that are ambient** (`.git/`, `node_modules/`, `.cache/`, `dist/`, `build/`) — out-of-scope candidates.
- **Shared-reference directories** (any `_shared/references/`) — candidates for context-table bundles.
- **Naming patterns** per filing directory — detect by pattern-matching existing filenames (`YYYY-MM-DD-<slug>.<type>.md` is the common shape).

Report the scan summary: N directories detected, K tagged as filing candidates, M tagged ambient.

### 3. Elicit Filing Table

Present autodetected filing rows as proposed content. For each, show: content type (from `_index.md` description), location (directory), naming pattern. Ask the user to confirm, correct, or extend.

For directories the scan could not classify, ask directly: "`.inbox/` has 4 files with no consistent naming pattern — filing target, or out-of-scope?"

The filing table is the one machine-generated part of the managed region. Capture final decisions per row.

### 4. Elicit Context Table

This is human-provided. Ask:

> "Name up to 5 recurring tasks whose reference-doc set should be bundled. Examples: 'authoring a hook', 'planning research', 'debugging the data pipeline'. For each, list the docs to load first."

Validate that each listed doc path resolves. If not, flag and ask for a correction before writing.

### 5. Seed Trigger Evals

Propose 10–20 eval cases drawn from:
- One positive case per filing row ("save this X" → expected location)
- One positive case per context row ("when doing Y" → expected doc set)
- 2–3 negative cases chosen for overlap risk ("save this X" should NOT go to similar-looking directory Z)

Ask the user to confirm, edit, or add cases. A resolver shipped without evals is a decoration.

### 6. Review Gate

Show the full proposed output:
- `RESOLVER.md` contents (filing + context + out-of-scope inside markers, notes section outside)
- `AGENTS.md` diff (one pointer line; placement proposed based on existing structure)
- `.resolver/evals.yml` contents

Iterate on feedback. Hold the write until the user approves.

### 7. Write

- Create `RESOLVER.md` at the target repo root
- Create `.resolver/evals.yml` (create `.resolver/` if missing)
- Apply the AGENTS.md pointer diff (create AGENTS.md with just the pointer if it doesn't exist; warn that an AGENTS.md with more context is recommended)

Report each file path.

### 8. Hand Off

Offer: "Run `/build:check-resolver` against the new resolver?" Run it on approval. Evals failing on the first run means the seeded expectations don't match the filing/context shape — fix the evals, not the resolver.

## Example

<example>
User: `/build:build-resolver`

Step 2 scan: finds `.research/`, `.plans/`, `.designs/`, `.context/`, `.prompts/`, `plugins/build/_shared/references/`. Detects `_index.md` in four of these. Flags `.raw/` as ambient (no `_index.md`, no frontmatter pattern).

Step 3: proposes 6 filing rows; user confirms 5, drops `.prompts/` as out-of-scope.

Step 4: user names three recurring tasks — "authoring a rule", "authoring a hook", "planning research" — with 2–3 doc paths each.

Step 5: skill proposes 12 eval cases (5 positive filing, 3 positive context, 4 negative); user accepts 10, edits 2.

Step 6 Review Gate: presents all three artifacts. User approves.

Step 7 writes:
- `RESOLVER.md` (42 lines)
- `.resolver/evals.yml` (35 lines)
- `AGENTS.md` — inserts pointer line under existing "Context Navigation"

Step 8: runs `/build:check-resolver`. All Tier-1 checks PASS; two Tier-2 WARN on thin context bundles ("authoring a rule" loads only one doc — consider adding primitive-routing.md). User applies WARN fix via repair loop.
</example>

## Key Instructions

- Run the Step 0 primitive check — redirect if the repo doesn't cross the resolver threshold (≥3 tracked dirs with conventions, or ≥5 cross-skill reference docs)
- Preserve human prose outside managed-region markers on regeneration — the managed region is disk-derived; everything else is author's
- The filing table is generated from the disk scan, not invented — if the scan produces nothing for a directory, ask rather than fabricate
- The context table is human-provided — do not synthesize task→doc bundles from model defaults; the user names recurring tasks
- Trigger evals are non-optional — a resolver without evals is a decoration; hold the write if the user skips seeding
- Hold each write until the Review Gate approval — three files plus an AGENTS.md edit is a large drop to land silently

## Anti-Pattern Guards

1. **Scaffolding without a disk scan.** The filing table must reflect observable reality; never accept a hand-provided filing list without grounding in directory presence.
2. **Skipping the AGENTS.md pointer.** The resolver is unreachable without it. Refuse to write `RESOLVER.md` alone when AGENTS.md exists and the pointer hasn't been approved.
3. **Synthesizing context entries from model defaults.** Context bundles are repo-specific; the user must name the recurring tasks and confirm the doc set. Manufactured entries rot on the first regeneration.
4. **Writing with zero eval cases.** Even 5 eval cases are better than 0; refuse to write `.resolver/evals.yml` empty.
5. **Overwriting existing human prose.** On regenerate mode, verify the managed-region markers exist and that only the region between them changes. Abort if the file exists but markers are missing — ask the user to reconcile.

## Handoff

**Receives:** Target repo root (defaults to CWD).
**Produces:** `RESOLVER.md` at root, `.resolver/evals.yml`, and an AGENTS.md pointer line (appended or created).
**Chainable to:** `/build:check-resolver` (audits the three artifacts; runs evals; flags dark capabilities).
