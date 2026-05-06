---
name: Injection Safety
description: Payload-derived values cannot trigger shell injection or PATH hijacking.
paths:
  - "**/.claude/hooks/**/*.sh"
  - "**/.claude/hooks/**/*.bash"
  - "**/.claude/hooks/**/*.py"
---

Never `eval` payload-derived values, always quote payload expansions as `"${var}"`, and absolute-path or `command -v`-guard bare commands in adversarial environments.

**Why:** Payload fields (`tool_input.command`, `tool_input.file_path`, etc.) reflect user-controllable input. Passing them to `eval` is shell injection with no safe sanitization — an attacker who can influence a tool call gets arbitrary code execution as the user. Unquoted expansions word-split and glob, so a payload value like `* /etc/passwd` becomes two arguments. Bare command names in project-committed `settings.json` or in CI invite PATH hijacking. Severity: `fail` for `eval` on payload; `warn` for unquoted expansions and bare commands in adversarial environments.

**How to apply:** remove `eval` entirely. If you must execute a derived command, build an array and expand it: `cmd=(executable --arg "$value"); "${cmd[@]}"`. Quote every expansion of a payload value as `"${VAR}"` — never bare `$VAR`. In adversarial environments (project `settings.json` with team commit access, CI contexts with `.github/`), absolute-path tools or guard with `command -v`.

```bash
# Quote payload expansions
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command')
if [[ "${COMMAND}" == *"rm -rf"* ]]; then ...; fi

# Guard bare command names
JQ=$(command -v jq) || { echo "jq required" >&2; exit 2; }
"$JQ" -r '.tool_input.command'
```

**Common fail signals (audit guidance):**
- `eval "$cmd"` / `eval "$INPUT"` / `eval $(...)` where the input traces back to the payload.
- Bare `$VAR` (unquoted) for any value derived from `tool_input` / stdin.
- `bash -c "$value"` with payload-derived `$value` — same hazard as `eval`.
- Calls to `jq`, `python3`, `git`, etc. without absolute path or `command -v` guard in a project-committed hook.
- String-interpolated subprocess invocation in Python (`subprocess.run(..., shell=True)` with payload values).
