---
name: GNU-Specific Flags
description: When using GNU-specific flags (`sed -i` without backup, `grep -P`, `readlink -f`, `date -d`, `stat -c`, `xargs -r`), declare the GNU-coreutils dependency in the header — or use a portable alternative.
paths:
  - "**/*.sh"
  - "**/*.bash"
---

When using GNU-specific flags — `sed -i` without backup, `grep -P`, `readlink -f`, `date -d`, `stat -c`, `xargs -r` — declare the GNU-coreutils dependency in the header comment, or use a portable alternative.

**Why:** `sed -i` accepts no argument on GNU and requires a backup-suffix argument on macOS/BSD. `grep -P` (Perl regex) is GNU-only. `readlink -f` resolves symlinks fully on GNU but errors on macOS without `-f` support. Silent cross-platform divergence is a recurring real-world failure: a script tested on Linux CI breaks on a developer's macOS laptop, or vice versa, with no clear error message — just wrong output or a cryptic flag error. The script needs to either declare its requirements (so a reader knows the script won't work elsewhere) or use a form that works everywhere.

**How to apply:** prefer portable alternatives where available — they cost nothing to write and remove the deployment risk. When the GNU form is genuinely needed (no clean portable rewrite), document the dependency in the header so a reader knows the script is GNU-bound.

```bash
# Option A — declare the dependency
#!/usr/bin/env bash
# rotate-logs — Compress logs older than 30 days.
# Dependencies: gnu-coreutils (sed -i without backup is GNU-only)

set -euo pipefail
sed -i 's/old/new/' file.txt
```

```bash
# Option B — portable form
sed 's/old/new/' file.txt > file.txt.new && mv file.txt.new file.txt
```

```bash
# Option B — portable date arithmetic
# GNU: date -d '30 days ago' +%Y-%m-%d
# Portable (requires perl):
perl -MPOSIX -e 'print strftime("%Y-%m-%d\n", localtime(time - 30*86400))'
```

**Exception:** scripts that explicitly target GNU-only environments (Linux containers, controlled CI runners) and have the dependency declared in the header. Without the declaration, the audit fires; with it, the script is documenting a real constraint and the audit accepts it.
