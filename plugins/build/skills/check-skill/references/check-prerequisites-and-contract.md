---
name: Prerequisites and Contract
description: `## Prerequisites` must enumerate every tool, env var, privilege tier, and I/O shape the skill depends on — no placeholders, no implicit contracts.
paths:
  - "**/SKILL.md"
---

State preconditions once and declare inputs, outputs, and their shapes — every dependency referenced in Steps appears in Prerequisites, with versions, env vars, privilege tier (when elevated), and concrete I/O formats.

**Why:** Implicit contracts force the agent to guess at runtime. A skill that references `$AWS_PROFILE` in Steps but doesn't declare it in Prerequisites will silently fail or run with the wrong identity; a skill that produces "a Parquet file" without naming its location, schema source, or column types forces every consumer to re-derive the contract from the body. Skills mutating elevated systems without naming their privilege tier let the agent run them under whatever credentials happen to be loaded — a quiet path to production incidents. Explicit contracts make the skill callable without reading the body.

**How to apply:** Enumerate tools with versions, env vars with their semantic role, the privilege tier (for elevated skills), and input/output shapes (types, formats, locations). Cross-check against Steps — every named dependency must appear here. Replace generic items ("requires a terminal") with the actual stack the skill uses.

```markdown
## Prerequisites
- `pandas >= 2.0`, `pyarrow >= 14.0`
- Env var `AWS_PROFILE` set to a profile with `s3:PutObject` on the target bucket
- Input: path to a `.csv` file (first row is header)
- Output: a `.parquet` file at `<input>.parquet` with inferred schema
```

**Common fail signals (audit guidance):**
- Section exists but lists only generic items ("requires a terminal", "requires git")
- Skill references env vars or tools in Steps that are not declared in Prerequisites
- Skill mutates persistent state or affects elevated systems but does not declare the privilege tier or IAM/RBAC roles
- Input/output shapes are implicit — the skill reads a file or produces an artifact without naming its format
