# Python Utilities Reference

CLI commands available during research sessions. All commands use
`${CLAUDE_PLUGIN_ROOT}` to resolve script paths — this variable is set
automatically by Claude Code when the plugin is active.

## Validate a Single Document

Runs all checks: frontmatter, content length, source URLs, related paths.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/audit.py" <file> [--root DIR] [--no-urls]
```

Example:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/audit.py" artifacts/research/2026-02-25-my-research.md --root . --no-urls
```

Output on success:
```
All checks passed.
```

Output on failure:
```
1 fail, 0 warn across 1 files

file                                     | sev  | issue
artifacts/research/my-research.md        | fail | Research document has no sources
```

## Validate Entire Project

Runs all checks across `context/` and `artifacts/`.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/audit.py" [--root DIR] [--no-urls] [--json] [--fix] [--strict]
```

## Regenerate Index Files

Regenerate all `_index.md` files under `context/` and `artifacts/`.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/reindex.py" [--root DIR]
```

## Document Model

The `Document` dataclass fields relevant to research:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | Yes | Concise title |
| `description` | string | Yes | One-sentence summary |
| `type` | string | No | Set to `research` for research docs |
| `sources` | list of strings | For research | URLs of verified sources |
| `related` | list of strings | No | Relative paths to related documents |
