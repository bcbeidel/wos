---
name: Read With -r Flag
description: Use `read -r` to disable backslash-escape interpretation when reading lines; without `-r`, `read` mangles input containing backslashes (shellcheck SC2162).
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Use `read -r` to disable backslash-escape interpretation when reading lines.

**Why:** without `-r`, `read` interprets `\` as a line-continuation or escape character — `read` followed by an input line ending in `\` reads the next line and concatenates them; an input line containing `\n` becomes a literal newline character; backslash-escape sequences are processed instead of preserved. For the common case of reading lines from a file or stdin, you almost always want the verbatim line, not bash's interpretation of it. The `-r` flag is one character of insurance against silent input mangling.

**How to apply:** add `-r` to every `read` that processes input lines. The full canonical form for line iteration is `while IFS= read -r line` — `IFS=` prevents leading/trailing whitespace stripping, `-r` prevents backslash interpretation.

```bash
# Before — backslashes mangled
while read line; do
  process "$line"
done < file

# After — verbatim lines
while IFS= read -r line; do
  process "$line"
done < file
```

```bash
# Single read from prompt
read -r -p "Enter path: " user_path
```

**Exception:** when you specifically want bash to interpret backslash escapes (rare — perhaps when reading a custom format that uses `\n` as a literal newline marker). Document the choice with a comment explaining why `-r` is omitted; the audit accepts the documented exception.

**See also:** `rule-for-line-in-cat.md` (SC2013) — sibling rule. The combined source recipe addressed both anti-patterns; this file is the `read -r` half.
