---
name: build-python-script
description: >
  Scaffolds a standalone Python 3 script — a single-file CLI tool,
  automation helper, or data-wrangling utility — with shebang, module
  docstring, `main(argv) -> int`, `__main__` guard via `sys.exit(main())`,
  argparse parser, KeyboardInterrupt handling, and declared dependencies.
  Use when the user wants to "scaffold a python script", "create a
  python script", or "build an automation script in python". Not for
  long-running
  services, packages with multiple modules, or Claude Code hooks — route
  to the appropriate primitive instead.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
argument-hint: "[purpose]"
user-invocable: true
references:
  - ../../_shared/references/python-script-best-practices.md
  - ../../_shared/references/primitive-routing.md
license: MIT
---

# Build Python Script

Scaffold a standalone Python 3 script: a single-file program that runs
from the shell, does one clear thing, and returns a useful exit code.
The authoring rubric — what makes a script load-bearing, the anatomy
template, patterns that work — lives in
[python-script-best-practices.md](../../_shared/references/python-script-best-practices.md).
This skill is the workflow; the principles doc is the rubric.

This skill is not for Claude Code hooks (`/build:build-hook` owns that
lifecycle), not for Bash scripts (`/build:build-bash-script`), and not for
multi-module Python packages (scripting discipline breaks down past a
threshold; start a proper package instead).

**Workflow sequence:** 1. Route → 2. Scope Gate → 3. Elicit →
4. Draft → 5. Safety Check → 6. Review Gate → 7. Save → 8. Test

## When to use

Also fires when the user phrases the request as:

- "write a CLI script in python"
- "new python script"

## 1. Route

Confirm a standalone Python script is the right primitive *and* that
Python is the right language before asking scaffold-specific questions.

**Wrong primitive:**

- **Event-triggered quality enforcement** (PreToolUse, SessionStart,
  Stop, etc.) → `/build:build-hook`. Hooks have a `settings.json`
  registration, a `tool_input` payload contract, and lifecycle
  semantics a standalone script doesn't express.
- **A Claude Code skill definition** → `/build:build-skill`.
- **A semantic judgment captured as an LLM-evaluated rule** →
  `/build:build-rule`.

**Wrong language — should be shell instead:**

- Task is pure glue — stitching `git` / `curl` / `jq` / `find` /
  `xargs` through a pipeline, no structured data
- Task is genuinely one-shot and will not grow business logic
- Execution environment cannot be relied on to ship Python (bare
  containers, minimal CI images)

The full language-selection decision lives in the *Language Selection*
section of
[primitive-routing.md](../../_shared/references/primitive-routing.md) —
consult it when the choice is not obvious. **Tiebreaker rule from that
doc:** when the decision is genuinely balanced, Python wins on
interpretability.

**Right primitive and right language** (CLI tool, data-wrangling helper,
automation utility, one-shot job with structured data or >100 LOC of
business logic, work that benefits from `pytest` against `main()`) →
proceed to Scope Gate.

## 2. Scope Gate

Refuse to scaffold — and recommend an alternative — when the request
signals Python-script is the wrong tool. Probe for any of:

1. **Multiple entry points or long-running service** — a daemon, a web
   server, or anything with more than one callable surface is a
   package, not a script. Recommend starting `pyproject.toml` +
   `src/<pkg>/` layout.
2. **Test coverage heavier than the code** — if the author is planning
   to write more test code than script code, the workflow wants a
   package with proper module boundaries. Single-file scripts trade
   testability for portability; if testability is the priority, pay
   the package cost.
3. **Shared state across invocations** — databases, long-lived
   connections, on-disk caches the script owns. Scripts are stateless
   units; persistent state belongs in a service or package.
4. **Hot path / performance-critical** — a script invoked thousands of
   times per second loses to the import-time overhead. Recommend a
   daemon + IPC or a compiled tool.
5. **Cross-platform GUI or system-tray integration** — Python scripts
   don't handle GUI packaging cleanly. Recommend the user pick a
   platform-native toolkit.

If any signal fires, state the signal, name the recommended
alternative, and stop. Do not proceed to Elicit.

## 3. Elicit

If `$ARGUMENTS` is non-empty, parse it as `[purpose]` and pre-fill the
purpose field. Otherwise ask, one question at a time:

**1. Purpose** — one sentence: what does this script do? Preferably
verb-phrased ("fetch daily exchange rates and write them to a CSV").

**2. Profile** — pick one. See
[python-script-profiles.md](../../_shared/references/python-script-profiles.md)
for the full spec.
- `cli` (default) — single-file program invoked from the shell;
  argparse, exit codes, `__main__` guard. The current scaffold shape.
- `library` — a module imported, not invoked. No shebang, no main,
  no argparse. Module docstring + `__all__` + public API only.
- `skill-helper` — JSON-over-stdio helper called from a skill.
  Reads `json.loads(sys.stdin.read())`; writes JSON to stdout;
  emits structured JSON errors to stderr; distinct exit codes
  (`EXIT_OK=0`, `EXIT_USER_ERROR=2`, `EXIT_INTERNAL_ERROR=3`);
  atomic file writes via `<path>.tmp` + `os.replace`.

When profile=library, **skip Questions 3, 4, 5, and 6** (invocation
style, input shape, output destination, destructive ops are all
CLI-shape concerns). Ask Question 7 (third-party dependencies — a
library can have them too) and Question 8 (save path).

When profile=skill-helper, skip Question 3 (invocation style is
fixed by the profile). Keep the rest.

**3. Invocation style** *(cli only)* — pick one:
- `cli` — accepts flags and positional args via `argparse`; has
  `--help` output. Default for anything a human invokes.
- `glue` — fixed positional args, called from a Makefile or another
  script. Minimal argparse surface.
- `library` — importable for testing (`from <script> import main`) but
  also runnable directly via the `__main__` guard. The default
  structure already supports this; pick when the user will write
  `pytest` against `main()`.

**4. Input shape** *(cli only)* — where does the script read from?
- `args` — filenames or values passed as positional arguments.
- `stdin` — reads from stdin, supports `-` as stdin sentinel.
- `none` — no input beyond flags.

**5. Output destination** *(cli, skill-helper)* — where does primary output go?
- `stdout` — default; data to stdout, logs to stderr. Composable in
  pipelines.
- `file` — writes to a path provided via `--out`. Pair with
  `encoding="utf-8"`.
- `none` — the script is called for its side effects (e.g., network
  calls).

**6. Destructive operations?** *(cli, skill-helper)* — does the script
delete, overwrite, move files, or make irreversible network calls? If
yes, the scaffold adds a `--dry-run` flag (default true) and a `--yes`
confirmation flag. If no, those are omitted.

**7. Third-party dependencies** — any non-stdlib imports? If yes,
collect the list and pick the declaration mechanism:
- `pep723` — inline `# /// script` block at the top of the file. Best
  for portable single-file scripts run via `uv run` or `pipx run`.
- `requirements` — a colocated `requirements.txt`. Best when the
  script ships with a README or test fixtures.
- `comment` — a top-of-file comment block. Accept as a fallback.
- `none` — stdlib-only (prefer this when feasible; most scripting
  needs are met by `argparse`, `pathlib`, `json`, `csv`,
  `subprocess`, `logging`, `http.client`, `tempfile`).

**8. Save path** — where should the script land? No default; common
homes: `scripts/`, `bin/`, `plugins/<name>/scripts/`,
`.github/scripts/`. Ask explicitly.

## 4. Draft

Produce two artifacts.

**Artifact 1: The script.** Branch on profile.

### Profile: library

Use the `library` template from
[python-script-profiles.md](../../_shared/references/python-script-profiles.md):
module docstring + `__all__` + public functions / classes only. No
shebang, no main, no `__main__` guard, no argparse. Type-hint the
public API; docstring the public symbols.

### Profile: skill-helper

Use the `skill-helper` template from the profiles spec: cli template
extended with `EXIT_OK / EXIT_USER_ERROR / EXIT_INTERNAL_ERROR`
constants, `json.loads(sys.stdin.read())` payload read in `main()`,
an `emit_error(code, message, hint=None)` helper writing JSON to
stderr, and an `atomic_write(path, content)` helper using `<path>.tmp`
+ `os.replace`. Argparse holds flags only — payload arrives on stdin.

### Profile: cli (default)

One conditionalized template. Sections marked *(if destructive)* or
*(if pep723)* are omitted when the intake rules them out.

```python
#!/usr/bin/env python3
"""<one-line synopsis>.

Example:
    ./<progname> <typical args>
"""

# /// script                                     # (if pep723)
# requires-python = ">=3.10"
# dependencies = [
#   "<dep>==<version>",
# ]
# ///

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

LOG = logging.getLogger(__name__)
EXIT_USAGE = 2
EXIT_INTERRUPTED = 130


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="<one-line purpose>",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--input", type=Path, required=True, help="Input path.")
    parser.add_argument("--out", type=Path, required=True, help="Output path.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print planned actions; take none.")       # (if destructive)
    parser.add_argument("-v", "--verbose", action="count", default=0,
                        help="Increase log verbosity (repeatable).")
    return parser


def run(args: argparse.Namespace) -> int:
    # <body — split into small functions as the script grows>
    return 0


def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.WARNING - 10 * min(args.verbose, 2),
        stream=sys.stderr,
        format="%(levelname)s %(message)s",
    )
    try:
        return run(args)
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED
    except (FileNotFoundError, ValueError) as err:
        print(f"error: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

*(if pep723)* Include the `# /// script` block between the docstring
and the imports. Omit the colocated `requirements.txt` reference —
PEP 723 is self-contained.

*(if not destructive)* Omit the `--dry-run` argument. The rest stays.

*(library invocation style)* No scaffold changes — the default
structure (`main(argv)` parameterized, module-scope side-effect-free,
`__main__` guard) already supports `from <script> import main` for
testing.

**Artifact 2: A suggested invocation line** — how the user or a
Makefile would call the script, ready to paste. Include the
`chmod +x` step so the shebang + executable-bit contract holds.

Present both artifacts to the user before any safety checks.

## 5. Safety Check

Review the draft against the rubric in
[python-script-best-practices.md](../../_shared/references/python-script-best-practices.md)
before presenting. Group the checks:

**Structure.** Shebang is exactly `#!/usr/bin/env python3`. Module
docstring is the first statement and shows at least one example
invocation. `main()` signature returns an `int`. The `__main__` guard
delegates via `sys.exit(main())`. `except KeyboardInterrupt` is present
at the top level.

**I/O contract.** Primary output goes to stdout; errors and logs go to
stderr. Text-mode `open()` calls carry `encoding="utf-8"`. Filesystem
paths use `pathlib.Path`, not `os.path` strings. Context managers
(`with`) wrap any resource needing cleanup.

**Arguments.** `argparse` is imported (not manual `sys.argv` slicing).
Every `add_argument` carries a non-empty `help=` string. Validation
lives in `type=` and `choices=` where applicable.

**Safety.** No `shell=True` in subprocess calls. No `eval` / `exec`.
No hardcoded `/tmp/` or `/var/tmp/` path literals (use `tempfile`
instead). No hardcoded credentials, hostnames, or absolute paths —
those come from arguments or `os.environ.get()`.

**Dependencies.** If any non-stdlib import is present, dependencies
are declared (PEP 723 block, colocated `requirements.txt`, or
top-of-file comment). No wildcard imports. No unused imports.

**Profile fit** *(applies when profile≠cli)*. For profile=library,
verify the draft has no shebang, no `__main__` guard, no `main()`,
no argparse, and declares `__all__`. For profile=skill-helper,
verify the draft reads JSON from stdin (`json.loads(sys.stdin.read())`),
emits structured JSON to stderr on error, declares ≥2 distinct
non-zero exit-code constants, and uses `os.replace` for any file
writes. The
[profiles spec](../../_shared/references/python-script-profiles.md)
is the canonical applicability matrix.

**Detector-script hygiene** *(applies when the script scans source
for forbidden patterns — `check-*/scripts/`, or a docstring that
names "detect," "scanner," or "linter")*. Docstrings, comments, and
identifier names paraphrase the detected pattern rather than naming
it literally (the *Detector-Script Pattern Hygiene* section of
[python-script-best-practices.md](../../_shared/references/python-script-best-practices.md)
covers the rules and live examples). Regex literals are structured
so the scanned byte sequence is non-contiguous in source — a
self-scan must not produce phantom findings.

If any check fails, revise the draft before presenting. The Review
Gate is for user approval, not correctness recovery — safety issues
get fixed in the draft, not at the gate.

## 6. Review Gate

Present both artifacts (script + invocation line) and wait for
explicit user approval before writing any file to disk. Write only
after this gate passes.

If the user requests changes, revise and re-present. Continue until
the user explicitly approves or cancels. Proceed to Save only on
explicit approval.

## 7. Save

Write the approved script to the path elicited in Step 3.6. Mark it
executable:

```bash
chmod +x <path>
```

A shebang without `+x` is a lie — the executable bit is part of the
contract the principles doc names. Show the suggested invocation line
for the user to wire into a Makefile, CI config, or README.

If PEP 723 was picked, no extra files are needed. If `requirements`
was picked, scaffold `<parent>/requirements.txt` next to the script
(create if absent, append if not).

## 8. Test

Offer the audit:

> "Run `/build:check-python-script <path>` to audit the scaffolded
> script against the deterministic checks and the judgment dimensions?"

The audit is the canonical follow-on; running it once after scaffold
catches anything the Safety Check missed and gives the user a
baseline-clean starting point.

## Anti-Pattern Guards

1. **Skipping the Scope Gate** — always probe the five signals before
   Elicit. Scaffolding a single-file script when the workflow wants a
   package pushes technical debt into the repo that will be expensive
   to pay down later.
2. **Leaving dependencies undeclared** — scripts that import
   third-party packages without a PEP 723 block, `requirements.txt`,
   or top-of-file comment block are not reproducible. The intake
   explicitly elicits the declaration mechanism; populate it.
3. **Omitting the KeyboardInterrupt handler** — a script that dumps a
   traceback on Ctrl+C is user-hostile, and this is a detail authors
   routinely forget. The scaffold includes it by default; do not
   strip it for brevity.
4. **Hand-waving `--dry-run`** — if Intake step 3.5 flagged destructive
   operations, the draft must wire `args.dry_run` into the actual
   destructive code path, not just accept the flag and ignore it.
   Show the `if args.dry_run: ...` branch in the `run()` body.
5. **Skipping the Review Gate** — write to disk only after explicit
   user approval. Present both artifacts first.

## Key Instructions

- Refuse cleanly on Scope Gate signals. Scaffolding a script when a
  package is the right tool creates a conversion cost someone has to
  pay later.
- Write files to disk only after the Review Gate passes.
- Elicit the save path from the user. Do not invent one.
- The `--dry-run` flag is only scaffolded when Intake step 3.5 flagged
  destructive operations. Do not add it unconditionally — it clutters
  read-only scripts.
- When Intake picks `pep723`, use only the PEP 723 block — a second
  declaration (colocated `requirements.txt`) creates two sources of
  truth.
- Won't scaffold scripts for Claude Code hook events — route to
  `/build:build-hook`.
- Won't scaffold when any Scope Gate signal fires — recommend the
  appropriate alternative instead.
- Recovery if a script is written in error: `rm <path>` removes it
  cleanly. The scaffold is self-contained (no settings.json entry, no
  shared-module registration), so removal leaves no dangling state.

## Handoff

**Receives:** user intent for a Python script (purpose, invocation
style, input shape, output destination, destructive-op flag,
third-party dependencies + declaration mechanism, save path).
**Produces:** an executable Python script at the user-supplied path
plus a suggested invocation line; optionally a `requirements.txt`
when that declaration mechanism was picked.
**Chainable to:** `/build:check-python-script` (audit the scaffolded
script against the deterministic checks and judgment dimensions).
