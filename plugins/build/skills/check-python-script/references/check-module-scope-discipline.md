---
name: Module-Scope Discipline
description: Keep module top level to imports, constants, definitions, and the `__main__` guard — no side-effecting calls or mutable globals at import time.
paths:
  - "**/*.py"
---

Keep the module top level to imports, constants, class and function definitions, and the `__main__` guard — no module-level function calls, no global mutable state, no side-effecting initialization that fires at import time.

**Why:** Module-level side effects fire on `import`, which breaks testability (you can't import the module to test a helper without running the work) and surfaces dependency-order bugs (an import-time `HTTPClient()` that needs an env var the importer hasn't set yet). Mutable globals make function behavior depend on hidden state and complicate reasoning. Source principle: *Keep the module scope disciplined* (plus Clean Code ch. 17 G13; Effective Python Item 16).

**How to apply:** at module top level, allow only imports, `UPPER_SNAKE_CASE` constants, typed aliases, and class/function definitions. Move construction (`client = HTTPClient()`) and config-loading (`CONFIG = json.load(...)`) inside the function that needs them, or behind the `__main__` guard. Replace mutable globals with arguments passed from `main()`.

```python
def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)
    client = HTTPClient(args.endpoint)
    return run(client, args)
```

**Common fail signals (audit guidance):** `client = HTTPClient()` at module scope; `CONFIG = json.load(open("cfg.json"))` at module scope; a `setup()` call outside the guard.
