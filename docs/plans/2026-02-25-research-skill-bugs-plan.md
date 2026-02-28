# Research Skill Bug Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix three research skill bugs (#56, #59, #60) — unreachable `/wos:create`, broken Python utility paths, and context window exhaustion with no checkpoints.

**Architecture:** Scripts get `sys.path` self-insertion so they work from any CWD. All skill docs switch to `${CLAUDE_PLUGIN_ROOT}` for paths. Research workflow restructured for progressive document building with a `<!-- DRAFT -->` marker and resumption heuristic.

**Tech Stack:** Python 3.9, pytest, Claude Code plugin framework (`${CLAUDE_PLUGIN_ROOT}`)

**Design doc:** `docs/plans/2026-02-25-research-skill-bugs-design.md`

**Branch:** `fix/research-skill-bugs-56-59-60`

---

## Task 1: Create Branch

**Step 1: Create and switch to feature branch**

Run: `git checkout -b fix/research-skill-bugs-56-59-60`

**Step 2: Verify branch**

Run: `git branch --show-current`
Expected: `fix/research-skill-bugs-56-59-60`

---

## Task 2: Script sys.path Self-Insertion — Tests (#59)

**Files:**
- Create: `tests/test_script_syspath.py`

Write tests that verify scripts work when invoked from a different working
directory. This simulates the plugin cache scenario where CWD is the user's
project, not the plugin root.

**Step 1: Write the failing tests**

```python
"""Tests for sys.path self-insertion in scripts (#59).

Scripts must work when invoked from any working directory, not just the
plugin root. This simulates the installed-plugin scenario where CWD is
the user's project.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


class TestAuditSysPath:
    def test_audit_runs_from_different_cwd(self, tmp_path: Path) -> None:
        """audit.py should work when CWD is not the plugin root."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "audit.py"), "--root", str(tmp_path), "--no-urls"],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )
        # No ModuleNotFoundError — script should either pass (no content dirs)
        # or fail gracefully (no context/artifacts dir)
        assert "ModuleNotFoundError" not in result.stderr
        assert "No module named" not in result.stderr

    def test_audit_help_from_different_cwd(self, tmp_path: Path) -> None:
        """audit.py --help should work from any directory."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "audit.py"), "--help"],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )
        assert result.returncode == 0
        assert "validation checks" in result.stdout.lower()


class TestReindexSysPath:
    def test_reindex_runs_from_different_cwd(self, tmp_path: Path) -> None:
        """reindex.py should work when CWD is not the plugin root."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "reindex.py"), "--root", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )
        assert "ModuleNotFoundError" not in result.stderr
        assert "No module named" not in result.stderr

    def test_reindex_help_from_different_cwd(self, tmp_path: Path) -> None:
        """reindex.py --help should work from any directory."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "reindex.py"), "--help"],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )
        assert result.returncode == 0
        assert "reindex" in result.stdout.lower() or "_index.md" in result.stdout


class TestValidateSysPath:
    def test_validate_runs_from_different_cwd(self, tmp_path: Path) -> None:
        """validate.py should work when CWD is not the plugin root."""
        doc = tmp_path / "test.md"
        doc.write_text("---\nname: Test\ndescription: A test\n---\nBody\n")
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "validate.py"), str(doc), "--root", str(tmp_path), "--no-urls"],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )
        assert "ModuleNotFoundError" not in result.stderr
        assert "No module named" not in result.stderr
        assert result.returncode == 0
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_script_syspath.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'wos'` in subprocess stderr,
causing assertions like `assert "ModuleNotFoundError" not in result.stderr` to fail.

**Step 3: Commit failing tests**

```bash
git add tests/test_script_syspath.py
git commit -m "test: add failing tests for script sys.path from different CWD (#59)"
```

---

## Task 3: Script sys.path Self-Insertion — Implementation (#59)

**Files:**
- Modify: `scripts/audit.py` (add preamble after docstring, before existing imports)
- Modify: `scripts/reindex.py` (add preamble after docstring, before existing imports)
- Modify: `scripts/validate.py` (add preamble after docstring, before existing imports)

**Step 1: Add sys.path preamble to `scripts/audit.py`**

Insert after line 7 (`from __future__ import annotations`), before line 9 (`import argparse`):

```python
# Ensure `import wos` works whether pip-installed or run from plugin cache.
_plugin_root = Path(__file__).resolve().parent.parent
if str(_plugin_root) not in sys.path:
    sys.path.insert(0, str(_plugin_root))
```

Note: `sys` and `Path` are already imported in this file. Move the `from pathlib
import Path` import above the preamble if it comes after. The final import order
should be:

```python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure `import wos` works whether pip-installed or run from plugin cache.
_plugin_root = Path(__file__).resolve().parent.parent
if str(_plugin_root) not in sys.path:
    sys.path.insert(0, str(_plugin_root))
```

**Step 2: Add sys.path preamble to `scripts/reindex.py`**

Same pattern. The final import section should be:

```python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure `import wos` works whether pip-installed or run from plugin cache.
_plugin_root = Path(__file__).resolve().parent.parent
if str(_plugin_root) not in sys.path:
    sys.path.insert(0, str(_plugin_root))
```

**Step 3: Add sys.path preamble to `scripts/validate.py`**

Same pattern. The final import section should be:

```python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure `import wos` works whether pip-installed or run from plugin cache.
_plugin_root = Path(__file__).resolve().parent.parent
if str(_plugin_root) not in sys.path:
    sys.path.insert(0, str(_plugin_root))
```

**Step 4: Run the new sys.path tests**

Run: `python3 -m pytest tests/test_script_syspath.py -v`
Expected: All 7 tests PASS

**Step 5: Run the full test suite (verification checkpoint)**

Run: `python3 -m pytest tests/ -v`
Expected: All existing tests still PASS. No regressions.

**Step 6: Commit**

```bash
git add scripts/audit.py scripts/reindex.py scripts/validate.py
git commit -m "fix: add sys.path self-insertion to scripts for plugin cache compatibility (#59)"
```

---

## Task 4: Update python-utilities.md (#59)

**Files:**
- Modify: `skills/research/references/python-utilities.md`

Replace all bare relative paths with `${CLAUDE_PLUGIN_ROOT}`-prefixed versions.

**Step 1: Rewrite python-utilities.md**

Replace the full content with:

```markdown
# Python Utilities Reference

CLI commands available during research sessions. All commands use
`${CLAUDE_PLUGIN_ROOT}` to resolve script paths — this variable is set
automatically by Claude Code when the plugin is active.

## Validate a Single Document

Runs all 4 checks: frontmatter, research sources, source URLs, related paths.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/validate.py" <file> [--root DIR] [--no-urls]
```

Example:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/validate.py" docs/research/2026-02-25-my-research.md --no-urls
```

Output on success:
```
All checks passed.
```

Output on failure:
```
[FAIL] docs/research/my-research.md: Research document has no sources
```

## Validate Entire Project

Runs all 5 checks across `context/` and `artifacts/`.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/audit.py" [--root DIR] [--no-urls] [--json] [--fix]
```

## Regenerate Index Files

Regenerate all `_index.md` files under `context/` and `artifacts/`.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/reindex.py" [--root DIR]
```

## Format Search Protocol

Renders a search protocol JSON as a markdown table.

```bash
echo '<json>' | PYTHONPATH="${CLAUDE_PLUGIN_ROOT}" python3 -m wos.research_protocol format
echo '<json>' | PYTHONPATH="${CLAUDE_PLUGIN_ROOT}" python3 -m wos.research_protocol format --summary
```

### Search Protocol JSON Schema

```json
{
  "entries": [
    {
      "query": "search terms used",
      "source": "google",
      "date_range": "2024-2026 or null",
      "results_found": 12,
      "results_used": 3
    }
  ],
  "not_searched": [
    "Google Scholar - covered by direct source fetching",
    "PubMed - topic is not biomedical"
  ]
}
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `entries[].query` | string | Search terms used |
| `entries[].source` | string | Search engine (e.g., `google`, `scholar`, `github`, `docs`) |
| `entries[].date_range` | string or null | Date filter applied (e.g., `"2024-2026"`) |
| `entries[].results_found` | int | Total results returned |
| `entries[].results_used` | int | Results kept for evaluation |
| `not_searched` | list of strings | Sources not searched, with reason (e.g., `"Reddit - not relevant to topic"`) |

### Example Output (table)

```
| Query | Source | Date Range | Found | Used |
|-------|--------|------------|-------|------|
| python asyncio patterns | google | 2024-2026 | 12 | 3 |
| asyncio best practices | google | — | 8 | 2 |

**Not searched:** Google Scholar - covered by direct source fetching
```

### Example Output (summary)

```
2 searches across 1 source, 20 results found, 5 used
```

## Document Model

The `Document` dataclass fields relevant to research:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | Yes | Concise title |
| `description` | string | Yes | One-sentence summary |
| `type` | string | No | Set to `research` for research docs |
| `sources` | list of strings | For research | URLs of verified sources |
| `related` | list of strings | No | Relative paths to related documents |
```

**Step 2: Commit**

```bash
git add skills/research/references/python-utilities.md
git commit -m "fix: use CLAUDE_PLUGIN_ROOT for all Python utility paths (#59)"
```

---

## Task 5: Update source-verification.md (#59)

**Files:**
- Modify: `skills/research/references/source-verification.md`

Replace the inline Python import snippet with a bash command using
`PYTHONPATH="${CLAUDE_PLUGIN_ROOT}"`.

**Step 1: Rewrite source-verification.md**

Replace the full content with:

```markdown
# Source Verification Reference

Mechanical URL verification to catch dead links and hallucinated sources.
Run this after gathering sources and before SIFT evaluation.

## When to Run

After Phase 2 (Initial Source Gathering) completes, before Phase 3 (Source
Evaluation). Every source collected during gathering must pass verification
before entering the SIFT pipeline.

## How to Run

Use the `wos.url_checker` module to verify source URLs are reachable:

```bash
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}" python3 -c "
from wos.url_checker import check_urls
import json
results = check_urls([
    'https://example.com/page',
    'https://other.com/article',
])
for r in results:
    print(json.dumps({'url': r.url, 'reachable': r.reachable, 'status': r.status, 'reason': r.reason}))
"
```

Each result has:
- `reachable` — `True` if the URL returned 2xx/3xx, `False` otherwise
- `status` — HTTP status code (0 for connection/DNS failures)
- `reason` — human-readable explanation when `reachable=False`

## What to Do with Results

**Unreachable sources (status 404, 0, DNS failure):** Drop them from your
source list. Do not include them in the research document. Note in your
investigation that N sources were removed during verification.

**Unreachable sources (status 403, 5xx):** The source exists but is
temporarily unavailable or paywalled. Keep the source but note the access
issue.

**All sources unreachable:** If verification removes every source, stop and
inform the user. Do not proceed with empty sources — gather new ones instead.
```

**Step 2: Commit**

```bash
git add skills/research/references/source-verification.md
git commit -m "fix: use CLAUDE_PLUGIN_ROOT in source verification reference (#59)"
```

---

## Task 6: Update SKILL.md — Remove /wos:create References (#56)

**Files:**
- Modify: `skills/research/SKILL.md`

**Step 1: Replace `/wos:create` references**

On line 62, replace:

```
Use `/wos:create` to produce the final document.
```

with:

```
Write the document directly, then run reindex and validate
(see `references/python-utilities.md`).
```

On lines 83-84, replace:

```
- **Output is a research document.** Use `/wos:create` to produce the final
  artifact with `type: research`.
```

with:

```
- **Output is a research document.** Write the final artifact directly with
  `type: research` frontmatter, then run reindex and validate.
```

**Step 2: Verify no remaining `/wos:create` references in the file**

Run: `grep -n "wos:create" skills/research/SKILL.md`
Expected: No matches

**Step 3: Commit**

```bash
git add skills/research/SKILL.md
git commit -m "fix: remove unreachable /wos:create references from research skill (#56)"
```

---

## Task 7: Verification Checkpoint — All Tests Pass

**Step 1: Run the full test suite**

Run: `python3 -m pytest tests/ -v`
Expected: All tests PASS. No regressions from tasks 2-6.

**Step 2: Verify no remaining bare script paths in skill references**

Run: `grep -rn "python3 scripts/" skills/`
Expected: No matches (all should use `${CLAUDE_PLUGIN_ROOT}` now)

**Step 3: Verify no remaining `/wos:create` in research skill**

Run: `grep -rn "wos:create" skills/research/`
Expected: No matches

---

## Task 8: Rewrite research-workflow.md — Progressive Document Building (#60 + #56 + #59)

**Files:**
- Modify: `skills/research/references/research-workflow.md`

This is the largest change. The workflow is restructured so the research
document is created in Phase 2 and updated at each phase boundary.

**Step 1: Rewrite research-workflow.md**

Replace the full content of `skills/research/references/research-workflow.md`
with the following. Key changes from current:
- Phase 2 now ends with "Write initial document to disk"
- Phases 3-5 now end with "Update the document on disk"
- Phase 6 replaces `/wos:create` with direct finalization steps
- New "Resuming After Context Reset" section added
- All Python utility paths use `${CLAUDE_PLUGIN_ROOT}`
- Quality checklist uses `${CLAUDE_PLUGIN_ROOT}` paths

```markdown
# Research Workflow

Six-phase investigation process. All research modes follow these phases,
with SIFT intensity and Challenge sub-steps varying by mode (see
research-modes.md).

The research document is created in Phase 2 and built progressively —
each phase writes its output to disk so work survives context resets.

## Resuming After Context Reset

If a document already exists at `docs/research/{date}-{slug}.md` with
`<!-- DRAFT -->` near the top, a previous session started this investigation.
Read the document to determine which phases are complete:

- Has `sources:` in frontmatter but no tier annotations in body → resume at Phase 3
- Has tier annotations but no `## Challenge` section → resume at Phase 4
- Has `## Challenge` section but no `## Findings` section → resume at Phase 5
- Has `## Findings` section but still has `<!-- DRAFT -->` → resume at Phase 6

When resuming, read the document fully to recover context before continuing.

## Phase 1: Frame the Question

1. Restate the user's question in a precise, answerable form
2. Identify the research mode from question framing (see SKILL.md)
3. Break the question into 2-4 sub-questions
4. Confirm scope with the user: "I'll investigate [question] by looking at
   [sub-questions]. Sound right?"
5. Note any constraints (time period, domain, technology stack)
6. **Declare search protocol:** State which sources you plan to search
   (e.g., Google, Google Scholar, GitHub, specific documentation sites)
   and what terms you'll use. Initialize the search protocol JSON:

```json
{"entries": [], "not_searched": []}
```

> **Source diversity:** `WebSearch` routes through a single search engine. To
> improve source diversity: (1) vary query terms to surface different source
> types, (2) fetch known database URLs directly (e.g., PubMed, Semantic
> Scholar) when relevant, (3) log `"google"` as the source honestly — this is
> expected. The `not_searched` field should list sources you chose not to
> search, not sources the tool can't access.

## Phase 2: Gather Sources

1. Conduct breadth-first web searches across the sub-questions
2. Aim for 10-20 candidate sources (more for deep-dive, fewer for historical)
3. For each candidate, record: URL, title, publication date, author/org
4. Flag all sources as **unverified** at this stage
5. Prioritize diversity — different organizations, perspectives, source types
6. **Log each search** — after every web search, append to the protocol:

```json
{
  "query": "the search terms used",
  "source": "google|scholar|github|docs|...",
  "date_range": "2024-2026 or null",
  "results_found": 12,
  "results_used": 3
}
```

7. After gathering is complete, record sources you considered but did
   not search in `not_searched` as strings with a brief reason:

```json
"not_searched": [
  "Google Scholar - covered by direct source fetching",
  "PubMed - topic is not biomedical"
]
```

> **Handling fetch failures:** When parallel `WebFetch` calls fail, a single
> failure can cascade to sibling calls ("Sibling tool call errored"). Retry
> failed URLs individually. Common failure modes:
> - **403** — bot protection; source exists but can't be fetched. Retain if
>   from a published venue.
> - **303/301** — redirect; retry with the redirect URL.
> - **Timeout** — retry once, then skip. Do not drop sources solely because
>   fetching failed — assess based on URL verification status.

8. **Write the initial document to disk.** Create the file at
   `docs/research/{date}-{slug}.md` with a `<!-- DRAFT -->` marker,
   frontmatter containing all gathered source URLs, and a sources table:

```yaml
---
name: "Concise summary of the investigation"
description: "One-sentence summary (update in Phase 5)"
type: research
sources:
  - https://gathered-source-1.example.com
  - https://gathered-source-2.example.com
related: []
---
<!-- DRAFT — investigation in progress -->

# [Title]

## Sources

| # | URL | Title | Author/Org | Date | Status |
|---|-----|-------|-----------|------|--------|
| 1 | ... | ...   | ...       | ...  | unverified |
```

This checkpoint means the source list survives a context reset.

## Phase 3: Verify & Evaluate

Mechanical URL verification followed by SIFT evaluation in a single phase.

### URL Verification

1. Collect all source URLs from the document's frontmatter
2. Use `wos.url_checker.check_urls()` to verify reachability
   (see `references/source-verification.md`)
3. Review the results:
   - Remove sources where `reachable=False` with status 404 or 0
   - Keep sources where `reachable=False` with status 403/5xx but note issues
4. If all sources removed, gather new sources before proceeding
5. Report verification results to the user before continuing

### SIFT Evaluation

Apply SIFT framework (see `references/sift-framework.md`) at the mode's
intensity level.

For each source:

1. **Stop** — Is this source known to me? Flag as unverified if not.
2. **Investigate** — Check domain authority, author credentials, bias.
   Classify into source hierarchy tier (T1-T6, see `references/source-evaluation.md`).
3. **Find better** — For key claims, search for the same information from a
   higher-tier source. Upgrade when found.
4. **Trace** — For critical claims, follow the citation chain to the primary
   source. Verify the claim matches the original context.

After evaluation:
- Drop sources below T5 unless no better source exists
- Never cite T6 (AI-generated) as a source
- Annotate remaining sources with their tier

5. **Update the document on disk.** Remove failed URLs from the `sources:`
   frontmatter list. Update the sources table with verification status and
   tier annotations:

```
| # | URL | Title | Author/Org | Date | Tier | Status |
|---|-----|-------|-----------|------|------|--------|
| 1 | ... | ...   | ...       | ...  | T2   | verified |
| 2 | ... | ...   | ...       | ...  | T4   | verified (403) |
```

## Phase 4: Challenge

Stress-test reasoning before synthesis. See `references/challenge-phase.md`
for full procedures.

Three sub-steps, applied based on research mode (see research-modes.md):

1. **Assumptions check** (all modes) — List 3-5 key assumptions, check
   evidence for/against each, assess impact if false
2. **ACH** (deep-dive, options, competitive, feasibility) — Generate
   competing hypotheses, build evidence matrix, select hypothesis with
   fewest inconsistencies
3. **Premortem** (all modes) — Imagine main conclusion is wrong, generate
   3 failure reasons, assess plausibility

4. **Update the document on disk.** Append a `## Challenge` section with
   the assumptions check, ACH matrix (if applicable), and premortem results.

## Phase 5: Synthesize

1. Organize findings by sub-question
2. For each sub-question, note:
   - Points of agreement across sources (strong evidence)
   - Points of disagreement (contested or uncertain)
   - Gaps where evidence is missing
3. **Annotate each finding with a confidence level:**

| Level | Criteria |
|-------|----------|
| HIGH | Multiple independent T1-T3 sources converge; methodology sound |
| MODERATE | Credible sources support; primary evidence not directly verified |
| LOW | Single source; unverified; some counter-evidence exists |

4. If mode requires counter-evidence: dedicate a section to arguments,
   evidence, or perspectives that challenge the main findings
5. Connect findings to the user's context and decisions
6. Identify actionable insights
7. Note limitations — what couldn't be determined and why
8. Suggest follow-up questions if the investigation revealed new unknowns

9. **Update the document on disk.** Add a `## Findings` section organized
   by sub-question with confidence levels, counter-evidence (if applicable),
   and a connections/implications section. Update the `description:` in
   frontmatter to reflect actual findings.

## Phase 6: Finalize Research Document

The document already exists on disk with content from Phases 2-5. This phase
restructures it for the final reader and runs validation.

1. **Restructure for lost-in-the-middle convention:**
   - **Top:** Summary with key findings (each annotated with confidence level)
     and search protocol summary line
   - **Middle:** Detailed analysis by sub-question, evidence, Challenge phase
     output (assumptions, ACH if applicable, premortem), counter-evidence
   - **Bottom:** Key takeaways, limitations, follow-up questions, and full
     search protocol table

2. **Insert the search protocol.** Format the accumulated search protocol
   JSON using:

```bash
echo '<protocol_json>' | PYTHONPATH="${CLAUDE_PLUGIN_ROOT}" python3 -m wos.research_protocol format
```

   Insert the rendered table into the **Search Protocol** section at the
   bottom of the document. Add the summary line (using `--summary` flag)
   near the top.

3. **Remove the `<!-- DRAFT -->` marker** from the document.

4. **Regenerate index files:**

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/reindex.py" --root .
```

5. **Validate the document:**

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/validate.py" <file> --root . --no-urls
```

## Quality Checklist

Before removing the `<!-- DRAFT -->` marker, verify:
- [ ] All sources passed URL verification
- [ ] All sources have been SIFT-evaluated at the mode's intensity
- [ ] Sources are annotated with hierarchy tiers
- [ ] Challenge phase completed (assumptions + premortem at minimum)
- [ ] ACH included if mode requires it
- [ ] Every finding annotated with confidence level (HIGH/MODERATE/LOW)
- [ ] Counter-evidence section present (if mode requires it)
- [ ] No T6 (AI-generated) sources cited
- [ ] Search protocol section present with all searches logged
- [ ] Implications connected to the user's context
- [ ] Document passes validation:
  `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/validate.py" <file> --root . --no-urls`
```

**Step 2: Commit**

```bash
git add skills/research/references/research-workflow.md
git commit -m "fix: progressive document building and CLAUDE_PLUGIN_ROOT paths in workflow (#56, #59, #60)"
```

---

## Task 9: Verification Checkpoint — Full Validation

**Step 1: Run full test suite**

Run: `python3 -m pytest tests/ -v`
Expected: All tests PASS.

**Step 2: Verify no bare `python3 scripts/` paths remain in skills**

Run: `grep -rn "python3 scripts/" skills/`
Expected: No matches.

**Step 3: Verify no `/wos:create` references in research skill**

Run: `grep -rn "wos:create" skills/research/`
Expected: No matches.

**Step 4: Verify `${CLAUDE_PLUGIN_ROOT}` is used in all utility references**

Run: `grep -rn "CLAUDE_PLUGIN_ROOT" skills/research/references/`
Expected: Matches in `python-utilities.md`, `source-verification.md`, and
`research-workflow.md`.

**Step 5: Verify `<!-- DRAFT -->` marker documented in workflow**

Run: `grep -n "DRAFT" skills/research/references/research-workflow.md`
Expected: Matches in the Resuming section and Phase 2/Phase 6 instructions.

---

## Task 10: Update CHANGELOG.md

**Files:**
- Modify: `CHANGELOG.md`

**Step 1: Add v0.3.4 entry**

Insert after the `## [Unreleased]` line (line 8) and before the
`## [0.3.3]` line (line 10):

```markdown

## [0.3.4] - 2026-02-25

### Fixed

- Research workflow no longer references unreachable `/wos:create` skill —
  replaced with direct document creation instructions.
  ([#56](https://github.com/bcbeidel/wos/issues/56))
- Python utility paths in skill references now use `${CLAUDE_PLUGIN_ROOT}`
  instead of bare relative paths that failed in installed plugin mode.
  Scripts also include `sys.path` self-insertion for plugin cache
  compatibility.
  ([#59](https://github.com/bcbeidel/wos/issues/59))
- Research workflow restructured for progressive document building — the
  document is created in Phase 2 and updated at each phase boundary, so
  intermediate work survives context window resets. Includes a resumption
  heuristic for detecting which phases are complete.
  ([#60](https://github.com/bcbeidel/wos/issues/60))

```

**Step 2: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: update changelog for v0.3.4"
```

---

## Task 11: Version Bump

**Files:**
- Modify: `pyproject.toml` (line 7: `version = "0.3.3"` → `"0.3.4"`)
- Modify: `.claude-plugin/plugin.json` (line 3: `"version": "0.3.3"` → `"0.3.4"`)
- Modify: `.claude-plugin/marketplace.json` (line 15: `"version": "0.3.3"` → `"0.3.4"`)

**Step 1: Bump version in all three files**

In `pyproject.toml`, change line 7:
```
version = "0.3.4"
```

In `.claude-plugin/plugin.json`, change line 3:
```json
"version": "0.3.4",
```

In `.claude-plugin/marketplace.json`, change line 15:
```json
"version": "0.3.4",
```

**Step 2: Verify all three match**

Run: `grep -n "0.3.4" pyproject.toml .claude-plugin/plugin.json .claude-plugin/marketplace.json`
Expected: Exactly 3 matches, one per file.

Run: `grep -n "0.3.3" pyproject.toml .claude-plugin/plugin.json .claude-plugin/marketplace.json`
Expected: No matches (old version fully replaced).

**Step 3: Run version test**

Run: `python3 -m pytest tests/test_version.py -v`
Expected: PASS (version test should pick up the new version).

**Step 4: Commit**

```bash
git add pyproject.toml .claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "chore: bump version to 0.3.4"
```

---

## Task 12: Final Verification Checkpoint

**Step 1: Run full test suite**

Run: `python3 -m pytest tests/ -v`
Expected: All tests PASS.

**Step 2: Verify version consistency**

Run: `grep -rn "0.3.4" pyproject.toml .claude-plugin/plugin.json .claude-plugin/marketplace.json CHANGELOG.md`
Expected: 4 matches (one per version file + changelog header).

**Step 3: Review git log for clean commit history**

Run: `git log --oneline main..HEAD`
Expected: ~8 clean commits, each addressing a specific piece:
1. Failing tests for sys.path
2. sys.path implementation
3. python-utilities.md update
4. source-verification.md update
5. SKILL.md /wos:create removal
6. research-workflow.md rewrite
7. Changelog
8. Version bump

---

## Task 13: Push Branch and Create Pull Request

**Step 1: Push branch**

Run: `git push -u origin fix/research-skill-bugs-56-59-60`

**Step 2: Create pull request**

```bash
gh pr create --title "fix: research skill bugs (#56, #59, #60)" --body "$(cat <<'EOF'
## Summary

- **#56** — Replaced unreachable `/wos:create` references with direct document creation instructions in the research workflow
- **#59** — All Python utility paths in skill references now use `${CLAUDE_PLUGIN_ROOT}`. Scripts include `sys.path` self-insertion for plugin cache compatibility.
- **#60** — Research workflow restructured for progressive document building. Document created in Phase 2, updated at each phase boundary. Includes resumption heuristic for context window resets.

## Files Changed

| File | Change |
|------|--------|
| `scripts/audit.py` | `sys.path` preamble |
| `scripts/reindex.py` | `sys.path` preamble |
| `scripts/validate.py` | `sys.path` preamble |
| `skills/research/SKILL.md` | Remove `/wos:create` references |
| `skills/research/references/research-workflow.md` | Progressive doc building + `${CLAUDE_PLUGIN_ROOT}` paths |
| `skills/research/references/python-utilities.md` | `${CLAUDE_PLUGIN_ROOT}` paths |
| `skills/research/references/source-verification.md` | `${CLAUDE_PLUGIN_ROOT}` invocation pattern |
| `tests/test_script_syspath.py` | 7 new tests for cross-CWD script execution |
| `CHANGELOG.md` | v0.3.4 entry |
| `pyproject.toml` | Version bump |
| `.claude-plugin/plugin.json` | Version bump |
| `.claude-plugin/marketplace.json` | Version bump |

## Test plan

- [x] New sys.path tests pass (scripts work from different CWD)
- [x] All existing tests pass (no regressions)
- [x] No bare `python3 scripts/` paths in skill references
- [x] No `/wos:create` references in research skill
- [x] `${CLAUDE_PLUGIN_ROOT}` used in all utility references
- [x] Version consistent across all 3 files
- [ ] Manual: run `/wos:research` end-to-end and confirm progressive document building works

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

**Step 3: Record PR URL in design doc**

Update `docs/plans/2026-02-25-research-skill-bugs-design.md` —
replace `**PR:** TBD` with the actual PR URL.

---

## Task 14: Tag Bugfix Release (After PR Merge)

**Wait for PR to be reviewed and merged before proceeding.**

**Step 1: Switch to main and pull**

```bash
git checkout main
git pull origin main
```

**Step 2: Verify version on main**

Run: `grep "version" pyproject.toml | head -1`
Expected: `version = "0.3.4"`

**Step 3: Create annotated tag**

```bash
git tag -a v0.3.4 -m "v0.3.4 — research skill bug fixes (#56, #59, #60)"
```

**Step 4: Push tag**

```bash
git push origin v0.3.4
```

**Step 5: Create GitHub release**

```bash
gh release create v0.3.4 --title "v0.3.4" --notes "$(cat <<'EOF'
## Fixed

- Research workflow no longer references unreachable `/wos:create` skill — replaced with direct document creation instructions. ([#56](https://github.com/bcbeidel/wos/issues/56))
- Python utility paths in skill references now use `${CLAUDE_PLUGIN_ROOT}` instead of bare relative paths that failed in installed plugin mode. ([#59](https://github.com/bcbeidel/wos/issues/59))
- Research workflow restructured for progressive document building — the document is created in Phase 2 and updated at each phase boundary, so intermediate work survives context window resets. ([#60](https://github.com/bcbeidel/wos/issues/60))
EOF
)"
```

**Step 6: Verify release**

Run: `gh release view v0.3.4`
Expected: Release visible with correct notes.
