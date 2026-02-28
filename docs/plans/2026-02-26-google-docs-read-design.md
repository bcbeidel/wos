---
name: Google Docs Read Integration Design
description: Design for reading Google Docs content via a PEP 723 script and /wos:read skill
type: plan
related:
  - docs/research/2026-02-24-google-apis-research.md
  - docs/research/2026-02-24-oauth-token-management-research.md
  - docs/research/2026-02-24-ai-integration-patterns-research.md
---

# Google Docs Read Integration Design

**Date:** 2026-02-26
**Issue:** #41
**Prerequisite:** #70 (reliable uv run invocation from skills)

## Problem

WOS has no way to read external documents. Users working with Google Docs must
manually copy-paste content into WOS context files. Two use cases are unserved:

1. **Live read** — Claude reads a Google Doc during a session to answer questions
   or inform decisions, without saving it locally.
2. **Ingest** — Pull Google Doc content into a WOS context file with proper
   frontmatter, linking the source URL.

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Implementation style | PEP 723 script with `uv run` | Keeps WOS stdlib-only; script declares its own deps inline; full code visibility (no MCP) |
| Architecture | Single script per platform | YAGNI — no PlatformAdapter abstraction until Microsoft is added |
| Platform scope | Google Docs only (v1) | Ship one integration well; Microsoft Graph follows later |
| OAuth client | User provides their own | No shared credentials, no Google verification requirement |
| Auth flow | Browser-based with console fallback | Covers both desktop and headless/SSH environments |
| Skill design | New standalone `/wos:read` | Clean separation from `/wos:create`; read is its own concern |
| Script path resolution | Deferred to #70 | Prerequisite solves this for all scripts, not just this one |

## Architecture

### Script: `scripts/google_docs.py`

Single self-contained PEP 723 script with three subcommands:

```
uv run scripts/google_docs.py auth [--force] [--client-secret PATH]
uv run scripts/google_docs.py read <doc-url> [--json]
uv run scripts/google_docs.py list [--limit N] [--query TEXT]
```

**Inline dependencies (PEP 723):**

```python
# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "google-api-python-client>=2.0",
#   "google-auth-oauthlib>=1.0",
# ]
# ///
```

### Subcommands

**`auth`** — OAuth setup and token management.

1. Check for existing valid token at `~/.config/wos/google-token.json`
2. If no token or `--force`:
   - Try `InstalledAppFlow.run_local_server()` (opens browser)
   - If no display/headless, fall back to `run_console()` (print URL, paste code)
3. Store credentials to `~/.config/wos/google-token.json` with `0600` permissions
4. Print confirmation with granted scopes
5. `--check` flag: silent check, exits 0 if authed, 1 if not (for skill preflight)

Client secret location: `~/.config/wos/google-client-secret.json` or `--client-secret <path>`.

**`read`** — Fetch and convert a Google Doc to markdown.

1. Parse document ID from URL (`_parse_doc_url()`)
2. Load and refresh auth token
3. Call `documents.get(documentId=doc_id)` via Docs API
4. Extract content via `_extract_text(doc_json)` → markdown string
5. Output to stdout (default: markdown, `--json`: raw API response)

**`list`** — Discover documents by title or search.

1. Load auth token
2. Call Drive API `files.list` with `mimeType='application/vnd.google-apps.document'`
3. Optional `--query` maps to Drive search (`name contains 'text'`)
4. Output compact table: title, last modified, URL

### OAuth Scopes

| Scope | Purpose |
|-------|---------|
| `documents.readonly` | Read document content via Docs API |
| `drive.metadata.readonly` | List documents by name/date via Drive API |

No write scopes requested. Ever.

### Text Extraction: `_extract_text(doc_json) -> str`

Walks the nested Google Docs API JSON structure and produces markdown:

| Element | Markdown output |
|---------|----------------|
| Paragraph | Plain text with newlines |
| HEADING_1 through HEADING_6 | `#` through `######` |
| Bold | `**text**` |
| Italic | `*text*` |
| Bullet list | `- item` (nested with indentation) |
| Numbered list | `1. item` |
| Table | Markdown table (`\| col \| col \|`) |
| Link | `[text](url)` |
| Image/drawing | `[image]` (skipped) |

Goal is readable text for Claude and humans, not round-trip fidelity.

### Token Storage

```
~/.config/wos/
├── google-client-secret.json   # User downloads from Google Cloud Console
└── google-token.json           # Auto-managed by auth subcommand (0600)
```

Token refresh is automatic — `google-auth` handles expiry and refresh on each
API call. Refresh tokens don't expire (until revoked by user).

Security: no tokens in stdout, no tokens in error messages.

### Skill: `/wos:read`

New skill that orchestrates the Google Docs script.

**Triggers:** "read a google doc", "pull in this document", "ingest this doc",
"what does this doc say", "read document"

**Flow:**

1. Preflight: verify `uv run` works (#70 pattern)
2. Auth check: `uv run scripts/google_docs.py auth --check`
   - If not authed, guide user through setup
3. If user provided a URL: `read <url>`
   If user needs to find a doc: `list [--query ...]`, then `read`
4. Based on user intent:
   - **Live read:** Present markdown content in conversation
   - **Ingest:** Hand off to `/wos:create` with content, adding doc URL to `sources:`

## Testing

**Unit tests (CI, no credentials):**
- `_extract_text()` — markdown extraction from fixture JSON files
- `_parse_doc_url()` — URL parsing for various Google Docs URL formats
- CLI argument parsing and routing

**Fixture data:** Sanitized Google Docs API response JSONs in `tests/fixtures/`.
Cover: simple paragraphs, headings, lists, tables, mixed formatting.

**Integration tests (manual, with credentials):**
- Marked with `@pytest.mark.integration`, skipped by default
- Full round-trip: auth → read → verify output
- Run with: `pytest tests/ -m integration`

## What's Not Included (YAGNI)

- PlatformAdapter protocol / shared abstractions — build when Microsoft is added
- Comments or suggestions — separate issues (#43)
- Calendar integration — separate issues (#42, #44)
- Shipped OAuth client ID — user provides their own
- Microsoft Graph support — future follow-up with a separate `scripts/microsoft_docs.py`

## Implementation Order

Dependencies flow downward:

- [ ] **#70: Reliable uv run invocation** (prerequisite — path resolution + preflight pattern)
- [ ] Parse doc URL utility + tests
- [ ] Text extraction (`_extract_text`) + tests with fixture JSON
- [ ] Auth subcommand (OAuth flow, token storage)
- [ ] Read subcommand (API call + extraction)
- [ ] List subcommand (Drive API)
- [ ] `/wos:read` skill definition
- [ ] Integration tests
- [ ] Update issue #41 acceptance criteria and close
