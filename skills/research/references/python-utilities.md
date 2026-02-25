# Python Utilities Reference

CLI commands available during research sessions. All scripts are run from
the project root.

## Validate a Single Document

Runs all 4 checks: frontmatter, research sources, source URLs, related paths.

```bash
python3 scripts/validate.py <file> [--root DIR] [--no-urls]
```

Example:
```bash
python3 scripts/validate.py artifacts/research/2026-02-25-my-research.md --no-urls
```

Output on success:
```
All checks passed.
```

Output on failure:
```
[FAIL] artifacts/research/my-research.md: Research document has no sources
```

## Validate Entire Project

Runs all 5 checks across `context/` and `artifacts/`.

```bash
python3 scripts/audit.py [--root DIR] [--no-urls] [--json] [--fix]
```

## Format Search Protocol

Renders a search protocol JSON as a markdown table.

```bash
echo '<json>' | python3 -m wos.research_protocol format
echo '<json>' | python3 -m wos.research_protocol format --summary
```

### Search Protocol JSON Schema

```json
{
  "entries": [
    {
      "query": "search terms used",
      "source": "google",
      "date_range": "2024-2026 or null",
      "results_found": 12,
      "results_used": 3
    }
  ],
  "not_searched": [
    "Google Scholar - covered by direct source fetching",
    "PubMed - topic is not biomedical"
  ]
}
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `entries[].query` | string | Search terms used |
| `entries[].source` | string | Search engine (e.g., `google`, `scholar`, `github`, `docs`) |
| `entries[].date_range` | string or null | Date filter applied (e.g., `"2024-2026"`) |
| `entries[].results_found` | int | Total results returned |
| `entries[].results_used` | int | Results kept for evaluation |
| `not_searched` | list of strings | Sources not searched, with reason (e.g., `"Reddit - not relevant to topic"`) |

### Example Output (table)

```
| Query | Source | Date Range | Found | Used |
|-------|--------|------------|-------|------|
| python asyncio patterns | google | 2024-2026 | 12 | 3 |
| asyncio best practices | google | — | 8 | 2 |

**Not searched:** Google Scholar - covered by direct source fetching
```

### Example Output (summary)

```
2 searches across 1 source, 20 results found, 5 used
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
