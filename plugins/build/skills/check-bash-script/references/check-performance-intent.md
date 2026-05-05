---
name: Performance Intent
description: Replace external-command calls inside loops with bash builtins or parameter expansion when feasible; each external invocation in a tight loop is a fork.
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Replace external-command calls inside loops with bash builtins or parameter expansion when feasible. Eliminate unnecessary subshells.

**Why:** each external invocation in a tight loop is a fork-and-exec — at scale, the loop becomes fork-dominated and the script's wall time is dominated by process creation overhead, not actual work. Parameter expansion (`${var##*/}` for basename, `${var%.*}` for extension stripping, `${var/pattern/replacement}` for substitution) runs in-process and is typically 100×+ faster. Subshells (`$(cmd)` that captures output, `(...)` that runs a block in a subshell) also fork — when the subshell isn't required for output capture or environment isolation, removing it saves cycles. The principle: loops are tight contexts; favor builtins.

**How to apply:** replace `basename`/`dirname`/`sed`/`awk` calls inside loops with parameter expansion when the operation is simple enough. Move `cat file | grep pattern` to `grep pattern file` (already covered by `rule-useless-cat.md`). Eliminate subshells where the substitution isn't required: `$(cmd)` is needed for output capture; `(cmd)` for isolating environment changes; otherwise, just `cmd`.

```bash
# Before — basename forks per iteration
for f in *.log; do
  base=$(basename "$f" .log)
  process "$base"
done

# After — parameter expansion, in-process
for f in *.log; do
  base="${f%.log}"
  base="${base##*/}"
  process "$base"
done
```

```bash
# Before — useless cat
cat file | grep pattern

# After — grep reads file directly
grep pattern file
```

```bash
# Before — date forks per log entry
for entry in "${log_entries[@]}"; do
  ts=$(date -d "$entry" +%s)
  process "$ts"
done

# After — extract timestamp once if all entries share a base
# or batch-convert outside the loop
```

**Common fail signals (audit guidance):**
- `for f in *.log; do basename "$f" .log; done` — use `${f%.log}` instead.
- `cat file | grep pattern` — use `grep pattern file`.
- A tight loop calling `date`, `wc`, `seq`, `tr` per iteration — opportunity to batch or use builtin.
- Unnecessary subshells: `result=$( echo "$x" )` where `result="$x"` would do.
- `$(echo "$var")` to "trim" a variable — parameter expansion `${var}` already does it.

**Exception:** scripts where readability matters more than performance and the loop iteration count is small (under ~100 iterations). The audit emits WARN — judgment-level, not blocking. Optimize the hot loops; leave the cold ones readable.
