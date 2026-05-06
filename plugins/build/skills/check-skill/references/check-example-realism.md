---
name: Example Realism
description: `## Examples` must use real domain identifiers, show side effects, and avoid synthetic placeholders — `foo`/`bar`/`Widget` and `"example"` strings do not anchor the skill.
paths:
  - "**/SKILL.md"
---

Anchor with a concrete example — use realistic file paths, parameter values, and error messages from the skill's actual domain, and show the inputs, outputs, and side effects all in one fenced block.

**Why:** Synthetic placeholders defeat the point of the example. `foo`/`bar`/`Widget` identifiers force the reader to translate the example into the actual domain on every reading — and translation is exactly the work the example was supposed to eliminate. Models copy-paste better than they translate prose; an example with `data/raw/orders-2026-04-22.csv` lets the agent recognize the shape and apply the skill the way it would to new cases. Examples that hide side effects (a skill that writes a file but shows no output) leave the reader unable to verify success.

**How to apply:** Replace placeholders with realistic domain identifiers — real file paths, real parameter values, realistic error messages. Show inputs, outputs, and side effects all visible in at least one example. A file-path comment showing provenance is a strong optional signal.

```bash
./scripts/convert.sh \
  --input data/raw/orders-2026-04-22.csv \
  --output data/staging/orders-2026-04-22.parquet
# Writes ~2.3MB parquet (1.8M rows); prints "schema inferred: order_id INT64, order_date DATE, ..."
```

**Common fail signals (audit guidance):**
- Examples use generic placeholders (`foo`, `bar`, `baz`, `myFunction`, `Widget`, `Thing`) as primary identifiers
- Example inputs are `"example"` / `"test"` / `"placeholder"` strings rather than realistic values
- Side effects are not shown — a skill that writes a file provides no sample output
- Example is a command template with `<>` placeholders and no concrete invocation
