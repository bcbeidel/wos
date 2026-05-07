---
name: Tool Proportionality
description: The effective tool set matches the described workflow, and high-risk tools (`Bash` / `Write` / `Edit`) carry body-level scoping.
paths:
  - "**/.claude/agents/**/*.md"
  - "**/agents/**/*.md"
---

**Why:** Least privilege limits blast radius on misinterpretation or prompt injection. Every granted tool is an attack surface. An eight-tool allowlist is appropriate for a workflow that needs eight tools, but suspicious for a narrow single-verb workflow. `Bash`, `Write`, and `Edit` are high-risk; without body-level scoping (enumerated commands for `Bash`, path constraints for `Write` / `Edit`) a misinterpretation can do real damage.
**How to apply:** Anchor the assessment to the description. Remove tools the workflow does not use. For required high-risk tools, add body-level scoping: enumerated allowed commands for `Bash`, path constraints for `Write` / `Edit`. A read-only review agent should not list `Write` or `Edit`; an internal-only workflow should not list `WebFetch` or `WebSearch`.

```yaml
# Read-only reviewer
tools:
  - Read
  - Grep
  - Glob
```

**Common fail signals (audit guidance):**
- `Bash` granted without any body-level mention of command execution, shell operations, or running processes.
- `Write` / `Edit` granted to a read-only / review / reporting agent.
- `WebFetch` / `WebSearch` granted for an explicitly internal-only workflow.
- Effective tool set substantially wider than the described workflow (a narrow single-verb workflow with >6 tools in the allowlist).
- High-risk tool granted with no body-level scoping or path constraints.
