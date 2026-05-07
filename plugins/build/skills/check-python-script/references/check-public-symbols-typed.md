---
name: Public Symbols Typed (library)
description: Public functions and class methods declare type hints on parameters and return types. Type hints are documentation that does not drift, enable static analysis downstream, and make IDE introspection useful.
paths:
  - "**/*.py"
---

Library modules expose a public API surface. The functions, classes, and methods on that surface that callers will use must declare type hints — on parameters and on return types. Internal helpers (names beginning with `_`) are out of scope; the public surface is the contract.

**Why:** Type hints are documentation that the runtime (and static analyzers) can verify. Without them, a public function's signature is opaque to callers — they read the body to figure out what it accepts. Source principle: *Dress the style — add type hints to function signatures.* Type hints are also the lowest-friction interface for static checking (`mypy`, `pyright`, IDE introspection) — without them, downstream consumers can't reason about the library mechanically.

**How to apply:** for each top-level function, class, or method whose name does not start with `_`, verify that its parameters and return type are annotated. `def greet(name)` is a finding; `def greet(name: str) -> str:` is not. For class methods, `self` and `cls` do not require annotations; other parameters do. Generic types (`list[str]`, `Iterable[Path]`, `dict[str, int]`) are preferred over bare `list`, `Iterable`, `dict`. Use `from __future__ import annotations` to enable forward-references and avoid circular-import noise.

**Common fail signals (audit guidance):** a public function without parameter annotations; a public function without a return-type annotation (use `-> None` for procedures); a public class method using `Any` to dodge the annotation work; bare `list`/`dict`/`tuple` without parametric types; a public function whose only annotation is on `self`.

**What is NOT a finding:** internal helpers (names beginning with `_`); `self` and `cls` parameters; `*args, **kwargs` in subclassing/decoration scenarios where the signature is intentionally permissive (cite the reason).
