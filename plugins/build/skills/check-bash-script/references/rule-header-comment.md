---
name: Header Comment Block
description: Include a header comment block in the first 10 lines naming purpose, usage signature, dependencies, and exit codes.
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Include a header comment block in the first 10 lines of every bash script naming purpose, usage signature, external dependencies, and exit codes.

**Why:** the header is the first thing a reader sees. A script without one is opaque — the reader has to parse `main` and infer intent from implementation. The four pieces are small and high-leverage: purpose answers "what does this do", usage answers "how do I invoke it", dependencies answer "what else needs to be installed", and exit codes answer "what does the calling script need to handle". A reader who hits an unfamiliar bash file finds these in ten seconds with the header; without it, they're spelunking.

**How to apply:** place the header immediately after the shebang, before `set -euo pipefail`. Use the canonical block: name + one-line purpose, blank, `Usage:` line(s), blank, `Dependencies:` line, blank, `Exit codes:` line. Keep it tight — five-or-six lines is typical, ten lines is the cap.

```bash
#!/usr/bin/env bash
#
# rotate-logs — Compress logs older than 30 days.
#
# Usage:
#   rotate-logs.sh [--dry-run] <log-dir>
#
# Dependencies: gzip, find
#
# Exit codes: 0 success, 1 failure, 64 usage error

set -euo pipefail

main() { ... }
```

**Exception:** trivially short scripts (under 20 non-blank lines, no external dependencies, single self-evident purpose) may omit the header. The audit emits WARN, not FAIL — judgment-level coaching. When in doubt, write the header.
