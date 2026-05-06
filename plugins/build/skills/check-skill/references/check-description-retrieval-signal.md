---
name: Description Retrieval Signal
description: Frontmatter `description` must front-load concrete invocation triggers a router can match on, not internal mechanics or capability prose.
paths:
  - "**/SKILL.md"
---

Write the `description` as a retrieval signal — lead with concrete invocation triggers (user phrases, file extensions, error strings, event types) so the router can match on observable user intent.

**Why:** The description is the router's primary retrieval signal. Capability phrasing ("handles tabular conversion") names what the skill contains — invisible at routing time. Trigger phrasing ("Use when the user asks to convert .csv to .parquet") names the situation that should invoke it, the only signal a router can observe. Generic tokens (`helper`, `utility`, `tools`) collapse the routing surface; without quoted user phrases, file extensions, or error strings, the description matches nothing specific and either over-fires or stays dark.

**How to apply:** Rewrite the first clause as a trigger framing — "Use when…" or equivalent. Name at least one concrete user phrase, file extension, error string, or event type. Use third-person, active voice; avoid second-person ("You can use this…") and passive voice. Keep the original purpose verbatim in the second clause if needed.

```yaml
description: Use when the user asks to convert .csv to .parquet, transform tabular data, or mentions "read_csv" / "to_parquet". Produces Parquet output with inferred schema.
```

**Common fail signals (audit guidance):**
- Description reads as capability ("Handles tabular conversion", "Processes data") rather than trigger ("Use when the user asks to convert .csv to .parquet")
- Starts in second person ("You can use this to…") or passive voice
- Generic tokens (`helper`, `utility`, `tools`, `thing`, `stuff`) used as the primary descriptor with no specific trigger
- No user-visible phrases a router would actually match against — no quoted user phrases, no file extensions, no error strings
