---
name: Cross-Entity Collision
description: When multiple scripts in the same directory duplicate helpers (`die`, `usage`, `preflight`) or argument-parsing logic, extract the shared block into a sourced helper file.
paths:
  - "**/*.sh"
  - "**/*.bash"
---

**Why:** shared utilities maintained in triplicate drift. One script's `die` gets a logging tweak; the second script's stays plain; the third grows a sentry hook. Six months later the team has three different "the same" helpers and no source of truth — the small fixes that were supposed to be one-line changes become three-place updates that don't all happen. A single sourced helper keeps the contract coherent across the whole script collection. The exception is genuine: scripts that happen to look alike but won't co-evolve (different teams, different deployment paths, different lifecycles) should accept the duplication. DRY applies to scripts that will co-evolve, not scripts that happen to look alike at a moment in time.

**How to apply:** identify duplicated helpers across two or more scripts in the same directory. Extract them into `<dir>/_helpers.sh` (the underscore prefix marks it as a sub-resource, not a directly-runnable script). Replace the per-script copies with `source "$(dirname "${BASH_SOURCE[0]}")/_helpers.sh"`. Keep the helpers narrowly scoped — `_helpers.sh` should be a small set of clearly named functions, not a kitchen-sink library. If only one script uses a function, leave it inline; extract only on the second or third occurrence.

```bash
# _helpers.sh
die() { printf 'error: %s\n' "$*" >&2; exit 1; }
usage() { sed -n '/^# Usage:/,/^$/p' "${BASH_SOURCE[1]}" | sed 's/^# //'; }
preflight() {
  local cmd missing=()
  for cmd in "$@"; do
    command -v "$cmd" >/dev/null || missing+=("$cmd")
  done
  [[ "${#missing[@]}" -eq 0 ]] || die "missing required commands: ${missing[*]}"
}

# script1.sh
#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_helpers.sh"

main() {
  preflight jq curl
  ...
}

[[ "${BASH_SOURCE[0]}" == "${0}" ]] && main "$@"
```

**Audit guidance:** this rule fires only when the audit scope holds multiple scripts in the same directory. Single-script audits return INAPPLICABLE — there's nothing to collide with. The judgment call is whether the duplication is genuine (will co-evolve, should be consolidated) or coincidental (separate lifecycles, leave alone). Surface the highest-signal duplication; don't enumerate every minor overlap.

**Exception:** scripts that share an authoring pattern but exist on different release tracks, are owned by different teams, or have explicit one-way-door reasons to stay independent. Document these cases — a comment in the script ("intentional duplicate; lives separately because X") prevents the next maintainer from "fixing" it.
