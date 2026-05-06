---
name: Documentation Intent
description: A header comment names the project and requirements; every public target carries a `## description`; inline comments explain why a non-obvious choice was made, not what the recipe does.
type: judgment-rule
related:
  - ../SKILL.md
  - ../../../_shared/references/makefile-best-practices.md
---

# Documentation Intent

A Makefile's documentation has three layers: the header (project + requirements), the per-target `##` descriptions (consumed by `make help`), and inline comments (rationale for non-obvious choices). This dimension judges whether each layer is present and whether the inline comments restate code (`# run tests` above `pytest`) or actually explain why a choice was made (`# || true: $(BUILD_DIR) may not exist on a clean checkout`).

## What to look for

- No header comment in the first ~5 lines naming the project and requirements (GNU Make ≥ 4.0, bash, any non-obvious tool dependency).
- A public target without a `## description` suffix — invisible to `make help`.
- A `## description` that restates the target name (`test: ## Run test`) instead of saying what the test surface covers.
- Inline `# run tests` above `pytest` (what restated, no new information).
- A non-obvious choice with no rationale comment: a `CONFIRM=1` gate, a `# deferred:` annotation on a bare `=`, a sentinel-file path, an `|| true` suppression.
- Stale documentation — a `## description` that promises behavior the recipe no longer does.

## Severity

`warn` — documentation gaps are coaching. The Makefile runs; readers just have to read code to figure out intent.

## Example finding

```json
{
  "status": "warn",
  "location": {"line": 12, "context": "# Run tests\\ntest:\\n\\tpytest"},
  "reasoning": "The comment `# Run tests` above the recipe restates what the recipe does — no new information for the reader. And the target lacks a `## description` suffix, so it's invisible to `make help`. The right place for the description is on the target line; the right content for an inline comment is the *why*, not the *what*.",
  "recommended_changes": "Move the description to the target line as `##` (consumed by `make help`); drop the what-comment. Reserve inline comments for non-obvious rationale:\n\ntest: ## Run the test suite (matches CI).\n\t$(PYTHON) -m pytest\n\nIf the file lacks a header, add one in the first ~5 lines:\n\n# repo-name — developer workflow orchestration.\n# Requires: GNU Make >= 4.0, bash."
}
```

## Recipe (canonical guidance)

**CHANGE** Add header comment; add `##` to every public target; remove what-comments; annotate non-obvious choices.

**FROM**
```makefile
# Run tests
test:
	pytest
```

**TO**
```makefile
# repo-name — developer workflow orchestration.
# Requires: GNU Make ≥ 4.0, bash.

...

test: ## Run the test suite.
	$(PYTHON) -m pytest
```

**REASON** `## description` feeds `make help`; the what-comment restates the recipe. Header names the environment requirements so a contributor with an ancient `make` fails fast instead of running into mysterious parse errors. Inline comments earn their place by explaining rationale.
