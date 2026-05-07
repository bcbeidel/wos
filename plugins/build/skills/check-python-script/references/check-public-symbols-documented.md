---
name: Public Symbols Documented (library)
description: Public functions, classes, and methods carry docstrings explaining purpose, contract, and edge cases. The docstring is the agent-facing API contract for consumers who will not read the body.
paths:
  - "**/*.py"
---

Library modules document their public symbols with docstrings. The docstring is the agent-facing description a consumer reads before deciding to call the function — it is part of the API surface, not optional decoration.

**Why:** Public symbols without docstrings force consumers to read the body to understand the contract. That is a friction tax paid by every consumer on every reference, and it lets the contract drift silently as the body changes. Source principle: *Document intent at the top.* The docstring is also the source the IDE, the help system, and downstream documentation tools render — silence here means silence everywhere.

**How to apply:** for each top-level function, class, or method whose name does not start with `_`, verify that the first statement of its body is a string literal. The docstring should name what the symbol does, what its parameters mean (when not obvious from naming and type hints), what it returns or raises (when non-trivial), and any preconditions or edge cases the caller must know. One-line docstrings are fine for trivial functions; multi-line for anything with non-obvious behavior. Class docstrings name the invariant the class preserves. Internal helpers (names beginning with `_`) are out of scope.

**Common fail signals (audit guidance):** a public function whose first statement is not a string literal; a public class whose first statement is not a string literal; a one-line docstring on a function with non-trivial behavior, edge cases, or exceptions ("does X" without naming the X-vs-Y distinction); a docstring that only restates the function name (`"""Greet a name."""` on `def greet(name)` adds no information).

**What is NOT a finding:** internal helpers (names beginning with `_`); trivial properties (a property whose getter is `return self._x` is its own documentation); `__init__` methods when the class docstring already names the invariant (constructor docs are optional when they would duplicate the class docstring).
