---
name: Audit Dimensions — Required Fields
description: Each dimension entry in `audit-dimensions.md` should carry six fields — name, what, pass, fail, severity, principles-doc section. Detection requires reading the prose; LLM judgment is the only effective check.
paths:
  - "**/audit-dimensions.md"
---

Each dimension entry in `audit-dimensions.md` should carry six fields — *name*, *what it checks*, *pass criteria*, *fail criteria*, *severity*, and a *principles-doc section reference*.

**Why:** the dimensions doc is the scoreable rubric the audit half evaluates against. Missing fields produce ambiguous findings — a dimension with no *severity* leaves the audit guessing whether to fail or warn; a dimension with no *principles-doc section* leaves the user unable to look up *why* the rule exists. Mechanically detecting field presence works for labeled forms (`**Pass:**`, `**Severity:**`) but breaks down on inferred forms ("Passes when…", "Severity is fail because…") that authors use to keep the prose readable. Detection requires reading each dimension's prose and judging whether each of the six concepts is expressed at all — labeled, inferred, or neither.

**How to apply:** for each dimension entry (H3 heading) in `audit-dimensions.md`:

1. Read the entry's prose. Identify whether each of the six fields appears, in either labeled form (`**Pass:**`) or inferred form (a sentence like "Passes when…", "The check fails when…").
2. Count missing fields. The six are: *name* (the H3 heading itself counts), *what it checks*, *pass criteria*, *fail criteria*, *severity*, and a *principles-doc section reference* (any pointer to a section of `<primitive>-best-practices.md`).
3. If three or more fields are missing in any dimension, surface as `warn`. Two or fewer missing is acceptable — partial dimensions are often intentional mid-refactor states.
4. The fix is structural — the user fills in the missing fields from the principles doc, or routes to `/build:build-skill-pair <primitive>` if three or more are missing (the Draft step rebuilds the rubric).

```markdown
# Acceptable (labeled form):

### my-dimension

**What it checks:** ...
**Pass:** ...
**Fail:** ...
**Severity:** warn.
**Principles section:** *Anatomy*.

# Acceptable (inferred form):

### my-dimension

This dimension verifies that the foo bar matches the baz pattern in the
principles doc's *Anatomy* section. Passes when the pattern is present;
fails when it is missing or misshapen — severity is warn because the
pair still works, just drifts.

# Failing (3+ missing):

### my-dimension

Checks that the foo bar exists.
```

**Common fail signals (audit guidance):**

- A dimension's prose is one or two sentences with no *Pass* / *Fail* / *Severity* mentions, labeled or inferred.
- A dimension references a principles-doc section that does not exist in the principles doc (the H2 headings differ).
- A dimension's *Severity* is omitted or contradicts the description (e.g., describes a hard breakage but is rated `warn`).
- A new dimension was added under a tier heading without filling in any of the field structure.

**Exception:** an introductory paragraph or a tier-divider paragraph that is not itself a dimension entry should be skipped — only H3 dimension entries are graded. The judgment is structural; if the prose reads as introductory matter, exclude it from the field-count.
