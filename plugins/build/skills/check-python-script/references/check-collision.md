---
name: Cross-Entity Collision
description: When the audit scope holds multiple Python scripts in the same directory, surface near-identical scaffolding (parsers, error handlers, docstrings) that wants a shared helper module.
paths:
  - "**/*.py"
---

When the audit scope holds multiple Python scripts in the same directory, surface near-identical `get_parser()` / error-handler / docstring patterns that the maintainer could lift into a shared helper module.

**Why:** Duplicated scaffolding is the early signal that a collection of scripts wants a real package. Shared parsing logic maintained in triplicate drifts: an `--out` flag added to one script gets a different default in the other two; a common error handler updated in one place keeps the old behavior elsewhere. A single source of truth keeps the arguments coherent and documents the shared conventions in one place.
**How to apply:** scan the directory for repeated scaffolding — argparse setup, exception-handling try/except blocks, common docstring shapes, shared constants. If three or more scripts carry near-identical blocks, propose extracting the shared piece into `<dir>/_helpers.py` (or a package) and importing from it. If the scripts are truly independent and unlikely to co-evolve, accept the duplication — DRY applies to code that will change together, not code that happens to look alike.

```python
# _helpers.py
def make_base_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--dry-run", action="store_true", help="Preview changes.")
    return parser
```

**Common fail signals (audit guidance):** `get_parser()` copied across three scripts with script-specific tweaks to each; the same try/except block with the same error message in multiple scripts; identical module docstring boilerplate across siblings.
