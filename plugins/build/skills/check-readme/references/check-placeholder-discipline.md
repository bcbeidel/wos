---
name: Placeholder Discipline
description: Every user-supplied value must be bracketed as a placeholder, defined exactly once, and used consistently — with no real secrets, tokens, hostnames, or IPs in examples.
paths:
  - "**/README.md"
  - "**/Readme.md"
---

Mark every user-supplied value as a placeholder (`<YOUR_API_KEY>`, `<PROJECT_ID>`), define each placeholder exactly once in Configuration or adjacent prose, and use the same token everywhere.

**Why:** Reader copies. Reader pastes. Reader hits prod. A README that mixes real-looking values (`sk-proj-abc123`) with placeholders trains readers to ignore the difference; a placeholder used in three blocks with no definition leaves them guessing. A URL that looks internal but is passed off as documentation invites accidental traffic to systems the reader does not own.
**How to apply:** Verify every user-supplied value is bracketed. Verify each placeholder is defined once and used consistently. Verify no production hostnames, tokens, or IPs appear in example blocks. Verify placeholder tokens are visually distinct from real values. If placeholders are undefined, inconsistent, or mixed with real values, define each placeholder once (typically in Configuration), use the same token everywhere, and swap any real-looking example values for `<...>`.

```bash
# Configuration: <YOUR_OPENAI_API_KEY> is your OpenAI API key.
export API_KEY="<YOUR_OPENAI_API_KEY>"
curl https://api.example.com/v1/models -H "Authorization: Bearer $API_KEY"
```

**Common fail signals (audit guidance):** `export API_KEY=sk-proj-abc123` (real-looking secret); `<YOUR_API_KEY>` used in three blocks with no definition; `<project>` used in some blocks and `my-project` in others; a URL like `https://api.acme-internal.corp.example` that looks internal but is passed off as documentation.
