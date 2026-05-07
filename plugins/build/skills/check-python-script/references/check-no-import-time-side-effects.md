---
name: No Import-Time Side Effects (library)
description: Library modules perform no work at import time other than imports, type aliases, `__all__`, and pure-RHS constant assignments. Side effects at module scope make the module hostile to import for testing, partial introspection, and reuse.
paths:
  - "**/*.py"
---

Library modules — files imported, not invoked — must execute no work at import time. The Tier-1 `library-no-side-effects` rule catches obvious cases (top-level statements outside `def`/`class`/`import`/`AnnAssign`/`Assign`/`if TYPE_CHECKING:` block); this dimension carries the judgment for nuance the regex/AST cannot resolve.

**Why:** A module that does work at import time imposes that work on every consumer that imports it — even those that only need a single symbol. It also fights testability (you can't `import` to introspect without paying the cost), couples module load order to runtime correctness, and creates difficult-to-debug surprises (`ImportError`s caused by unrelated startup code). Source principle: *Keep the module scope disciplined.* Constants, imports, type aliases, and `__all__` are fine; everything else belongs inside a function.

**How to apply:** read the top-level statements of the module. Each one should be: an import, a `def`, a `class`, a constant assignment with a literal RHS, an `__all__` declaration, a type alias (e.g., `Foo: TypeAlias = int`), the module docstring, or a `if TYPE_CHECKING:` block guarding type-only imports. Anything else — a function call at module scope, a `for`/`while`/`try` block, a non-trivial expression evaluated at top level — is import-time work and is a finding. Pay particular attention to "configuration" idioms (`logging.basicConfig(...)` at module scope, `os.environ[...] = ...` at module scope) — these are the most common offenders and the most insidious.

**Common fail signals (audit guidance):** `logging.basicConfig(...)` or similar configuration call at module scope; `print(...)` or other I/O at module scope; `os.environ[...] = ...` or other env-var mutation at module scope; a top-level `try/except` block doing real work (e.g., loading a config file with a fallback); a `for` loop populating a module-level constant from a runtime source.

**What is NOT a finding:** module docstring (always allowed); imports including conditional imports under `if TYPE_CHECKING:`; `__all__` declaration; type aliases via `AnnAssign` (`Foo: TypeAlias = int`); module-level constants with literal RHS (`MAX_RETRIES = 3`).
