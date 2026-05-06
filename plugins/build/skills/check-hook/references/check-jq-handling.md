---
name: jq Handling
description: jq calls check availability, use tool-appropriate field paths, and account for cross-platform payload shape.
paths:
  - "**/.claude/hooks/**/*.sh"
  - "**/.claude/hooks/**/*.bash"
  - "**/.claude/hooks/**/*.py"
---

Verify `jq` is on PATH, match the field path to the matcher's tool (`.tool_input.command` for Bash, `.tool_input.file_path` for Write, `.tool_input.path` for Edit/MultiEdit), and branch on payload shape for Copilot-capable hooks.

**Why:** `jq` is not guaranteed in Claude Code's restricted PATH — a hook that assumes it works fails silently when it's missing. Field paths are tool-specific; reading `.tool_input.command` on a Write payload returns null and the hook becomes a no-op without surfacing the mismatch. Copilot uses `toolArgs` (a JSON string) instead of `tool_input` — a hook designed for Claude that runs under Copilot reads null and silently passes everything. Severity: `fail` for Copilot field-path mismatch; `warn` for missing availability check or field-path mismatch vs matcher's tool.

**How to apply:** add `command -v jq &>/dev/null || { echo "jq required" >&2; exit 2; }` near the top. Match the jq path to the matcher: Bash → `.tool_input.command`; Write → `.tool_input.file_path`; Edit/MultiEdit → `.tool_input.path`. For Copilot-capable hooks, branch on the payload shape and parse `toolArgs` as a JSON string.

```bash
command -v jq &>/dev/null || { echo "jq required" >&2; exit 2; }

# Cross-platform branching
PLATFORM=$(echo "$INPUT" | jq -r 'if .toolArgs then "copilot" else "claude" end')
case "$PLATFORM" in
  claude)   CMD=$(echo "$INPUT" | jq -r '.tool_input.command') ;;
  copilot)  CMD=$(echo "$INPUT" | jq -r '.toolArgs | fromjson | .command') ;;
esac
```

**Common fail signals (audit guidance):**
- `jq` invoked without an availability check — hook silently breaks on a Claude Code install missing jq.
- Matcher is `Bash` but the script reads `.tool_input.file_path` (Write's field) — null result, no-op.
- Hook intended for both Claude and Copilot reads `.tool_input.*` only — silently null on Copilot.
- jq path lookup with no `// "default"` fallback — `null` propagates into shell as the literal string `"null"`.
