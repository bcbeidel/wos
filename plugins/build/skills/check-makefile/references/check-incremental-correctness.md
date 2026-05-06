---
name: Incremental Correctness
description: File-producing targets are declared by their output path with real prerequisites; phony names are reserved for verbs; sentinels and order-only prerequisites prevent unnecessary rebuilds.
type: judgment-rule
related:
  - ../SKILL.md
  - ../../../_shared/references/makefile-best-practices.md
---

# Incremental Correctness

Make's whole reason to exist is incremental correctness: rebuild what changed, skip what didn't. A Makefile that declares `build: $(PYTHON) -m build` as `.PHONY` rebuilds every invocation — Make has no idea what file the recipe produced, so it can't decide whether the target is up to date. This dimension judges whether file targets are declared against their outputs, whether expensive idempotent setup is sentinel-gated, and whether directories use order-only prerequisites.

## What to look for

- File-producing targets declared as `.PHONY` (e.g., `build` listed in `.PHONY:` but the recipe writes `dist/*.whl`).
- Expensive idempotent setup (`pip install -r requirements.txt`, `npm ci`, `terraform init`) declared as a regular phony target with no sentinel — reruns on every invocation.
- `mkdir -p $(BUILD_DIR)` as a regular prerequisite (retriggers the dependent target every time the directory mtime changes); should be order-only with `|`.
- Real file targets without prerequisites listed (Make can't know to rebuild when sources change).
- A `.PHONY` annotation missing on actual phony targets (Tier-1 catches the obvious cases; this dimension catches the heuristic gaps).
- Recipes that write to `$@` without `.DELETE_ON_ERROR:` enabled (Tier-1 also checks; this dimension weighs the cost of partial outputs).

## Severity

`warn` — most files run correctly even when incremental rebuilds are broken; the symptom is wasted time, not wrong output. A judge may escalate to `fail` if a `.PHONY` file target is causing observable rebuild loops.

## Example finding

```json
{
  "status": "warn",
  "location": {"line": 31, "context": ".PHONY: setup\\nsetup:\\n\\tpip install -r requirements.txt"},
  "reasoning": "The `setup` target is declared `.PHONY` and runs `pip install` every invocation. Even when requirements.txt hasn't changed, every developer invocation pays the install cost. A sentinel file gates the work behind a single stat.",
  "recommended_changes": "Replace the phony with a sentinel-file target that depends on requirements.txt:\n\n.venv/.installed: requirements.txt\n\tpip install -r requirements.txt\n\ttouch \"$@\"\n\nsetup: .venv/.installed ## Install dev dependencies.\n\nNow `make setup` is a no-op when requirements.txt hasn't changed."
}
```

## Recipe (canonical guidance)

**CHANGE** Declare file-producing targets against their output files. Use a sentinel for expensive idempotent setup. Use order-only prerequisites for directories.

**FROM**
```makefile
.PHONY: build setup

setup:
	pip install -r requirements.txt

build:
	mkdir -p build
	python -m build --outdir build
```

**TO**
```makefile
.PHONY: build

.venv/.installed: requirements.txt
	pip install -r requirements.txt
	touch "$@"

build: | build-dir
	python -m build --outdir build

build-dir:
	mkdir -p build

.PHONY: build-dir
```

**REASON** `.PHONY: setup` makes `pip install` run every time; the sentinel short-circuits to a single `stat`. Order-only `| build-dir` creates the directory once without retriggering `build` on every mtime change.
