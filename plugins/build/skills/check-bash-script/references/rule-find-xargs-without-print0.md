---
name: Pair find -print0 with xargs -0
description: Pair `find ... -print0` with `xargs -0` (or use `find -exec ... {} +`); default whitespace separation breaks on filenames with spaces (shellcheck SC2038).
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Pair `find ... -print0` with `xargs -0` (or use `find ... -exec cmd {} +`); the default whitespace separation in `xargs` breaks on filenames with spaces or newlines.

**Why:** the default separator in `xargs` is whitespace — a filename containing a space gets split into two arguments to the downstream command. `find ... | xargs rm` will happily run `rm "my" "report.txt"` against a file named `my report.txt`. The `-print0`/`-0` pair switches both sides to null-byte separation; null bytes can't appear in filenames, so the separation is unambiguous regardless of the filename's contents. The `-exec ... {} +` form does the same thing without the pipeline — `find` invokes the command directly with batched arguments, no separator issue at all.

**How to apply:** add `-print0` to the `find` and `-0` to the `xargs`. For simple cases, prefer `-exec ... {} +` — it's slightly faster (no pipe), reads cleanly, and removes the need to remember the separator pair.

```bash
# Before — breaks on filenames with spaces
find . -name '*.log' | xargs rm

# After — null-separated
find . -name '*.log' -print0 | xargs -0 rm

# After — exec form
find . -name '*.log' -exec rm {} +
```

**Exception:** when the downstream command genuinely needs whitespace-separated input and the filenames are guaranteed safe (no spaces, no newlines). Such guarantees are fragile in real-world directories; the audit prefers the null-separated forms by default.
