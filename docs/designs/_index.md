# Designs


Design documents for WOS features.

| File | Description |
| --- | --- |
| [2026-03-13-deploy-documentation.design.md](2026-03-13-deploy-documentation.design.md) | Update stale deploy design doc and create user-facing DEPLOYING.md guide |
| [2026-03-13-flexible-layout.design.md](2026-03-13-flexible-layout.design.md) | Decouple WOS document management from fixed directory hierarchies — discover documents by frontmatter, type by suffix/metadata, let users organize freely |
| [2026-03-23-challenge-skill.design.md](2026-03-23-challenge-skill.design.md) | Design for /wos:challenge — a skill that enumerates assumptions behind an output, sanity-checks them against project context and research, and proposes corrections for gaps |
| [2026-03-23-eval-framework.design.md](2026-03-23-eval-framework.design.md) | Design for a hybrid eval framework (YAML cases + Python scorers) supporting prompt performance monitoring, regression detection, and degradation alerting |
| [2026-03-27-pre-commit-ci-verification.design.md](2026-03-27-pre-commit-ci-verification.design.md) | Add shell-script pre-commit hook (ruff + version consistency) and extend CI with audit step |
| [2026-04-07-rule-extraction-enforcement.design.md](2026-04-07-rule-extraction-enforcement.design.md) | System for extracting codebase conventions into structured rule files and enforcing them via LLM-based semantic evaluation |
| [cross-platform-deploy-design.md](cross-platform-deploy-design.md) | Deploy script that symlinks WOS skills to project or platform directories for cross-platform agent discovery |
