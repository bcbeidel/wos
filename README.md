# wos

A Claude Code plugin for building and maintaining structured project context
with AI-assisted research, source verification, and quality validation.

## What It Does

WOS helps teams create and maintain a structured knowledge base alongside their
code. It provides skills for creating context documents, verifying sources,
and auditing quality — so agents can find what they need and trust what they
find.

**Structured context** — Documents have YAML metadata (`name`, `description`,
optional `type`, `sources`, `related`). Auto-generated `_index.md` files
provide lookup tables at every directory level.

**Research quality** — The SIFT framework guides source evaluation. Source URLs
are verified programmatically (HTTP HEAD/GET) at creation time and during
audit. Research documents require non-empty `sources` lists.

**Agent navigation** — AGENTS.md contains a WOS-managed section
(`<!-- wos:begin -->` / `<!-- wos:end -->`) with navigation instructions,
an areas table, metadata format, and communication preferences.

## Skills

| Skill | Purpose |
|-------|---------|
| `/wos:create` | Create project context, areas, or documents |
| `/wos:audit` | Validate project health (5 checks + auto-fix) |
| `/wos:research` | SIFT-based research with source verification |
| `/wos:consider` | Mental models for problem analysis |
| `/wos:report-issue` | File GitHub issues against WOS repo |
| `/wos:preferences` | Capture communication preferences |

## Project Structure

```
wos/
  document.py          # Document dataclass + parse_document()
  index.py             # _index.md generation + sync checking
  validators.py        # 5 validation checks
  url_checker.py       # HTTP HEAD/GET URL reachability
  agents_md.py         # Marker-based AGENTS.md section management
  source_verification.py  # Full source verification with title matching
  preferences.py       # Communication preferences capture
scripts/
  audit.py             # CLI: run validation, offer fixes
  reindex.py           # CLI: regenerate all _index.md files
skills/                # Skill definitions (SKILL.md + references/)
tests/                 # pytest tests
artifacts/plans/       # Design docs and implementation plans
```

## Usage

```bash
claude --plugin-dir /path/to/wos
```

Or add to Claude Code settings for automatic loading.

## Dependencies

- Python 3.9+
- `pydantic>=2.0`, `pyyaml>=6.0`, `requests>=2.28`
- `gh` CLI (for report-issue skill)
