---
name: Bash Shebang
description: Begin every bash script with `#!/usr/bin/env bash` (or `#!/bin/bash` in tightly controlled environments where PATH is trusted).
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Begin every bash script with `#!/usr/bin/env bash` as the first line (or `#!/bin/bash` in tightly controlled environments where `PATH` is trusted).

**Why:** this skill is bash-only. A `#!/bin/sh` shebang invites silent bashisms-fail-on-dash bugs — `[[`, arrays, `${var/pattern/replacement}`, and `local` either don't work or work differently in `dash` and `busybox sh`. A missing shebang means the script runs under whatever shell the invoker happens to have, producing nondeterministic behavior that depends on the user's `$SHELL`. `#!/usr/bin/env bash` finds bash via `PATH`, which is portable across macOS (Homebrew bash at `/opt/homebrew/bin/bash`) and Linux (system bash at `/bin/bash` or `/usr/bin/bash`).

**How to apply:** ensure the file's first line is exactly `#!/usr/bin/env bash`. Use `#!/bin/bash` only when you can guarantee `/bin/bash` exists at version 4.0+ (locked-down container images, controlled internal environments). Never `#!/bin/sh`, `#!/usr/bin/python`, or any other shell — the file is bash, declare it bash.

```bash
#!/usr/bin/env bash
# rotate-logs — Compress logs older than 30 days.

set -euo pipefail
...
```

**Exception:** none. POSIX `sh` portability is a different concern with its own primitive (`/build:build-shell-script`). When the work needs `dash`/BusyBox/Alpine, that's a separate decision made before authoring; this rule applies to files routed to the bash skill.
