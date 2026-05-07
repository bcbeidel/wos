---
name: Python Script Profiles
description: Profile enum and per-profile rule applicability for python-script primitives. Defines cli/library/skill-helper, the heuristic detection rules, and which Tier-1 detector scripts and Tier-2 judgment dimensions apply per profile. Referenced by build-python-script and check-python-script.
---

# Python Script Profiles

A *profile* is the shape a python-script takes — its entry-point contract, its imports posture, its I/O contract. Three concrete profiles cover the python-script use cases this skill library supports. Profile is a string enum, not a composable feature flag, because three concrete shapes cover the stated workload and composability invites combinatorial explosion in the rule applicability matrix.

## Profiles

### cli

The default shape: a single-file program invoked from the shell, parses arguments via `argparse`, returns an exit code. Every existing python-script in the repo is `cli`-profile by default — when no `--profile=<name>` flag is provided and the heuristic does not strongly indicate `library` or `skill-helper`, the profile resolves to `cli`.

Required shape:
- `#!/usr/bin/env python3` shebang
- module docstring with one example invocation
- `main(argv: list[str] | None = None) -> int`
- `if __name__ == "__main__": sys.exit(main())` guard
- `argparse` for any flags
- `KeyboardInterrupt` handled at the top level

### library

A module imported by other code, not invoked from a shell. The CLI shell from `cli` is dead weight here; the rules that enforce shebang/main/argparse become *expected absent* and new rules around import-time discipline take their place.

Required shape:
- module docstring (a one-line synopsis followed by an optional paragraph naming the public API)
- `__all__` declared at module scope (explicit public-API surface)
- public functions and classes type-hinted
- public symbols carry docstrings
- no module-level side effects (no work at import time other than imports, type aliases, `__all__`, and pure-RHS constant assignments)

Forbidden shape:
- shebang
- `if __name__ == "__main__":` guard
- `main()` function returning `int`
- `argparse` (a library does not parse CLI flags)

### skill-helper

A specialized `cli` for the contract that Claude Code skills shell out to. Reads a JSON payload from stdin, writes a JSON summary to stdout, emits structured JSON errors to stderr with non-zero exit codes, and writes any output files atomically.

Required shape (in addition to `cli` requirements):
- payload arrives via `json.loads(sys.stdin.read())` — *not* via `--payload-file` or any other flag-based mechanism
- summary emitted to stdout via `json.dumps(...)`
- on error, structured JSON to stderr matching `{"error": "<code>", "message": "<str>", "hint": "<str>"}` (the `hint` field is optional)
- distinct exit codes carry meaning: `0` success, `2` user error, `3` internal error (a script that uses only `0` and `1` is below the contract — non-zero must be subdivided when the user's recovery action differs)
- atomic writes use `<path>.tmp` followed by `os.replace(<tmp>, <path>)` — direct `<path>.write_text(...)` is non-atomic and may leave half-written state on interruption

Forbidden shape:
- raw tracebacks emitted to stderr (the contract is structured JSON; `--debug` for verbose output is the escape hatch)
- payload arriving through CLI flags

## Heuristic Detection

Used by `check-python-script` when no `--profile=<name>` flag is supplied. The detection is best-effort — when ambiguous, the result is `cli` (the safe default). The flag override always wins.

Detection rules, applied in order:

1. **library**: if the script has *no* shebang AND *no* `if __name__ == "__main__":` guard AND *no* `main(` function definition, return `library`.
2. **skill-helper**: if the script imports `argparse` AND uses `sys.stdin.read()` AND uses `json.loads(`, return `skill-helper`.
3. **cli (default)**: anything else.

The detector lives at `plugins/build/_shared/scripts/detect_python_profile.py` and exposes both library use (`from detect_python_profile import detect`) and CLI use (`./detect_python_profile.py <path>` prints the resolved profile name).

## Tier-1 Applicability Matrix

`check-python-script`'s 6 existing Tier-1 scripts, plus the 2 new profile-specific Tier-1 scripts:

| Script | cli | library | skill-helper |
|---|---|---|---|
| `check_argparse.sh` | ✓ | — | ✓ |
| `check_deps.sh` | ✓ | ✓ | ✓ |
| `check_ruff.sh` | ✓ | ✓ | ✓ |
| `check_secrets.sh` | ✓ | ✓ | ✓ |
| `check_size.sh` | ✓ | ✓ | ✓ |
| `check_structure.sh` | ✓ | — | ✓ |
| `check_library_discipline.py` (new) | — | ✓ | — |
| `check_skill_helper_contract.py` (new) | — | — | ✓ |

`check_argparse.sh` and `check_structure.sh` enforce the cli-shell shape (shebang, main, `__main__` guard, argparse). They do not apply under `library` because the absence of those items is *correct*. They do apply under `skill-helper` because skill-helper is a cli-shell variant that adds rules on top.

## Tier-2 Applicability Matrix

The 9 existing Tier-2 dimensions apply across all profiles — they describe judgment-level concerns (input validation, output discipline, naming, function design, etc.) that are profile-agnostic. The 5 new dimensions are profile-specific:

| Dimension | cli | library | skill-helper |
|---|---|---|---|
| (existing 9: input-validation, output-discipline, dependency-posture, performance-intent, naming, function-design, module-scope-discipline, literal-intent, commenting-intent) | ✓ | ✓ | ✓ |
| `check-no-import-time-side-effects` | — | ✓ | — |
| `check-public-symbols-typed` | — | ✓ | — |
| `check-public-symbols-documented` | — | ✓ | — |
| `check-structured-stderr-errors` | — | — | ✓ |
| `check-exit-code-meaning` | — | — | ✓ |

## Build-Side Templates

Three conditional templates in `build-python-script`'s Draft step. The `cli` template is the existing scaffold; the other two are new shapes.

**`cli`** — unchanged (current behavior). See the existing template in `build-python-script/SKILL.md` Step 4.

**`library`** — module docstring + explicit public-API + nothing else.

```python
"""<one-line synopsis of the module>.

<Optional paragraph naming the public API.>
"""

from __future__ import annotations

__all__ = ["<public_symbol>"]

# (public functions and classes here, type-hinted, docstring'd)
```

**`skill-helper`** — cli template + stdin-JSON read + structured-error helper + atomic-write helper + distinct exit codes.

```python
#!/usr/bin/env python3
"""<one-line synopsis>.

Reads JSON payload from stdin; writes JSON summary to stdout;
emits structured errors to stderr with distinct exit codes.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_USER_ERROR = 2
EXIT_INTERNAL_ERROR = 3


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="<one-line purpose>")
    # flags only — payload arrives on stdin
    return parser


def emit_error(code: str, message: str, hint: str | None = None) -> None:
    payload: dict[str, str] = {"error": code, "message": message}
    if hint:
        payload["hint"] = hint
    print(json.dumps(payload), file=sys.stderr)


def atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)
    try:
        payload = json.loads(sys.stdin.read())
    except json.JSONDecodeError as err:
        emit_error("invalid-json", f"could not parse stdin: {err}")
        return EXIT_USER_ERROR
    try:
        result: dict = {}
        # ... do work, populate result ...
        print(json.dumps(result))
        return EXIT_OK
    except KeyboardInterrupt:
        return 130
    except Exception as err:  # noqa: BLE001 — top-level safety net
        emit_error("internal", str(err))
        return EXIT_INTERNAL_ERROR


if __name__ == "__main__":
    sys.exit(main())
```

## Versioning

The profile enum is closed at v1: `cli`, `library`, `skill-helper`. Adding a fourth value (`service`, `notebook`, etc.) requires a deliberate scoping pass — applicability matrices, build templates, and check rules all need a coherent extension. Until that pass happens, ambiguous cases default to `cli` and the user can override with `--profile=<name>`.
