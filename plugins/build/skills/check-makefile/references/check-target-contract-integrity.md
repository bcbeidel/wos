---
name: Target Contract Integrity
description: Every public target's recipe matches the work its name promises; phony targets really are phony; the canonical workflow verbs (test, lint, ci) exist where the repo has the workflow.
type: judgment-rule
related:
  - ../SKILL.md
  - ../../../_shared/references/makefile-best-practices.md
---

# Target Contract Integrity

A Makefile's public target list is a contract: `make test` runs tests, `make ci` runs what CI runs, `make deploy` deploys. When the recipe drifts from the name, or when canonical verbs are missing in a repo that has the workflow, the contract breaks silently and the Makefile stops being a reliable index of the project.

## What to look for

- A `ci` target that re-invokes `pytest` and `ruff` directly instead of calling `$(MAKE) lint test` (CI drifts from local).
- Aspirational verbs declared but empty or stubbed (`deploy:` with a `TODO` recipe).
- Missing canonical verbs the repo clearly has (a `tests/` directory and `pytest.ini` but no `test` target; a `Dockerfile` but no `build` target).
- Inconsistent verb pairs (`lint` and `lint-py` vs `lint` and `pylint` — pick one convention).
- A `.PHONY` target that produces a real file as a side effect, or a file target that is actually phony.

## Severity

`warn` — coaching the surface area, not blocking. The Makefile parses and runs; the contract is just frayed.

## Example finding

```json
{
  "status": "warn",
  "location": {"line": 42, "context": "ci: ; pytest && ruff check ."},
  "reasoning": "The `ci` target invokes pytest and ruff directly instead of `$(MAKE) test lint`. This is the failure mode the Makefile exists to prevent — CI drifts from the targets a developer runs locally.",
  "recommended_changes": "Replace the direct invocations with target prerequisites:\n\nci: lint test ## Run the same checks CI runs.\n\nThis enforces 'one graph, two callers' — local and CI walk the same dependency tree."
}
```

## Recipe (canonical guidance)

**CHANGE** Align the target surface with the repo's actual workflows. Add missing canonical verbs (`ci` almost always, `test` when tests exist). Remove or stub aspirational verbs that don't do their job.

**FROM** `ci:` that re-runs `pytest` and `ruff` directly.
**TO** `ci: lint test` — reuse the same targets the developer runs.

**REASON** CI drifting from local is the failure mode the Makefile is supposed to prevent. Reusing targets enforces the "one graph, two callers" contract.
