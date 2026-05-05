---
name: Tmp Path Literal
description: Use `mktemp` plus a cleanup trap; avoid hardcoded `/tmp/` and `/var/tmp/` paths because predictable names invite races and symlink attacks.
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Use `mktemp` plus a cleanup trap for temporary files and directories; avoid hardcoded `/tmp/` and `/var/tmp/` paths.

**Why:** predictable temp paths invite races (other processes can guess the name and create or modify the file before the script writes it) and symlink attacks (a malicious symlink at the expected location redirects writes elsewhere — into `/etc/passwd`, into root-owned config). `mktemp` produces a path with random suffixes that the OS guarantees doesn't already exist, eliminating both classes of vulnerability. The trap pairing (see `rule-mktemp-trap-pairing.md`) ensures the temp resource is cleaned up on any exit, including signals.

**How to apply:** replace literal `/tmp/...` and `/var/tmp/...` paths with `mktemp` invocations. Use `mktemp` (no flags) for files; `mktemp -d` for directories. Capture the path in a variable and register an `EXIT INT TERM` trap immediately. The OS-default temp directory (`$TMPDIR` on macOS, `/tmp` on Linux) is fine — `mktemp` finds it.

```bash
# Before — predictable path; race + symlink risk
out="/tmp/work_$$"
do_work > "$out"

# After — random name + trap cleanup
out="$(mktemp)"
trap 'rm -f "$out"' EXIT INT TERM
do_work > "$out"
```

```bash
# Directory variant
tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT INT TERM
do_work_in "$tmpdir"
```

**Exception:** none. Even seemingly-safe patterns like `/tmp/$$` (PID-suffixed) are predictable — PIDs are guessable and roll over. `mktemp` is the answer; the only reason to skip it is "I don't know about it", which is what this rule fixes.
