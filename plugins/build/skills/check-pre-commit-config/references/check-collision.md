---
name: Cross-Entity Collision
description: When multiple local hook scripts live under `scripts/hooks/`, surface duplicated helpers (`die`, `usage`, validation, per-file iteration) the maintainer could consolidate into `scripts/hooks/_helpers.sh`.
paths:
  - "**/.pre-commit-config.yaml"
  - "**/.pre-commit-config.yml"
---

When multiple local hook scripts live under `scripts/hooks/`, surface duplicated helpers (`die`, `usage`, input validation, per-file iteration loops) the maintainer could consolidate into `scripts/hooks/_helpers.sh`.

**Why:** Duplicated logic in hook scripts drifts over time — *Patterns That Work* recommends custom logic in `scripts/hooks/`, and a single source of truth keeps that logic coherent. Three scripts each carrying their own copy of `die() { printf 'error: %s\n' "$*" >&2; exit 1; }` and a per-file `for file in "$@"` loop are three places where the next maintainer might fix a bug — and only fix it in one. Consolidation is mechanical and the payoff compounds with every new hook.

**How to apply:** When two or more local hook scripts exist under `scripts/hooks/`, scan for repeated blocks: `die` / `usage` / argparse-like skeletons, identical `for file in "$@"` iteration loops, identical input-validation idioms. Surface the highest-signal duplicate in a single finding; recommend extracting into `scripts/hooks/_helpers.sh` and `source`-ing from each script. Single-script scope returns inapplicable silently.

```bash
# scripts/hooks/_helpers.sh
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

iterate_files() {
  local handler="$1"; shift
  local file
  for file in "$@"; do
    "$handler" "$file" || die "$handler failed on $file"
  done
}
```

```bash
# scripts/hooks/validate_schema.sh
source "$(dirname "${BASH_SOURCE[0]}")/_helpers.sh"
```

**Common fail signals (audit guidance):** `die() { ... }` and per-file iteration loop copied across three scripts in `scripts/hooks/`; identical 5-line argparse / `usage` skeletons in two or more hook scripts.
