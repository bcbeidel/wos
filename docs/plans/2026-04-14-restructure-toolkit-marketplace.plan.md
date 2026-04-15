---
name: Restructure wos into toolkit marketplace
description: Split the wos monorepo into a Claude Code plugin marketplace with 5 self-contained plugins — build, check, wiki, work, consider
type: plan
status: executing
branch: restructure/toolkit-marketplace
related: []
---

# Goal

Restructure the `wos` repo into a Claude Code plugin marketplace named `toolkit`
(`github.com/bcbeidel/toolkit`), containing 5 self-contained, independently installable
plugins under a `tools/` directory. Each plugin owns its Python code, scripts, skills,
and tests.

# Scope

## Must Have
- `tools/` marketplace container with 5 plugin subdirectories
- Each plugin has a valid `.claude-plugin/plugin.json`
- `marketplace.json` at repo root
- `wiki` and `check` plugins have self-contained Python packages
- All 21 skills migrated to new plugins with new names
- 16 `consider` commands converted to `consider` plugin skills
- `_shared/references/` distributed to owning plugins
- Tests migrated and passing against new package structure
- CI updated for new structure
- Root `pyproject.toml` retained for dev tooling only

## Won't Have
- GitHub repo rename (manual step, post-merge)
- `_index.md` files (removed from repo; library no longer generates them)
- New skills or features
- Skill content changes beyond the pre-requisite fix already applied: removing 5 cross-plugin `_shared/references/` entries from `start-work` frontmatter (done prior to plan execution)
- `distill` skill (deleted; replaced by `ingest`)
- Plugin marketplace publishing or registration
- Version bumps beyond `0.1.0` for new plugins

# Approach

Work proceeds in 4 sequential chunks. Each chunk ends with a commit creating a
rollback boundary. The old structure (`wos/`, `skills/`, `commands/`, `scripts/`)
is removed only in Chunk 4, after all content is confirmed migrated.

**Python ownership:**
- `tools/wiki/wiki/` — document.py, agents_md.py, plan.py, project.py, research.py, skill_chain.py, url_checker.py, wiki.py
- `tools/check/check/` — skill.py, document.py, url_checker.py (document.py and url_checker.py duplicated from wiki; accepted — check must be standalone for build tooling)
- `tools/build/`, `tools/work/`, `tools/consider/` — pure skills, no Python

**Script path convention:** scripts in `tools/<plugin>/scripts/` use
`Path(__file__).parent.parent` (2 levels up) to find plugin root. No marker-based
walk-up, no `CLAUDE_PLUGIN_ROOT` required for path discovery.

**Skill rename map:**

| Old skill | New plugin | New skill name |
|-----------|-----------|----------------|
| `build-skill` | `build` | `build:skill` |
| `build-rule` | `build` | `build:rule` |
| `build-hook` | `build` | `build:hook` |
| `build-subagent` | `build` | `build:subagent` |
| `refine-prompt` | `build` | `build:refine-prompt` |
| `check-skill` | `check` | `check:skill` |
| `check-rule` | `check` | `check:rule` |
| `check-hook` | `check` | `check:hook` |
| `check-subagent` | `check` | `check:subagent` |
| `check-skill-chain` | `check` | `check:skill-chain` |
| `setup` | `wiki` | `wiki:setup` |
| `research` | `wiki` | `wiki:research` |
| `ingest` | `wiki` | `wiki:ingest` |
| `lint` | `wiki` | `wiki:lint` |
| `scope-work` | `work` | `work:scope` |
| `plan-work` | `work` | `work:plan` |
| `start-work` | `work` | `work:start` |
| `check-work` | `work` | `work:verify` |
| `finish-work` | `work` | `work:finish` |
| `audit` | `work` | `work:audit` |
| `retrospective` | `work` | `work:retro` |
| `commands/consider/*` | `consider` | `consider:<name>` |

**`_shared/references/` distribution:**

| Source | Destination |
|--------|-------------|
| `research/*` | `tools/wiki/skills/research/references/` |
| `plan-format.md`, `feedback-loop.md` | `tools/work/_shared/references/` |
| `primitive-routing.md` | `tools/build/_shared/references/` |

Note: if `feedback-loop.md` is referenced by `build` or `check` skills, duplicate it
into `tools/build/_shared/references/` as well. Verify during execution by grepping
each SKILL.md for the reference path.

# File Changes

## Created
- `tools/build/.claude-plugin/plugin.json`
- `tools/check/.claude-plugin/plugin.json`
- `tools/wiki/.claude-plugin/plugin.json`
- `tools/work/.claude-plugin/plugin.json`
- `tools/consider/.claude-plugin/plugin.json`
- `marketplace.json`
- `tools/wiki/pyproject.toml`
- `tools/check/pyproject.toml`
- `tools/wiki/wiki/` (Python package — 8 modules from `wos/`: document.py, agents_md.py, plan.py, project.py, research.py, skill_chain.py, url_checker.py, wiki.py)
- `tools/check/check/` (Python package — `skill.py`, `document.py`, `url_checker.py`; latter two duplicated from wiki)
- `tools/wiki/scripts/` (4 scripts: lint.py, update_preferences.py, check_url.py, _bootstrap.py)
- `tools/build/skills/` (5 skill directories)
- `tools/check/skills/` (5 skill directories)
- `tools/wiki/skills/` (4 skill directories — no distill)
- `tools/work/skills/` (7 skill directories)
- `tools/consider/skills/` (17 skill directories — 16 models + meta)
- `tools/wiki/tests/` (wiki module tests)
- `tools/check/tests/` (check module tests)
- `conftest.py` (root sys.path setup for cross-plugin test discovery)

## Modified
- `pyproject.toml` (dev deps only; update testpaths and ruff paths)
- `.github/workflows/ci.yml` (install both plugin packages; lint `tools/`)
- `CLAUDE.md` (new architecture and marketplace structure)
- `AGENTS.md` (updated navigation)
- `README.md` (install instructions)

## Deleted
- `wos/` (entire Python package)
- `skills/` (entire directory)
- `commands/` (entire directory)
- `scripts/` (entire directory)
- `tests/` (root-level, after migration to plugin test dirs)

# Tasks

## Chunk 1: Scaffold Marketplace Structure

- [x] Create `tools/` with 5 plugin subdirectories (`build`, `check`, `wiki`, `work`,
  `consider`), each containing a `.claude-plugin/` folder. No content yet.
  Verify: `ls tools/` outputs `build check consider wiki work`
  Commit: `chore: create tools/ marketplace directory skeleton` <!-- sha:300e013 -->

- [x] Write `.claude-plugin/plugin.json` for each of the 5 plugins. Fields: `name`
  (matching directory), `version` (`0.1.0`), `description` (one sentence), `author`
  (`{"name": "Brandon Beidel"}`). Use the agreed names: `build`, `check`, `wiki`,
  `work`, `consider`.
  Verify: `python -c "import json; [json.load(open(f'tools/{p}/.claude-plugin/plugin.json')) for p in ['build','check','wiki','work','consider']]; print('ok')"` exits 0
  Commit: `chore: add plugin.json manifests for all 5 plugins` <!-- sha:300e013 -->

- [x] Write `marketplace.json` — spec requires `.claude-plugin/marketplace.json` (not repo
  root). Updated existing `.claude-plugin/marketplace.json` to 5-plugin toolkit structure
  with `source` field (spec uses `source`, not `path`). `recommended` groupings included.
  Verify: `python -c "import json; json.load(open('.claude-plugin/marketplace.json')); print('ok')"` exits 0
  Commit: `chore: update marketplace.json to toolkit 5-plugin structure` <!-- sha:fef851d -->

- [x] Create `tools/wiki/pyproject.toml` (package name `wiki`) and
  `tools/check/pyproject.toml` (package name `check`). Both: Python `>=3.9`,
  no runtime dependencies, setuptools build backend.
  Verify: `pip install -e tools/wiki -e tools/check` exits 0
  Commit: `chore: add per-plugin pyproject.toml for wiki and check` <!-- sha:beab4b6 -->

- [x] Update root `pyproject.toml`: remove the `wos` package declaration and
  `[tool.setuptools.packages.find]` section. Rename `[project] name` from `wos` to
  `toolkit` (the root is now a dev-deps meta-package, not the `wos` library). Keep
  `[project.optional-dependencies].dev` with pytest and ruff. Update
  `[tool.pytest.ini_options].testpaths` to `["tools/wiki/tests", "tools/check/tests"]`.
  Update `[tool.ruff]` paths in CI (not in pyproject, but note for CI task).
  Verify: `pip install -e ".[dev]"` exits 0
  Commit: `chore: update root pyproject.toml to dev-deps only toolkit meta-package` <!-- sha:a6a8989 -->

## Chunk 2: Split Python Packages

- [ ] Create `tools/wiki/wiki/` package. Copy from `wos/` all modules except
  `skill.py`: `document.py`, `agents_md.py`, `plan.py`, `project.py`, `research.py`,
  `skill_chain.py`, `url_checker.py`, `wiki.py`, `__init__.py`. No subdirectories.
  Update all internal imports: `from wos.` → `from wiki.`, `import wos.` → `import wiki.`.
  `__init__.py` uses a self-registration pattern — do NOT copy verbatim. Write it to
  import only the modules that live in `wiki`: `wiki.plan`, `wiki.research`,
  `wiki.skill_chain`, `wiki.wiki`. Do not import `wiki.skill` (that lives in `check`).
  Verify: `cd tools/wiki && python -c "from wiki.document import Document; print('ok')"` exits 0
  Commit: `feat: create wiki Python package from wos modules`

- [ ] Create `tools/check/check/` package with `skill.py`, `document.py`,
  `url_checker.py` (all copied from `wos/`). `document.py` and `url_checker.py` are
  intentional duplicates — check must be standalone for build tooling. Update all
  internal imports: `from wos.` → `from check.`.
  Write `__init__.py` explicitly (do NOT copy from `wos/`):
  ```python
  """check: Claude Code plugin for skill and rule quality checks."""
  import check.skill  # noqa: F401  — registers SkillDocument with Document registry
  ```
  Without this import, `check.document.parse_document()` will not route to SkillDocument.
  Verify: `cd tools/check && python -c "from check.skill import check_skill_sizes; print('ok')"` exits 0
  Commit: `feat: create check Python package`

- [ ] Migrate `scripts/` to `tools/wiki/scripts/`. For each script, update:
  (1) `sys.path` insertion to use `Path(__file__).parent.parent` (plugin root = `tools/wiki/`),
  (2) all `from wos.` imports → `from wiki.`, (3) remove any `CLAUDE_PLUGIN_ROOT`
  walk-up logic. Migrate: `lint.py`, `update_preferences.py`, `check_url.py`, `_bootstrap.py`.
  (`reindex.py`, `get_version.py`, and `deploy.py` are not migrated — deleted with
  legacy directories in Chunk 4. `deploy.py` needs a full rewrite for the new structure;
  deferred to a future task.)
  **`_bootstrap.py` warning:** inspect before migrating — it may manipulate paths based on
  the `wos/` directory name rather than using `from wos.` imports. Update any hardcoded
  `wos` path references alongside the import updates.
  Verify: `python tools/wiki/scripts/lint.py --help` exits 0
  Commit: `feat: migrate scripts to tools/wiki/scripts with updated imports`

## Chunk 3: Migrate Skills and Commands

- [ ] Migrate `build` skills. Move directories:
  `skills/build-skill/ → tools/build/skills/skill/`,
  `skills/build-rule/ → tools/build/skills/rule/`,
  `skills/build-hook/ → tools/build/skills/hook/`,
  `skills/build-subagent/ → tools/build/skills/subagent/`,
  `skills/refine-prompt/ → tools/build/skills/refine-prompt/`.
  Move `skills/build-skill/scripts/` → `tools/build/skills/skill/scripts/`.
  Move `_shared/references/primitive-routing.md` → `tools/build/_shared/references/`.
  In each SKILL.md, update `${CLAUDE_PLUGIN_ROOT}` paths to reflect new plugin root.
  If any SKILL.md references `_shared/references/feedback-loop.md`, copy that file
  to `tools/build/_shared/references/` as well.
  **Inspect all files in `skills/build-skill/scripts/` for `from wos.` or `import wos`
  imports and update them to `from wiki.` / `from check.` as appropriate.** `build` has
  no Python package — these scripts rely on editable installs of `wiki` and `check`
  (`pip install -e tools/wiki -e tools/check`) making those packages importable directly.
  Verify: `ls tools/build/skills/` shows `hook  refine-prompt  rule  skill  subagent`
  Commit: `feat: migrate build skills to tools/build`

- [ ] Migrate `check` skills. Move directories:
  `skills/check-skill/ → tools/check/skills/skill/`,
  `skills/check-rule/ → tools/check/skills/rule/`,
  `skills/check-hook/ → tools/check/skills/hook/`,
  `skills/check-subagent/ → tools/check/skills/subagent/`,
  `skills/check-skill-chain/ → tools/check/skills/skill-chain/`.
  Update `${CLAUDE_PLUGIN_ROOT}` paths in each SKILL.md.
  Verify: `ls tools/check/skills/` shows `hook  rule  skill  skill-chain  subagent`
  Commit: `feat: migrate check skills to tools/check`

- [ ] Migrate `wiki` skills. Move directories:
  `skills/setup/ → tools/wiki/skills/setup/`,
  `skills/research/ → tools/wiki/skills/research/`,
  `skills/ingest/ → tools/wiki/skills/ingest/`,
  `skills/lint/ → tools/wiki/skills/lint/`.
  (`distill` was deleted prior to this plan — replaced by `ingest`. Do not migrate.)
  Move `skills/research/scripts/` → `tools/wiki/skills/research/scripts/`.
  Move `_shared/references/research/*` → `tools/wiki/skills/research/references/`.
  Update all `${CLAUDE_PLUGIN_ROOT}` script paths in SKILL.md files.
  Verify: `ls tools/wiki/skills/` shows `ingest  lint  research  setup`
  Commit: `feat: migrate wiki skills to tools/wiki`

- [ ] Migrate `work` skills. Move directories:
  `skills/scope-work/ → tools/work/skills/scope/`,
  `skills/plan-work/ → tools/work/skills/plan/`,
  `skills/start-work/ → tools/work/skills/start/`,
  `skills/check-work/ → tools/work/skills/verify/`,
  `skills/finish-work/ → tools/work/skills/finish/`,
  `skills/audit/ → tools/work/skills/audit/`,
  `skills/retrospective/ → tools/work/skills/retro/`.
  Move all 3 files from `skills/start-work/scripts/` → `tools/work/skills/start/scripts/`:
  `plan_assess.py`, `check_tasks_complete.sh`, `validate_plan.sh`.
  Move `_shared/references/plan-format.md` and `feedback-loop.md` →
  `tools/work/_shared/references/`.
  Update all `${CLAUDE_PLUGIN_ROOT}` paths in SKILL.md files.
  **Update Python imports in per-skill scripts:** `plan_assess.py` imports from `wos.` —
  update to `from wiki.` (or `from check.` as appropriate). `work` has no Python package;
  these scripts rely on editable installs making `wiki` and `check` importable directly.
  Do NOT add sys.path manipulation — the editable install is the contract.
  Also inspect any other `.py` files under migrated `work` skill directories for `wos.` imports.
  Verify: `ls tools/work/skills/` shows `audit  finish  plan  retro  scope  start  verify`
  Commit: `feat: migrate work skills to tools/work`

- [ ] Convert `commands/consider/` to `consider` plugin. For each of the 16 files in
  `commands/consider/<name>.md`, create `tools/consider/skills/<name>/SKILL.md`
  with the file content as the skill body. Convert `commands/consider.md` to
  `tools/consider/skills/consider/SKILL.md` as the meta entry point. No Python needed.
  Verify: `ls tools/consider/skills/ | wc -l` outputs `17`
  Commit: `feat: convert consider commands to tools/consider plugin`

## Chunk 4: Tests, CI, Docs, Cleanup

- [ ] Migrate tests. Copy wiki-related tests to `tools/wiki/tests/`:
  `test_document.py`, `test_frontmatter.py`, `test_validators.py`, `test_agents_md.py`,
  `test_markers.py`, `test_preferences.py`, `test_wiki.py`, `test_chain.py`,
  `test_suffix.py`, `test_lint.py`, `test_update_preferences.py`, `test_deploy.py`,
  `test_check_url.py`, `test_url_checker.py`, `test_research_assess.py`,
  `test_research_gates.py`, `test_version.py`, `test_script_syspath.py`.
  Copy check-related tests to `tools/check/tests/`: `test_skill_audit.py`,
  `test_plan_assess.py`. Copy `tests/fixtures/` to both plugin test dirs as needed.
  Update all imports `from wos.` → `from wiki.`/`from check.`.
  (`conftest.py` and `fixtures/` already exist in `tests/` — migrate, don't create.)
  (`test_discovery.py`, `test_index.py`, `test_research_protocol.py`, `test_get_version.py`
  do not exist — do not migrate.)
  **`test_script_syspath.py` requires a rewrite, not just import updates.** It tests
  that scripts perform correct sys.path insertion. Script locations are changing
  (`scripts/` → `tools/wiki/scripts/`) and the path convention changes. Rewrite to
  test the new `Path(__file__).parent.parent` convention against the new script locations.
  Verify: `python -m pytest tools/wiki/tests/ tools/check/tests/ -v` passes
  Commit: `test: migrate test suite to per-plugin directories`

- [ ] Update `.github/workflows/ci.yml`. Change install step:
  `pip install -e tools/wiki -e tools/check -e ".[dev]"`. Change ruff step:
  `ruff check tools/`. Change pytest step:
  `python -m pytest tools/wiki/tests/ tools/check/tests/ -v`.
  Verify: `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` parses without error (install pyyaml if needed, or review manually)
  Commit: `ci: update workflow for toolkit marketplace structure`

- [ ] Update `CLAUDE.md`. Replace the Architecture section with the new marketplace
  structure (5 plugins, per-plugin packages). Update Package Structure listing to
  describe `tools/<plugin>/<package>/` pattern. Update Script invocation convention
  to `Path(__file__).parent.parent` (2-level). Update Build & Test commands to
  `pip install -e tools/wiki -e tools/check -e ".[dev]"`. Remove all `wos/` references.
  Verify: `grep -c "wos/" CLAUDE.md` outputs `0`
  Commit: `docs: update CLAUDE.md for toolkit marketplace structure`

- [ ] Update `AGENTS.md` navigation: revise areas table and any `wos/`-specific
  references to reflect `tools/` structure. Update `README.md`: add marketplace
  overview, per-plugin install commands, recommended groupings (knowledge, tooling,
  full suite). Include manual repo rename note.
  Verify: `grep -c "wos/" AGENTS.md README.md` outputs `0`
  Commit: `docs: update AGENTS.md and README for toolkit structure`

- [ ] Remove legacy directories: `wos/`, `skills/`, `commands/`, `scripts/`, `tests/`.
  Before deletion, verify no dangling references:
  `grep -r "from wos\." tools/ .github/ CLAUDE.md` returns no matches.
  `grep -r "skills/" CLAUDE.md AGENTS.md` returns no unexpected matches.
  Then: `rm -rf wos/ skills/ commands/ scripts/ tests/`
  Verify: `ls` at repo root does not show `wos skills commands scripts tests`
  Commit: `chore: remove legacy wos/ skills/ commands/ scripts/ directories`

- [ ] Orphan review. After legacy deletion, sweep the repo for files that need
  a decision. For each file found, decide: rewrite, move, or delete.
  Run the following checks and triage each result:
  - `grep -r "from wos\." tools/` — any remaining wos imports (should be zero; fix if not)
  - `grep -r "skills/" tools/ CLAUDE.md AGENTS.md` — stale path references
  - `find tools/ -name "*.py" -not -path "*/tests/*"` — any Python files outside packages (unexpected scripts)
  - `find tools/ -name "*.md" -not -name "SKILL.md" -not -name "README.md"` — loose markdown not in a known role
  - `find . -maxdepth 2 -name "*.py" -not -path "./tools/*" -not -path "./.venv/*"` — Python at repo root that shouldn't be there
  No commit until each flagged file has been explicitly triaged.
  Commit: `chore: triage and resolve orphaned files post-migration`

# Validation

1. **All 5 plugins load:**
   `claude --plugin-dir tools/build --plugin-dir tools/check --plugin-dir tools/wiki --plugin-dir tools/work --plugin-dir tools/consider`
   Expected: no manifest errors reported

2. **Python packages install:**
   `pip install -e tools/wiki -e tools/check`
   Expected: exit 0

3. **Test suite passes:**
   `python -m pytest tools/wiki/tests/ tools/check/tests/ -v`
   Expected: all green

4. **Lint clean:**
   `ruff check tools/`
   Expected: no errors

5. **No legacy imports:**
   `grep -r "from wos\." tools/`
   Expected: no output

6. **Marketplace JSON valid:**
   `python -c "import json; json.load(open('marketplace.json')); print('ok')"`
   Expected: `ok`

7. **Manual post-merge:** rename GitHub repo `wos` → `toolkit` at
   github.com/bcbeidel/wos → Settings → Repository name
