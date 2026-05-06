---
name: JSON Output Contract
description: Structured JSON responses comply with the exit-0-only contract, include required fields, and fit within the 10,000-character cap.
paths:
  - "**/.claude/hooks/**/*.sh"
  - "**/.claude/hooks/**/*.bash"
  - "**/.claude/hooks/**/*.py"
---

Emit JSON only on exit 0, begin stdout directly with the JSON object, include `hookSpecificOutput.hookEventName`, keep payload under ~8 KB, and consolidate `updatedInput` into one PreToolUse hook per tool.

**Why:** Claude Code parses stdout only on exit 0 — JSON emitted on a non-zero exit is silently discarded. Any leading non-JSON text (a stray `echo "running"` before the object) triggers "JSON validation failed" with no recovery. Output is silently truncated at 10,000 characters, which corrupts JSON mid-string and produces an unparseable payload. Multiple PreToolUse hooks returning `updatedInput` for the same tool race; the last finisher wins, the others are silently dropped — `updatedInput` only works under last-finisher semantics. Severity: `warn`.

**How to apply:** use `exit 2` with a plain-text message to stderr for blocks; reserve JSON for successful exit-0 paths. Ensure the first byte of stdout is `{`. Always include `hookSpecificOutput.hookEventName`. Keep `additionalContext` / `systemMessage` under ~8 KB as a safety margin. Consolidate any `updatedInput` logic for a given tool into a single hook.

```bash
# Pass-through with structured output (exit 0 only)
cat <<JSON
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "${context}"
  }
}
JSON
exit 0
```

**Common fail signals (audit guidance):**
- `echo` / `printf` / log lines emitted to stdout before the JSON object.
- JSON output on a code path that ends in `exit 2` (block + JSON; the JSON is discarded).
- Missing `hookSpecificOutput.hookEventName` field.
- Output assembled from large file reads or `git log` without size capping — can exceed 10 KB.
- Multiple hook entries returning `updatedInput` for the same tool matcher.
