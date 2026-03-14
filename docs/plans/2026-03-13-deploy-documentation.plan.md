---
name: Deploy Documentation Updates
description: Update stale deploy design doc and create user-facing DEPLOYING.md guide
type: plan
status: completed
related:
  - docs/designs/2026-03-13-deploy-documentation.design.md
  - docs/designs/cross-platform-deploy-design.md
---

## Goal

Update the stale deploy design doc to reflect the current symlink-based
implementation and create a user-facing DEPLOYING.md guide.

## Scope

**Must have:**
- Updated `cross-platform-deploy-design.md` reflecting symlinks, `--platform`, platform registry
- `DEPLOYING.md` at repo root with quick start, both modes, all 7 platforms, how-it-works
- README.md cross-reference to DEPLOYING.md

**Won't have:**
- Changes to `deploy.py`
- Platform capability matrix (hooks, rules, etc.)
- Agent-facing context docs

## Approach

Pure documentation. Task 1 rewrites the stale design doc. Task 2 creates
the new user-facing guide from scratch based on `deploy.py`'s actual
behavior. Task 3 adds the README cross-reference. Each task is a commit.

## File Changes

| Action | File | Description |
|--------|------|-------------|
| Modify | `docs/designs/cross-platform-deploy-design.md` | Rewrite to reflect symlink-based deployment |
| Create | `DEPLOYING.md` | User-facing deployment guide |
| Modify | `README.md` | Add cross-platform deployment section |

## Tasks

- [x] **Task 1: Rewrite `cross-platform-deploy-design.md`** <!-- sha:f69f1d2 -->
  - Replace all content after frontmatter to describe the current
    symlink-based deployment:
    - Two modes: `--target` (project-level → `.agents/`) and
      `--platform` (platform-level → `~/.<platform>/`)
    - Platform registry: copilot (`.copilot`), cursor (`.cursor`),
      claude (`.claude`), codex (`.codex`), gemini (`.gemini`),
      windsurf (`.codeium/windsurf`), opencode (`.config/opencode`)
    - Symlinks `scripts/`, `wos/`, and individual skill dirs under `skills/`
    - Backup behavior: timestamped `.backup_` rename before relinking
    - Idempotent: skips already-correct symlinks
    - `--dry-run` flag
  - Remove all references to: file copying, `transform_markdown`,
    `uv run` rewriting, preflight stripping, `check_runtime.py`
  - Update frontmatter: set `status: approved`, add `updated_at: 2026-03-13`
  - Update `related` to include the new design doc
  - Verify: `grep -E "copy|transform|preflight|uv run" docs/designs/cross-platform-deploy-design.md`
    returns no matches
  - Commit

- [x] **Task 2: Create `DEPLOYING.md`** <!-- sha:59d0ecf -->
  - Create `DEPLOYING.md` at repo root with sections:
    - **Quick Start** — `--target` and `--platform` one-liners
    - **Project-Level Deployment** — what `--target` does, resulting
      directory structure, when to use (per-project)
    - **Platform-Level Deployment** — what `--platform` does, resulting
      directory structure, when to use (all projects for that platform)
    - **Supported Platforms** — table with platform key, display name,
      deploy path, and command for all 7 platforms
    - **How It Works** — symlinks not copies, backup behavior,
      idempotency, `--dry-run`
    - **Prerequisites** — Python 3.9+, WOS cloned or installed
  - Keep under 200 lines
  - Verify: `wc -l DEPLOYING.md` is under 200
  - Verify: commands shown in the doc parse correctly:
    `python scripts/deploy.py --help` exits 0
  - Commit

- [x] **Task 3: Update `README.md` with cross-reference** <!-- sha:f76f06d -->
  - Add a "Cross-Platform Deployment" section after "Usage" and before
    "Script Invocation"
  - Content: 2-3 sentences explaining WOS skills can be deployed to
    other platforms, link to DEPLOYING.md, show the deploy command
  - Verify: `grep "DEPLOYING.md" README.md` returns a match
  - Commit

## Validation

1. **Design doc is accurate:**
   ```
   grep -cE "copy|transform|preflight|uv run" docs/designs/cross-platform-deploy-design.md
   ```
   Expected: `0`

2. **DEPLOYING.md exists and is concise:**
   ```
   test -f DEPLOYING.md && wc -l DEPLOYING.md
   ```
   Expected: file exists, under 200 lines

3. **All 7 platforms documented:**
   ```
   grep -c "python scripts/deploy.py --platform" DEPLOYING.md
   ```
   Expected: `7` (one command per platform)

4. **README links to DEPLOYING.md:**
   ```
   grep -c "DEPLOYING.md" README.md
   ```
   Expected: at least `1`

5. **Deploy script still works:**
   ```
   python scripts/deploy.py --help
   ```
   Expected: exits 0, shows usage
