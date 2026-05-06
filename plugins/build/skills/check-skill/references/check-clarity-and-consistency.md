---
name: Clarity and Consistency
description: Define domain jargon on first use, name each concept with one consistent term throughout, and avoid hedging the Tier-1 wordlist didn't catch.
paths:
  - "**/SKILL.md"
---

Speak in plain, direct English — define jargon on first use, pick one name per concept and use it everywhere, and replace non-obvious hedges with concrete conditions.

**Why:** Undefined jargon excludes readers who don't already share the author's domain context. Inconsistent naming (`service_name` → `svc` → `service_id`) forces re-derivation at every reference, multiplying the cognitive cost of every section. Tier-1 catches a fixed wordlist of hedges; the non-obvious tail ("where applicable", "if possible", "as needed") still propagates ambiguity into model behavior — the agent has to guess what "applicable" means at runtime, on every invocation, and may guess differently each time.

**How to apply:** Define each domain term on first use or link to a glossary. Pick one name per concept and use it throughout. Replace hedges like "where applicable" / "if possible" with the specific condition they hide ("when `$INPUT` is a CSV"), or delete them.

```markdown
The pipeline's upstream change-data-capture (CDC) source feeds into the
staging ELT, where `service_id` indexes into the registry. Apply the
transform when `service_id` is non-null; skip rows otherwise.
```

**Common fail signals (audit guidance):**
- Domain jargon or abbreviations used without definition on first use
- The same concept named differently in different sections (`service_name` → `svc` → `service_id`)
- Non-obvious hedging beyond the Tier-1 wordlist ("where applicable", "if possible", "as needed")
