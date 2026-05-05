---
name: Avoid Eval
description: Avoid `eval`; use targeted constructs (`case`, parameter expansion, dispatch tables) instead. `eval` on input is shell injection.
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Avoid `eval`; use targeted constructs — `case`, parameter expansion, dispatch arrays — instead.

**Why:** `eval` on user input is shell injection — full stop. Any `eval "$x"` where `$x` came from outside the script is a remote-code-execution vulnerability waiting to happen. Even `eval` on internal values is fragile: it performs a second shell-parsing pass over the expanded string, re-introducing word-splitting, glob expansion, command substitution, and quote interpretation. Most legitimate `eval` uses turn out to be pattern matches that `case` handles safely, or function dispatches that arrays handle safely. The cases where `eval` is genuinely irreplaceable are rare; treat each one as requiring justification.

**How to apply:** replace `eval` with explicit constructs. For action dispatch, `case` is almost always clearer and safer. For dynamic command construction, build an array and execute it directly. If `eval` is genuinely required (rare), justify it with `# shellcheck disable=SC2294 # <reason>` or `# eval-justified: <reason>` so the audit knows to allow this specific instance.

```bash
# Before — eval on action dispatch
eval "$action"

# After — explicit case
case "$action" in
  start) start_server ;;
  stop)  stop_server  ;;
  reload) reload_config ;;
  *)     die "unknown action: $action" ;;
esac
```

```bash
# Before — eval to construct command
eval "cmd $args"

# After — array
cmd_args=(--flag value --other "$value_with_spaces")
some_command "${cmd_args[@]}"
```

**Exception:** documented `eval` usage with `# shellcheck disable=SC2294 # <reason>` or a `# eval-justified: <reason>` comment on the same or preceding line. The justification names what the script is doing and why no alternative works. Genuine examples are rare — emitting a positive verdict requires the reader to be convinced.
