# toolkit

> **Experimental** — This project is under active development. APIs, skill
> interfaces, and document conventions may change without notice.

A Claude Code plugin marketplace for building and maintaining structured project context,
with AI-assisted research, source verification, and quality validation.

For Claude Code users who want reusable tooling for skill authoring, project
documentation, task planning, and structured reasoning — packaged as four
independently installable plugins.

## Prerequisites

- Python 3.9+
- No runtime Python dependencies (stdlib only)
- `gh` CLI (for `work:finish-work` skill)

## Plugins

Four self-contained plugins, each independently installable:

| Plugin | Install | Skills |
|--------|---------|--------|
| `wiki` | `claude plugin install bcbeidel/toolkit --plugin wiki` | `setup`, `research`, `ingest`, `lint` |
| `build` | `claude plugin install bcbeidel/toolkit --plugin build` | 26 skills for creating and auditing Claude Code primitives (skills, rules, hooks, subagents, scripts, configs) |
| `work` | `claude plugin install bcbeidel/toolkit --plugin work` | `scope-work`, `plan-work`, `start-work`, `verify-work`, `finish-work` |
| `consider` | `claude plugin install bcbeidel/toolkit --plugin consider` | 16 mental models + meta |

## Installation

**Knowledge** — build and maintain project context documents:
```bash
claude plugin install bcbeidel/toolkit --plugin wiki
```

**Build tooling** — create, audit, and maintain Claude Code skills and rules:
```bash
claude plugin install bcbeidel/toolkit --plugin build
```

**Full suite** — complete toolkit for AI-assisted project work:
```bash
claude plugin install bcbeidel/toolkit --plugin wiki
claude plugin install bcbeidel/toolkit --plugin build
claude plugin install bcbeidel/toolkit --plugin work
claude plugin install bcbeidel/toolkit --plugin consider
```

## Usage

Once installed, invoke a plugin's skills via the `/plugin:skill-name` syntax
in Claude Code. For example, after installing the `wiki` plugin:

```text
/wiki:setup
```

Expected: Claude Code initializes project context directories and prompts
for any missing metadata.

See each plugin's skill directory for the full skill catalogue
(`plugins/<plugin>/skills/`).

## Local Development

```bash
pip install -e plugins/wiki -e ".[dev]"

python -m pytest plugins/wiki/tests/ -v

ruff check plugins/
```

## Project Structure

```text
plugins/
  build/       # Skill authoring and auditing
  wiki/        # Project context: setup, research, ingest, lint
    src/wiki/  # Python package
    scripts/   # Shared CLI scripts
    skills/    # Skill definitions
    tests/     # Unit tests
  work/        # Task scoping, planning, execution
  consider/    # Structured mental models
.context/      # Domain knowledge and conventions
.plans/        # Implementation plans
.research/     # Research investigations
.prompts/      # Saved and refined prompts
.claude-plugin/
  marketplace.json
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
