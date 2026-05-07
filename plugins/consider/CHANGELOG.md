# Changelog

## 0.2.0

- **Cycle 5 rows 2 + 24**: simplify `consider` skills.
  - Row 2: replace the 17-row `## Available Models` table in
    `consider/SKILL.md` with a one-line invocation note pointing at the
    marketplace listing.
  - Row 24: drop the `- Does not X; produces Y` Key Instructions
    bullets across 16 mental-model SKILLs (`<objective>` blocks already
    convey the positive scope). Meta `consider/SKILL.md` also drops its
    "Does not execute implementations" bullet. `pick-model` is out of
    scope — its bold `**Does not recommend...**` bullets serve a
    different rhetorical role.

## 0.1.3

- Add `license: MIT` to skill frontmatter; teach the scaffolder and
  `check-skill` to expect the field (#375)

## 0.1.2

- Add `pick-model` skill — AI model selection advisory based on external
  benchmarks, cross-provider pricing, and effort/stakes tradeoffs
- Add `pick-model` to `consider` meta-skill routing table
- Add `references/model-landscape.md` with benchmark tables, pricing
  comparison, and effort controls by provider (data as of April 2026)

## 0.1.1

- Skill quality audit — add Handoff, Anti-Pattern Guards, Key Instructions
  to all 17 skills (#306)
- Metadata correctness and lint accuracy fixes (#296)

## 0.1.0

- Initial release with 16 mental models + `consider` meta-skill (#264)
