---
name: Installation Correctness
description: Prerequisites must name every runtime, tool, and external service with minimum versions; install commands must succeed top-to-bottom on a freshly provisioned machine.
paths:
  - "**/README.md"
  - "**/Readme.md"
---

List versioned prerequisites before install commands, cover every supported platform with its own labeled command block, and never assume preexisting state silently.

**Why:** First-run failure is the largest source of abandoned adoption — a reader who hits a missing dependency, a wrong package manager, or a hidden setup step on their first attempt does not return. "Just run `make install`" with no Make prerequisite, a Node command without a Node version, or a macOS-only `brew` recipe in a project that claims Linux support all break the implicit promise that copy-pasted commands will work.
**How to apply:** Verify the Prerequisites list names every runtime, tool, and external service the reader needs, with minimum versions. Verify the install commands would succeed on a clean machine that has only the prerequisites. If the project supports multiple platforms, verify each is covered with a labeled command block. Verify destructive install steps (database migrations, filesystem modifications) are noted. If commands would fail on a clean machine, add the missing prerequisites with versions, list any hidden setup steps, and test on a fresh VM or container.

```markdown
## Prerequisites
- Python 3.9+
- PostgreSQL 14+ (running locally or accessible via `DATABASE_URL`)
- `make` 4.0+

## Installation
```bash
pip install -e .
make migrate
```
```

**Common fail signals (audit guidance):** "Just run `make install`" with no Make prerequisite listed; Node install command with no Node version; macOS-only `brew` install in a project that claims Linux support.
