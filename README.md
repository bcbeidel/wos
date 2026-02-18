# work-os

Personal work operating system — a Claude Code plugin containing skills, agents, and hooks for daily workflows.

## Structure

```
.claude-plugin/
  plugin.json        # Plugin manifest
skills/              # Claude Code skills (each skill is a directory with SKILL.md)
agents/              # Custom agent definitions
hooks/               # Event-driven hook configurations
scripts/             # Shared utility scripts
```

## Usage

```bash
claude --plugin-dir /path/to/work-os
```

Or add to your Claude Code settings to load automatically.
