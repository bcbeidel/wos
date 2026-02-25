---
name: Research Skill Bug Fixes Design
description: Design for addressing GitHub issues #56, #59, #60 — unreachable /wos:create, broken Python utility paths, and context window exhaustion with no checkpoints
type: plan
related:
  - skills/research/SKILL.md
  - skills/research/references/research-workflow.md
  - skills/research/references/python-utilities.md
  - skills/research/references/source-verification.md
  - scripts/audit.py
  - scripts/reindex.py
  - artifacts/plans/2026-02-25-research-skill-fixes-design.md
---

# Research Skill Bug Fixes Design

**Issues:** #56, #59, #60
**Branch:** `fix/research-skill-bugs-56-59-60`
**PR:** TBD

## Context

Three bugs in the research skill cause failures during real research sessions:

1. **#56 — `/wos:create` unreachable.** Phase 6 tells the agent to invoke
   `/wos:create`, but that skill has `user-invocable: false` and
   `disable-model-invocation: true`. The agent falls back to the Write tool
   with no validation or reindexing.

2. **#59 — Python utility paths broken.** Skill docs reference scripts with
   bare relative paths (`python3 scripts/validate.py`) that only work when CWD
   is the plugin root. In installed mode, scripts are in the plugin cache at
   `~/.claude/plugins/cache/...`. 5 of 13 utility invocations failed in a
   real session.

3. **#60 — No checkpoints for context resets.** The 6-phase workflow keeps all
   intermediate state in context memory until Phase 6. A context reset before
   Phase 6 loses all work. Observed during a deep-dive with 8 topics and 33
   sources.

These are interconnected: fixing #56 and #59 gives the workflow reliable
document creation and validation commands; fixing #60 means intermediate
work survives context resets.

## Design Decisions

1. **Replace `/wos:create` with direct instructions (#56)** — The research
   workflow includes its own document creation steps (Write file, reindex,
   validate). No cross-skill dependency. The creation recipe is ~3 lines of
   instruction, not meaningful duplication.

2. **Use `${CLAUDE_PLUGIN_ROOT}` for all Python utility paths (#59)** — This
   is the standard Claude Code plugin pattern, matching how VS Code extensions
   use `extensionPath` and Terraform providers use host-provided paths. The
   host tells the plugin where it lives. Scripts also get a `sys.path`
   self-insertion preamble so `import wos` works whether pip-installed or
   running from the cache.

3. **Progressive document building (#60)** — Instead of a separate scratch
   file system, the research document itself is the checkpoint. Created in
   Phase 2 (marked `<!-- DRAFT -->`), updated at each phase boundary, finalized
   in Phase 6. Sequential phases with a single atomic write at each boundary.
   No concurrent file access.

## Changes

### 1. Script Self-Sufficiency (#59)

**Files:** `scripts/audit.py`, `scripts/reindex.py`

Add a `sys.path` preamble to each script so `from wos.xxx import ...` works
regardless of how the script was invoked:

```python
import sys
from pathlib import Path

_plugin_root = Path(__file__).resolve().parent.parent
if str(_plugin_root) not in sys.path:
    sys.path.insert(0, str(_plugin_root))
```

`Path(__file__).parent.parent` resolves `scripts/audit.py` → `scripts/` →
plugin root, which contains both `scripts/` and `wos/`. Works in dev mode
(`python3 scripts/audit.py`) and installed mode
(`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/audit.py"`).

### 2. Skill Reference Updates (#59 + #56)

**Files:** `skills/research/references/python-utilities.md`,
`skills/research/references/source-verification.md`,
`skills/research/references/research-workflow.md`,
`skills/research/SKILL.md`

**python-utilities.md** — Replace all bare relative paths with
`${CLAUDE_PLUGIN_ROOT}`-prefixed versions:

```bash
# Validate a single file
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/audit.py" --root . --no-urls

# Reindex
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/reindex.py" --root .

# Format search protocol
echo '<json>' | PYTHONPATH="${CLAUDE_PLUGIN_ROOT}" python3 -m wos.research_protocol format
```

**source-verification.md** — Replace inline Python snippet with a bash
command using `PYTHONPATH="${CLAUDE_PLUGIN_ROOT}"`:

```bash
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}" python3 -c "
from wos.url_checker import check_urls
import json
results = check_urls(['URL1', 'URL2'])
for r in results:
    print(json.dumps({'url': r.url, 'reachable': r.reachable, 'status': r.status, 'reason': r.reason}))
"
```

**SKILL.md** — Remove two `/wos:create` references (lines 62, 83-84).
Replace with: "Write the document directly and run reindex + validate."

**research-workflow.md Phase 6** — Replace `/wos:create` invocation with
direct instructions:
1. Write the file to `artifacts/research/{date}-{slug}.md`
2. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/reindex.py" --root .`
3. Validate: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/audit.py" --root . --no-urls`

### 3. Progressive Document Building (#60)

**Files:** `skills/research/references/research-workflow.md`

Restructure the workflow so the research document is created early and built
progressively. Each phase writes its output to disk at the phase boundary
as a single atomic write.

| Phase | Current | New |
|-------|---------|-----|
| 1: Frame | In context only | No change (small) |
| 2: Gather | Sources in context | **Create document** with frontmatter + sources section, marked `<!-- DRAFT -->` |
| 3: Verify | SIFT results in context | **Update document** — remove failed URLs, add tier annotations |
| 4: Challenge | ACH/assumptions in context | **Update document** — append Challenge section |
| 5: Synthesize | Narrative in context | **Update document** — add synthesis, confidence levels, counter-evidence |
| 6: Produce | Write from scratch | **Finalize** — restructure for lost-in-the-middle, remove DRAFT marker, reindex, validate |

**Write pattern:** Each phase is a read-modify-write cycle performed by a
single agent. No concurrent writes. Subagents (parallel web searches) return
results to context; only the main agent writes to the file.

**Resumption heuristic** (new section in research-workflow.md):

> If a document already exists at the expected path with `<!-- DRAFT -->` at
> the top, read it to determine which phases are complete:
> - Has sources in frontmatter but no tier annotations → resume at Phase 3
> - Has tier annotations but no Challenge section → resume at Phase 4
> - Has Challenge section but no synthesis → resume at Phase 5
> - Has synthesis but still marked DRAFT → resume at Phase 6

## Testing

- Existing `pytest` tests must still pass after `sys.path` preamble changes
- Add test verifying scripts work when invoked from a different working
  directory (simulating plugin cache execution)
- Manual verification: run the research workflow end-to-end and confirm
  progressive document building works

## Non-Goals

- SIFT intensity operational definitions (#57 — deferred)
- Research enrichment guidance (#58 — deferred)
- Changes to the `wos/` Python package beyond `sys.path` preamble in scripts
- Changes to the create skill's invocability settings
- New CLI entry points in `pyproject.toml` (not needed with `${CLAUDE_PLUGIN_ROOT}`)
- Scratch file / checkpoint file system (progressive document building is sufficient)
