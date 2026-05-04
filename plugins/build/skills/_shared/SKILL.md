---
name: _shared
description: >-
  Shared reference catalog for the build plugin — distilled best-practices
  documents and the cross-skill primitive-routing guide that every build-*
  and check-* skill cites. Not a procedure: build/check skills load specific
  files via their `references:` frontmatter. Exists so the skill-scanner can
  index this directory and so authors have a single landing page for the
  shared rubric set.
user-invocable: false
disable-model-invocation: true
version: 1.0.0
owner: build-plugin
license: MIT
---

# _shared — Build Plugin Reference Catalog

This directory holds reference material consumed by every build-* and
check-* skill in the plugin. It is not invoked directly. The SKILL.md
exists to satisfy the skill-scanner's "every directory under `skills/`
contains a SKILL.md" contract, and to give Claude a navigable index of
what lives here.

## Contents

- `references/primitive-routing.md` — the cross-skill routing guide
  that explains when to reach for each primitive (rule, skill, hook,
  subagent, makefile, README, workflow, resolver, help-skill). Cited
  by every build-* skill.
- `references/skill-best-practices.md` — distilled SKILL.md authoring
  rubric. Both `/build:build-skill` and `/build:check-skill` read from
  it.
- `references/skill-pair-best-practices.md` — authoring rubric for
  matched build-/check- pairs.
- `references/skill-locations.md` — where a SKILL.md belongs on disk
  (plugin vs. project, agent vs. user-invocable).
- `references/brief-best-practices.md` — guidance for the intake
  brief skills request before scaffolding.
- `references/<primitive>-best-practices.md` — one rubric per matched
  primitive pair (bash-script, python-script, makefile, hook, rule,
  subagent, readme, github-workflow, pre-commit-config, help-skill,
  resolver). Both halves of each pair read from the same file.

## How build/check skills consume these

Each skill declares relative paths in its frontmatter so the harness
loads them eagerly into context:

```yaml
references:
  - ../_shared/references/skill-best-practices.md
  - ../_shared/references/primitive-routing.md
```

Inline content should never duplicate what lives here. If a shared
rubric needs to change, edit the file in this directory once and every
skill that cites it picks up the change.

## Adding a new shared reference

Use `/build:build-skill-pair <primitive>` — it creates the principles
doc at `references/<primitive>-best-practices.md`, both halves of the
matched pair, and the routing entry in `primitive-routing.md`. Do not
hand-author files here in isolation; the pair authoring step is what
keeps the build/check sides synchronized.
