---
name: Avoid Eval of Array
description: Pass array contents directly without `eval`; `eval "${cmd[@]}"` re-parses expanded values, re-introducing injection vulnerability (shellcheck SC2294).
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Pass array contents directly with `"${cmd[@]}"` — never `eval "${cmd[@]}"`.

**Why:** `eval "${cmd[@]}"` performs a second shell-parsing pass over the already-expanded array values. If any element contains a space, a quote, or shell metacharacters, the second pass re-parses them — which is precisely the injection vulnerability the array form was supposed to prevent. The whole point of using arrays for command construction is that `"${cmd[@]}"` expands each element into one argument, preserving spaces and special characters; wrapping the expansion in `eval` discards that protection. The fix is mechanical: just remove the `eval`.

**How to apply:** replace `eval "${cmd[@]}"` with `"${cmd[@]}"`. If the goal was dynamic command dispatch and the developer thought `eval` was needed — it isn't. Arrays already do this correctly.

```bash
# Before — re-parses array contents through the shell
cmd=(rm -rf "$user_input")
eval "${cmd[@]}"

# After — array expansion preserves arg boundaries
cmd=(rm -rf "$user_input")
"${cmd[@]}"
```

```bash
# Building up a command with conditional flags
cmd=(curl)
[[ "$verbose" == 1 ]] && cmd+=(-v)
cmd+=(-H "Authorization: Bearer $token")
cmd+=("$url")

# Run it — no eval
"${cmd[@]}"
```

**Exception:** none. The fix is to remove the `eval`. If a script genuinely needs dynamic shell parsing (rare, almost always unsafe), see `rule-eval.md` — but it's a separate concern with its own audit.
