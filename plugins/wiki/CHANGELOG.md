# Changelog

## 0.5.3

- Cycle 4 process-echo guard sweep: drop `wiki/setup` Anti-Pattern Guard
  #2 ("Overwriting content outside managed markers") — restated the
  Key Instruction "Won't overwrite content outside managed markers"
  verbatim. Section drops from 3 to 2 guards; both retained guards
  name distinct non-obvious failure modes (uncommitted-changes
  precondition, current-state idempotency check).

## 0.5.2

- Trigger-cap sweep: cap each SKILL.md description to ≤3 quoted phrases;
  surplus phrases relocated to `## When to use` (#429, refs #399).
  Touches `ingest`, `lint`, and `research` skill descriptions.
