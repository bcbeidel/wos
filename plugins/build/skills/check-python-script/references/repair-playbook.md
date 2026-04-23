---
name: Repair Playbook — Python Scripts
description: One repair recipe per Tier-1 finding type plus one per Tier-2 dimension plus one per Tier-3 collision. Each recipe is Signal → CHANGE → FROM → TO → REASON. Applied during the check-python-script opt-in repair loop with per-finding confirmation.
---

# Repair Playbook

Per-finding repair recipes for check-python-script. Every Tier-1
finding type and every Tier-2 dimension has a recipe here. Apply
one at a time, with explicit user confirmation, re-running the
producing check after each fix.

**HINT-severity findings are feed-forward context, not repair
targets.** They inform the Tier-2 prompt; they do not belong in the
repair queue.

## Table of Contents

- [Format](#format)
- Tier-1 recipes
  - [`check_secrets.sh`](#tier-1--check_secretssh)
  - [AST parse failure (syntax)](#tier-1--ast-parse-failure)
  - [`check_structure.sh`](#tier-1--check_structuresh)
  - [`check_argparse.sh`](#tier-1--check_argparsesh)
  - [`check_deps.sh`](#tier-1--check_depssh)
  - [`check_ruff.sh`](#tier-1--check_ruffsh)
  - [`check_size.sh`](#tier-1--check_sizesh)
- [Tier-2 — Judgment Dimension Recipes](#tier-2--judgment-dimension-recipes)
  - D1 Output Discipline · D2 Input Validation · D3 Dependency Posture · D4 Performance Intent · D5 Naming · D6 Function Design · D7 Module-Scope Discipline · D8 Literal Intent · D9 Commenting Intent
- [Tier-3 — Cross-Entity Collision](#tier-3--cross-entity-collision)
- [Notes](#notes)

## Format

Each recipe carries five fields:

- **Signal** — the finding string or dimension name that triggers
  the recipe
- **CHANGE** — what to modify, in one sentence
- **FROM** — a concrete example of the non-compliant pattern
- **TO** — the compliant replacement
- **REASON** — why the change matters, tied to the source principle

---

## Tier-1 — `check_secrets.sh`

### Signal: `secret — API key / token / private URL detected`

**CHANGE** Remove the secret from source. Replace with an
`os.environ.get("<VAR_NAME>")` read and document the env var in the
module docstring.

**FROM**
```python
API_KEY = "sk-proj-abc123def456..."
```

**TO**
```python
import os
API_KEY = os.environ.get("OPENAI_API_KEY")
if not API_KEY:
    sys.exit("OPENAI_API_KEY not set")
```

**REASON** Secrets in committed source leak through git history,
logs, and backups. Externalizing to the environment is the minimum
bar; a secret manager is better where available.

---

## Tier-1 — AST parse failure

### Signal: `syntax — SyntaxError at line N: <msg>`

**CHANGE** Fix the Python syntax error named in the finding. The file
cannot be evaluated further — no other Tier-1 check runs on an
unparseable file, and Tier-2 judgment is skipped.

**FROM** *(unparseable — for example, an unclosed parenthesis or a
misaligned indent block)*

**TO** *(syntactically valid Python, verified by `python3 -c "import
ast; ast.parse(open('<path>').read())"`)*

**REASON** The AST helper cannot run any downstream check on a file
that doesn't parse. Fixing the syntax error is a strict prerequisite
to the rest of the audit; nothing else runs until this clears.

---

## Tier-1 — `check_structure.sh`

### Signal: `shebang — first line is not \`#!/usr/bin/env python3\``

**CHANGE** Replace the first line with `#!/usr/bin/env python3`. No
other first-line form is accepted; hardcoded paths (`/usr/bin/python`)
break virtualenvs and `/opt/homebrew/bin/python3` is not portable.

**FROM** `#!/usr/bin/python3`
**TO** `#!/usr/bin/env python3`

**REASON** `env` resolves the active Python from `PATH`, including
virtualenv-activated shells. Hardcoded paths are fragile across
environments.

### Signal: `guard-missing — no \`if __name__ == "__main__":\` guard at top level`

**CHANGE** Add a `__main__` guard at the module bottom that invokes
`sys.exit(main())`.

**FROM** *(script has no guard; `main()` is called at module scope or
never)*

**TO**
```python
if __name__ == "__main__":
    sys.exit(main())
```

**REASON** Without the guard, importing the script runs its body as a
side effect — breaking testability and turning `import myscript` into
an execution event. The guard also gives `sys.exit` a return value
from `main()` to translate into an exit code.

### Signal: `guard-shape — \`if __name__ == "__main__":\` does not invoke \`sys.exit(main())\``

**CHANGE** Replace the guard body with `sys.exit(main())`.

**FROM**
```python
if __name__ == "__main__":
    main()
```

**TO**
```python
if __name__ == "__main__":
    sys.exit(main())
```

**REASON** `main()` returns an int by the conventions in the
principles doc; without `sys.exit`, the return value is dropped and
the exit code is always 0 regardless of error paths.

### Signal: `main-returns — main() does not return an int`

**CHANGE** Annotate the `main()` signature as `-> int` and ensure
every code path returns a concrete int.

**FROM**
```python
def main(argv=None):
    args = get_parser().parse_args(argv)
    run(args)
```

**TO**
```python
def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)
    return run(args)
```

**REASON** The `sys.exit(main())` contract only works when `main()`
actually returns an exit code.

### Signal: `keyboard-interrupt — no except KeyboardInterrupt at top level of main()`

**CHANGE** Wrap the body of `main()` in a `try` that catches
`KeyboardInterrupt` and returns `130`.

**FROM**
```python
def main(argv=None) -> int:
    args = get_parser().parse_args(argv)
    return run(args)
```

**TO**
```python
def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)
    try:
        return run(args)
    except KeyboardInterrupt:
        return 130
```

**REASON** A script that dumps a traceback on Ctrl+C is
user-hostile. Exit code 130 is the shell convention for
SIGINT-terminated processes.

### Signal: `exec-bit — shebang present but executable bit not set`

**CHANGE** Run `chmod +x <path>` against the file.

**FROM** (filesystem) `-rw-r--r-- 1 user user 2048 Apr 22 14:30 script.py`
**TO** (filesystem) `-rwxr-xr-x 1 user user 2048 Apr 22 14:30 script.py`

**REASON** A shebang without `+x` is a lie — `./script.py` still
errors. The scaffold depends on the invocation contract.

---

## Tier-1 — `check_argparse.sh`

### Signal: `argparse-when-argv — sys.argv used past [0] but argparse not imported`

**CHANGE** Replace manual `sys.argv` slicing with an `argparse`-based
parser inside a `get_parser()` function.

**FROM**
```python
input_path = sys.argv[1]
output_path = sys.argv[2]
```

**TO**
```python
parser = argparse.ArgumentParser()
parser.add_argument("input", type=Path, help="Input file.")
parser.add_argument("output", type=Path, help="Output file.")
args = parser.parse_args()
```

**REASON** `argparse` provides `--help`, type coercion, and usage
errors that manual slicing can never match. Users who run the script
wrong deserve a useful error, not an `IndexError` traceback.

### Signal: `add-argument-help — add_argument() missing non-empty help=`

**CHANGE** Add a `help=` string to every `add_argument` call that
lacks one.

**FROM** `parser.add_argument("--out", type=Path)`
**TO** `parser.add_argument("--out", type=Path, help="Output path.")`

**REASON** The `help=` string is what the user sees when they run
`--help`. No string means no documentation.

### Signal: `subprocess-check — subprocess.run() missing check=True (or result not inspected)`

**CHANGE** Add `check=True` to the `subprocess.run()` call, or inspect
`result.returncode` explicitly.

**FROM** `subprocess.run(["git", "pull"])`
**TO** `subprocess.run(["git", "pull"], check=True)`

**REASON** Without `check=True`, a non-zero exit from the child
process is silently ignored and the script continues as if nothing
went wrong. That failure mode is exactly what a script should surface.

---

## Tier-1 — `check_deps.sh`

### Signal: `declared-deps — 3rd-party import without declared dependencies`

**CHANGE** Either add a PEP 723 `# /// script` block at the top of
the file, or colocate a `requirements.txt` next to the script.

**FROM** (script imports `requests` with no declaration present)

**TO** (PEP 723, self-contained)
```python
#!/usr/bin/env python3
"""Fetch exchange rates."""

# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.32"]
# ///

import requests
```

Or (colocated `requirements.txt`):
```
# requirements.txt next to the script
requests>=2.32
```

**REASON** Scripts are expected to be reproducible on a fresh
machine. Undeclared dependencies mean the next maintainer debugs an
`ImportError` before they can debug the actual problem.

---

## Tier-1 — `check_ruff.sh`

`check_ruff.sh` wraps `ruff`; the recipes below cover the emitted rule
codes.

### Signal: `ruff-D100 — module docstring missing`

**CHANGE** Add a module docstring as the first statement, naming the
script's purpose and one example invocation.

**FROM**
```python
#!/usr/bin/env python3
import argparse
```

**TO**
```python
#!/usr/bin/env python3
"""Fetch exchange rates and write them to a CSV.

Example:
    ./fetch_rates.py --source usd --target eur --out rates.csv
"""

import argparse
```

**REASON** The docstring is the first thing a reader sees and often
the only documentation a one-off script has.

### Signal: `ruff-E722 — bare except:` *(FAIL)*

**CHANGE** Replace `except:` with a specific exception type, or with
`except Exception as err:` at the top-level `main()` if a catch-all is
intended.

**FROM**
```python
try:
    run(args)
except:
    print("failed")
```

**TO**
```python
try:
    run(args)
except (FileNotFoundError, ValueError) as err:
    print(f"error: {err}", file=sys.stderr)
    return 1
```

**REASON** Bare `except:` swallows `KeyboardInterrupt` and
`SystemExit` and hides real bugs. It is the highest-frequency cause
of "my script is ignoring Ctrl+C" reports.

### Signal: `ruff-SIM115 — open() call not wrapped in a with statement`

**CHANGE** Wrap the `open()` call in a `with` block so cleanup runs on
exceptions.

**FROM**
```python
f = open(path)
data = f.read()
f.close()
```

**TO**
```python
with open(path, encoding="utf-8") as f:
    data = f.read()
```

**REASON** An exception between `open` and `close` leaves the file
handle dangling. The context manager guarantees cleanup.

### Signal: `ruff-PLW1514 — text-mode open() without encoding=`

**CHANGE** Add `encoding="utf-8"` to the `open()` call.

**FROM** `with open(path) as f:`
**TO** `with open(path, encoding="utf-8") as f:`

**REASON** The default encoding is platform-dependent. On a Windows
CI runner, a file that works locally on macOS silently corrupts
non-ASCII characters.

### Signal: `ruff-PTH — os.path.* used where pathlib.Path would work`

**CHANGE** Rewrite the `os.path` operation using `pathlib.Path`.

**FROM**
```python
if os.path.exists(os.path.join(dirname, filename)):
    ...
```

**TO**
```python
if (Path(dirname) / filename).exists():
    ...
```

**REASON** `pathlib.Path` removes a class of string-manipulation bugs
and reads more clearly. On Windows, the normalization is handled by
the library rather than by the author.

### Signal: `ruff-S602` / `ruff-S604 — shell=True in subprocess call` *(FAIL)*

**CHANGE** Replace `shell=True` with a list of arguments. Both S602
and S604 flag the same pattern; the ruff wrapper reports whichever ruff
version-specific code fires.

**FROM** `subprocess.run(f"grep {pattern} {file}", shell=True)`
**TO** `subprocess.run(["grep", pattern, file])`

**REASON** Shell injection is trivial when interpolated input reaches
`shell=True`. Argument lists pass through `execvp`, not a shell
parser, and are injection-safe.

### Signal: `ruff-S307 — eval or exec call` *(FAIL)*

**CHANGE** Replace `eval` / `exec` with a targeted parser — `json.loads`,
`ast.literal_eval`, or an explicit dispatch table.

**FROM** `result = eval(user_input)`
**TO** `result = ast.literal_eval(user_input)` *(for literal values)*

Or, for dispatch:
```python
ACTIONS = {"start": start, "stop": stop}
ACTIONS[action_name](args)
```

**REASON** `eval` / `exec` on external input is an RCE vector. The
targeted replacements cover every legitimate use case without the
vulnerability surface.

### Signal: `ruff-F401 — unused import`

**CHANGE** Remove the import.

**FROM** `import json  # not used anywhere`
**TO** *(line deleted)*

**REASON** Unused imports confuse readers and slow startup. If the
import exists for a side effect, add an explicit comment naming the
side effect.

### Signal: `ruff-ANN — function signature missing type hints`

**CHANGE** Add type annotations to parameters and return type. Start
with `main()` and script-boundary functions; interior helpers are
optional but encouraged.

**FROM** `def run(args):`
**TO** `def run(args: argparse.Namespace) -> int:`

**REASON** Type hints are documentation that doesn't drift and enable
static analysis (mypy, pyright) that catches a class of bugs before
runtime.

### Signal: `ruff-format — ruff format --check drift`

**CHANGE** Run `ruff format <path>` against the file.

**FROM** *(formatting drift)*
**TO** *(formatted)*

**REASON** Formatter compliance eliminates style bikeshedding and
keeps diffs legible. Drift from the formatter's output is a mechanical
signal, not a judgment call.

### Signal: `ruff-UP031 / ruff-UP032 — %-format or .format() where f-string applies`

**CHANGE** Rewrite as an f-string.

**FROM** `"hello, %s" % name` or `"hello, {}".format(name)`
**TO** `f"hello, {name}"`

**REASON** f-strings are clearer, faster at runtime, and harder to
mis-quote.

### Signal: `ruff-F403 — wildcard import` *(FAIL)*

**CHANGE** Replace the wildcard with explicit named imports.

**FROM** `from utils import *`
**TO** `from utils import load_config, write_report`

**REASON** Wildcard imports pollute the namespace and impede static
analysis — the tools can't tell which names the module exports.

### Signal: `ruff-S108 — hardcoded /tmp/ or /var/tmp/ path literal` *(FAIL)*

**CHANGE** Replace with a `tempfile` call.

**FROM** `tmp = f"/tmp/work_{os.getpid()}"`
**TO**
```python
import tempfile
with tempfile.TemporaryDirectory() as tmp:
    ...
```

**REASON** Hand-constructed `/tmp/` paths race against other processes
creating the same name and expose symlink-attack surface. `tempfile`
handles both.

---

## Tier-1 — `check_size.sh`

### Signal: `size — script length over 500 non-blank lines`

**CHANGE** Extract cohesive sections into helper functions (or
modules, if the refactor is large enough to justify a `utils.py`
alongside the script). Past ~500 lines, convert to a package:
`pyproject.toml` + `src/<pkg>/`.

**FROM** *(a 750-line single-file script with four logical sections
inlined in `main()`)*
**TO** *(a 300-line script that imports helpers from a colocated
`<script>_helpers.py`, or a `pyproject.toml`-managed package)*

**REASON** Single-file discipline breaks down past a threshold. A
750-line script fails testability, readability, and partial-import
signals that a package handles cleanly.

---

## Tier-2 — Judgment Dimension Recipes

Tier-2 findings carry WARN severity; they're coaching, not blocking.
Each recipe is a repair pattern the user can apply after the judge
names a specific violation.

### D1 Output Discipline

**CHANGE** Move non-data output to stderr. Switch status narration to
`logging`. Ensure every error branch returns non-zero.

**FROM** `print(f"error: {err}")` in an error path that returns `0`
**TO** `print(f"error: {err}", file=sys.stderr); return 1`

**REASON** Unix pipelines depend on the stdout-for-data /
stderr-for-chatter convention. Callers in cron, CI, and Make depend on
the exit-code contract.

### D2 Input Validation

**CHANGE** Add early input validation before destructive work. Wire
`args.dry_run` into the destructive code path.

**FROM**
```python
for path in args.inputs:
    shutil.rmtree(path)
```

**TO**
```python
for path in args.inputs:
    if not path.exists():
        print(f"skip: {path} does not exist", file=sys.stderr)
        continue
    if args.dry_run:
        print(f"would remove: {path}")
        continue
    shutil.rmtree(path)
```

**REASON** "Fail before damage" is cheap to implement and expensive
to skip. A dry-run flag that isn't consulted is worse than no flag —
it implies safety that isn't there.

### D3 Dependency Posture

**CHANGE** Replace the third-party dependency with a stdlib
equivalent, when feasible.

**FROM** `import requests; resp = requests.get(url).json()`
**TO**
```python
import json, urllib.request
with urllib.request.urlopen(url, timeout=30) as resp:
    data = json.load(resp)
```

**REASON** Each third-party dependency is a deployment surface and a
potential security-update obligation. Scripts that use stdlib
equivalents run anywhere Python runs.

### D4 Performance Intent

**CHANGE** Replace `.read()` followed by iteration with line-by-line
iteration.

**FROM**
```python
content = open(path).read()
for line in content.splitlines():
    process(line)
```

**TO**
```python
with open(path, encoding="utf-8") as f:
    for line in f:
        process(line)
```

**REASON** Scripts get run on files larger than the author imagined.
OOM on a 2 GB input is not a bug the user should have to work around.

### D5 Naming

**CHANGE** Rename the function or variable to state its intent. Move
away from `tmp`, `data`, `process`, `handle_it`.

**FROM** `def process(data):` with a body that parses CSV rows
**TO** `def parse_csv_rows(rows: Iterable[str]) -> list[Row]:`

**REASON** Code is read far more often than it's written. A name
that predicts behavior saves the reader one or more scans of the
body.

### D6 Function Design

**CHANGE** Extract cohesive sections of a long function into
helpers. Fold three copies of the same block into a single helper
call.

**FROM** *(a 150-line main() with fetch, transform, validate, write
inlined)*

**TO**
```python
def main(argv=None) -> int:
    args = get_parser().parse_args(argv)
    raw = fetch(args.source)
    records = transform(raw)
    validate(records)
    write(records, args.out)
    return 0
```

**REASON** Short named functions read as their own commentary. Duplicated
blocks drift — fix one copy, forget the others, ship a partial bug.

### D7 Module-Scope Discipline

**CHANGE** Move module-level side-effecting calls into a function or
behind the `__main__` guard. Replace module-level mutable state with
argument-passed parameters.

**FROM** `client = HTTPClient()` at module scope
**TO** Instantiate `client` inside the function that needs it, or
pass it as a parameter from `main()`.

**REASON** Module-level side effects fire on `import`, which breaks
testability and surfaces subtle dependency-order bugs.

### D8 Literal Intent

**CHANGE** Promote the meaningful literal to a named constant at the
top of the module.

**FROM** `response = requests.get(url, timeout=30)`
**TO**
```python
HTTP_TIMEOUT_SECONDS = 30
...
response = requests.get(url, timeout=HTTP_TIMEOUT_SECONDS)
```

**REASON** A named constant teaches the reader what the value means
and centralizes its adjustment point.

### D9 Commenting Intent

**CHANGE** Replace what-comments with why-comments (or delete them if
the code speaks for itself). Tag owner-less TODOs.

**FROM** `# increment counter` above `counter += 1`
**TO** *(delete the comment)*

Or
**FROM** `# TODO: fix this`
**TO** `# TODO(bbeidel): normalize Unicode before comparison — currently miscounts combining characters`

**REASON** Comments that restate the code rot alongside it. Comments
that explain *why* stay useful as the code evolves.

---

## Tier-3 — Cross-Entity Collision

### Signal: `collision — near-identical get_parser() / error-handler / docstring across scripts`

**CHANGE** Extract the shared block into a helper module sitting
alongside the scripts (`<dir>/_helpers.py`) and import from it. If the
scripts are truly independent, accept the duplication — DRY applies
to scripts that will co-evolve, not scripts that happen to look alike.

**FROM** `get_parser()` copied across three scripts with
script-specific tweaks to each

**TO** `_helpers.py` exposes `make_base_parser()`; each script
imports it and adds its own arguments.

**REASON** Shared parsing logic drifts when maintained in triplicate.
A single source of truth keeps the arguments coherent and documents
the shared conventions in one place.

---

## Notes

- **HINT-severity findings** are pre-filter pre-evaluations, not
  repair targets. They inform the Tier-2 prompt and do not enter the
  repair queue.
- **Per-finding confirmation** is non-negotiable. Bulk application
  removes the user's ability to review individual changes and is a
  documented anti-pattern in the check-python-script SKILL.md.
- **Re-run after each fix.** A repair can introduce a new finding
  elsewhere (e.g., adding `sys.exit(main())` may require fixing the
  `main()` return type). The Tier-1 script that produced the original
  finding re-runs before moving to the next repair.
