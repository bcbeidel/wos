---
name: Mechanical-Work Partition
description: Mechanical substeps (file existence, regex match, count, schema validity, fixed-list lookup, exit-code branching) must invoke a sibling script rather than ask the LLM to re-derive the check on every invocation.
paths:
  - "**/SKILL.md"
---

Partition mechanical work from judgment — extract deterministic substeps to sibling scripts under `scripts/` and have the SKILL.md invoke them, with the LLM reasoning over the script's output (text, JSON, exit code).

**Why:** Mechanical work in prose is slower per invocation, less reliable run-to-run, and pays the token cost every call. Asking the LLM to "verify the file exists at `<path>`" or "count the entries in the registry" is asking it to re-derive a deterministic check on every invocation — a check that would cost ~1ms in a script and produce identical output every time. The toolkit's own `check-*` skills follow this partition: Tier-1 deterministic scripts feed Tier-2 LLM judgment. Skills that fuse the two waste budget on substeps the model is statistically worse at than a 5-line Python.

**How to apply:** Identify mechanical substeps — file existence, regex match, count, schema validity, fixed-list lookup, exit-code branching. Extract each to a script under `scripts/` and have the SKILL.md invoke it. The LLM reads the script's output and reasons over it. Keep judgment substeps (does this read well, is the scope right) inline.

```markdown
## Steps
1. Run `python scripts/audit_frontmatter.py references/` — emits one JSON object per file with `path`, `name`, `version_ok`, `description_len`, and `failures: []`.
2. Read the script's output. For each entry with non-empty `failures`, decide whether the failure is repair-now or repair-later based on severity, then report the partition to the user.
```

**Common fail signals (audit guidance):**
- A step instructs the LLM to perform a check that is purely mechanical: "Verify the file exists", "Count the occurrences of X", "Validate the YAML matches schema Y", "Check whether all entries appear in the registered list" — with no sibling script invoked
- A step asks the LLM to parse, extract, or compare structured data the script could feed it as already-parsed output
- The skill bundles no `scripts/` sibling but contains multiple mechanical-shaped steps
- The skill describes pattern-matching against a fixed regex, fixed list, or known schema as if it were judgment

**Exception:** Judgment-only skills (rubric application, scope decisions, narrative writing) return PASS with verdict N/A — no extraction applies. A single trivial inline check whose script would add maintenance burden disproportionate to the cost can stay inline if the skill acknowledges the choice with a one-line reason.
