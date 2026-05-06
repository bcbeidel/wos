---
name: Staleness
description: Describe the codebase as it is — referenced paths, commands, and imports must still exist.
paths:
  - "**/.claude/rules/*.md"
  - "**/.claude/rules/**/*.md"
---

Reference only paths, commands, framework imports, and patterns that exist in the current codebase. Update references when the codebase moves; delete the rule when the convention is retired.

**Why:** A rule that scopes itself to a non-existent directory never fires — Claude silently never sees it. Stale examples actively mislead Claude by teaching the wrong pattern (an old import path, a deprecated command). A rule referencing a dependency not in the project's manifest signals either the rule is stale or the manifest drifted; either way, the rule isn't doing what the author thought. Staleness is the most common decay mode for rule libraries because nothing surfaces it until you audit.

**How to apply:** Scan `paths:` globs, code-block examples, and prose for file paths, command names, framework imports, and pattern names. Then check the codebase: do those paths exist? Do those commands and imports still appear? When `paths: "app/legacy/**/*.rb"` references a directory removed in a refactor, update to the replacement layer (`paths: "app/services/**/*.rb"`) or delete the rule. When an example uses `import { Logger } from '@old-org/logging'` and the package was replaced six months ago, rewrite with the current import. If no current pattern exists, the rule itself is likely stale and should be deleted.

```yaml
paths:
  - "src/api/**/*.ts"   # src/api/ exists in the current tree
```

**Common fail signals (audit guidance):**
- `paths:` glob references a directory that does not exist
- Code-block examples reference functions, imports, or modules not found in the codebase
- Prose references a dependency or framework not in the project's manifest
- Rule mentions a deprecated convention that has been replaced
