---
name: Recipe Hygiene
description: Recipes use literal-make idioms, `@`-discipline, `|| true` only when annotated, multi-step shell joined with `\` continuations, and stay short enough to read.
type: judgment-rule
related:
  - ../SKILL.md
  - ../../../_shared/references/makefile-best-practices.md
---

# Recipe Hygiene

Each recipe line runs in a fresh shell. That single fact governs nearly every recipe-hygiene decision: a `cd` on line 1 has no effect on line 2; a `$foo` is Make-expanded unless escaped to `$$foo`; multi-step shell needs `\` continuations or it silently does the wrong thing. This dimension judges whether recipes read as legitimate glue or as inline programs that should have moved to `scripts/`.

## What to look for

- Multi-step shell operations across separate physical recipe lines (each runs in a fresh shell — the `cd`, the `for` loop variable, the `if` state are all lost).
- `$foo` in a recipe that meant `$$foo` (shell variable) — Make is expanding what should be shell.
- `$(VAR)` unquoted in a path expansion where the value could contain spaces or be empty.
- Bare `make` in a recipe instead of `$(MAKE)` (loses `-j`, `-s`, `MAKEFLAGS`).
- `@` on commands other than `echo`, `printf`, or `:` (hides the failing command from the user).
- `|| true` without an adjacent comment explaining why failure is acceptable.
- Recipes longer than ~10 lines doing inline scripting that should be in `scripts/<name>.sh`.

## Severity

`warn` — these are coaching findings. A recipe that silently does the wrong thing (lost `cd`, unescaped `$`) is a real bug, but the audit surfaces it as a learnable pattern, not a blocker.

## Example finding

```json
{
  "status": "warn",
  "location": {"line": 64, "context": "release:\\n\\tcd dist\\n\\tfor f in *.whl; do echo \"$f\"; done"},
  "reasoning": "Each recipe line runs in a fresh shell. The `cd dist` on line 1 has no effect on the `for` loop on line 2 — the loop runs in the original directory. And `$f` is Make-expanding to empty; the shell variable needs `$$f`. The recipe silently does the wrong thing.",
  "recommended_changes": "Join the steps with `\\` continuations and escape the shell variable:\n\nrelease:\n\tcd dist && \\\n\tfor f in *.whl; do \\\n\t  echo \"$$f\"; \\\n\tdone\n\nFor anything beyond two or three lines, prefer moving the logic to scripts/release.sh and invoking it as a single recipe line."
}
```

## Recipe (canonical guidance)

**CHANGE** Join multi-step shell operations with `\` continuations, or extract to a `scripts/` file. Use `$$` for shell-variable escapes.

**FROM**
```makefile
release:
	cd dist
	for f in *.whl; do
	  echo "$f"
	done
```
*(each line runs in a fresh shell — the `cd` is lost, `$f` is Make-expanded)*

**TO**
```makefile
release:
	cd dist && \
	for f in *.whl; do \
	  echo "$$f"; \
	done
```
*(or move the body to `scripts/release.sh`, preferred for anything non-trivial)*

**REASON** Each recipe line is a fresh shell. Without `\` continuations, `cd` on line 1 has no effect on line 2. `$$` escapes a literal `$` past Make's expansion so the shell sees `$f`.
