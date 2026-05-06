---
name: Destructive-Op Safety
description: Destructive operations (rm, sudo, global install, deploy) are guarded with a confirmation that actually gates the command, scoped tightly, or reversible — beyond the Tier-1 mechanical checks.
type: judgment-rule
related:
  - ../SKILL.md
  - ../../../_shared/references/makefile-best-practices.md
---

# Destructive-Op Safety

Tier-1 catches unguarded `rm -rf $(VAR)`, `sudo`, global installs, and `curl | sh`. This dimension catches the failures Tier-1 can't see: a `CONFIRM` variable that's documented but never tested, a `clean` target whose scope is too broad, or destructive side effects hidden in innocuously-named targets.

## What to look for

- A `CONFIRM=1` pattern that's declared in the description but never appears as a guard in the recipe (decoration, not gate).
- `clean:` recipes that `rm -rf` directory trees broader than `$(BUILD_DIR)` and explicit artifacts (e.g., `rm -rf *.pyc node_modules .venv build`).
- Destructive side effects in non-destructive-named targets (a `fmt` target that rewrites `~/.gitconfig`; a `setup` that overwrites user files).
- Recursive `$(MAKE) -C subdir clean` invocations whose subdirectory's `clean` is itself unscoped.
- Confirmation guards that test the wrong thing (`[[ -n "$(CONFIRM)" ]]` accepts any non-empty value, including a stale `CONFIRM=0` from earlier).

## Severity

`warn` — most cases are coaching. A judge may escalate to `fail` for a destructive recipe with a malformed guard that fails open (e.g., a `deploy` whose `CONFIRM` check is commented out).

## Example finding

```json
{
  "status": "warn",
  "location": {"line": 87, "context": "deploy: ## Deploy (set CONFIRM=1)."},
  "reasoning": "The `deploy` target's description advertises CONFIRM=1 as a safety, but the recipe never tests $(CONFIRM). Accidental `make deploy` runs production deploy with no gate. The CONFIRM advertisement implies a safety that isn't there — worse than no advertisement at all.",
  "recommended_changes": "Add the guard as the first command in the recipe:\n\ndeploy: ## Deploy (set CONFIRM=1).\n\t@[[ \"$${CONFIRM:-0}\" = \"1\" ]] || { echo \"set CONFIRM=1 to deploy\" >&2; exit 1; }\n\t./scripts/deploy.sh"
}
```

## Recipe (canonical guidance)

**CHANGE** Wire the `CONFIRM=1` guard as the first command in every destructive recipe. Scope `clean` to `$(BUILD_DIR)` and an explicit allowlist.

**FROM**
```makefile
deploy: ## Deploy (set CONFIRM=1).
	# $(CONFIRM) is documented but never checked
	./scripts/deploy.sh
```

**TO**
```makefile
deploy: ## Deploy (set CONFIRM=1).
	@[[ "$${CONFIRM:-0}" = "1" ]] || { echo "set CONFIRM=1" >&2; exit 1; }
	./scripts/deploy.sh
```

**REASON** A `CONFIRM` variable nobody checks is worse than no `CONFIRM` at all — it implies a safety that isn't there. The guard belongs as the first command in the recipe so accidental invocation no-ops cleanly.
