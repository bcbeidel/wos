# uv run Preflight Check

Skills that invoke `uv run` MUST run this preflight sequence before the
actual script. This catches missing tools early with actionable errors.

## Steps

### 1. Check uv availability

Run:
```bash
uv --version
```

If the command fails (not found):
- Tell the user: **"uv is required but not installed. Install it with:
  `curl -LsSf https://astral.sh/uv/install.sh | sh` — then restart your
  terminal."**
- **STOP.** Do not attempt to run the script.

### 2. Run the canary script

Run:
```bash
uv run <plugin-scripts-dir>/check_runtime.py
```

Where `<plugin-scripts-dir>` is the `scripts/` directory at the root of this
plugin (sibling to the `skills/` directory containing this reference file).

Parse the JSON output:
- If `"status": "ok"` — proceed to step 3.
- If `"status": "fail"` or non-zero exit — tell the user:
  **"uv cannot resolve PEP 723 inline dependencies. Check your network
  connection and proxy settings."** Then show the error from the JSON output.
  **STOP.**

### 3. Run the actual script

Run:
```bash
uv run <plugin-scripts-dir>/<script-name>.py [arguments]
```

If the script itself fails (non-zero exit), show stderr to the user.

## Error Reference

| Failure | User Message |
|---------|-------------|
| `uv` not in PATH | "uv is required but not installed. Install: `curl -LsSf https://astral.sh/uv/install.sh \| sh`" |
| Canary returns `"fail"` | "uv cannot resolve PEP 723 dependencies. Check network/proxy settings." |
| Canary non-zero exit | Show stderr output from the canary |
| Target script fails | Show stderr output from the target script |

## Skill Integration

Add this reference to any skill that uses `uv run`:

```yaml
references:
  - ../_shared/references/preflight.md
```

Then in the skill's instructions, reference the preflight steps:
"Before running any `uv run` command, follow the preflight check in the
preflight reference."
