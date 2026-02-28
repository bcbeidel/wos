---
name: Experiment Skill Phase 1 Implementation Plan
description: Step-by-step TDD implementation of /wos:experiment skill skeleton with state management, phase tracking, artifact gates, and CLI
type: plan
related:
  - docs/plans/2026-02-25-experiment-framework-design.md
---

# Experiment Skill Phase 1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a `/wos:experiment` skill skeleton that manages `experiment-state.json`, tracks phase progression with artifact-existence gates, and displays progress.

**Architecture:** New `wos/experiment_state.py` module (dataclass + functions), new `scripts/experiment_state.py` CLI (4 subcommands), new `skills/experiment/SKILL.md`. All stdlib-only, matching existing WOS patterns.

**Tech Stack:** Python 3.9+ (stdlib only), pytest, ruff

**Issue:** [#74](https://github.com/bcbeidel/work-os/issues/74)
**Parent Issue:** [#67](https://github.com/bcbeidel/work-os/issues/67)
**Branch:** `feat/74-experiment-skill`
**PR:** TBD

### Progress

- [x] Task 1: ExperimentState dataclass and JSON serialization
- [x] Task 2: Phase progression logic
- [x] Task 3: Artifact gate checking
- [x] Task 4: Progress formatting
- [x] Task 5: CLI script
- [x] Task 6: SKILL.md
- [x] Task 7: Integration verification (208/208 tests pass, CLI e2e verified)

---

### Task 1: ExperimentState Dataclass and JSON Serialization

**Files:**
- Create: `wos/experiment_state.py`
- Create: `tests/test_experiment_state.py`

**Context:** Follow the dataclass pattern from `wos/document.py` — `from __future__ import annotations`, `@dataclass`, `field(default_factory=...)` for mutable defaults. Follow `wos/url_checker.py` for module-level constants. The module will grow through Tasks 1-4, each adding functions.

**Step 1: Create the test file**

Create `tests/test_experiment_state.py` with this exact content:

```python
"""Tests for wos.experiment_state — data model and JSON serialization."""

from __future__ import annotations

import json
from pathlib import Path

from wos.experiment_state import (
    ExperimentState,
    PhaseState,
    load_state,
    save_state,
)


class TestPhaseState:
    def test_defaults(self) -> None:
        ps = PhaseState()
        assert ps.status == "pending"
        assert ps.completed_at is None

    def test_custom_values(self) -> None:
        ps = PhaseState(status="complete", completed_at="2026-02-27T10:00:00Z")
        assert ps.status == "complete"
        assert ps.completed_at == "2026-02-27T10:00:00Z"


class TestExperimentState:
    def test_defaults(self) -> None:
        state = ExperimentState()
        assert state.experiment_id == ""
        assert state.rigor_tier == "exploratory"
        assert state.conditions == []


class TestLoadState:
    def test_round_trip(self, tmp_path: Path) -> None:
        state_file = tmp_path / "experiment-state.json"
        data = {
            "experiment_id": "2026-02-27-test",
            "title": "Test Experiment",
            "rigor_tier": "pilot",
            "created_at": "2026-02-27T10:00:00Z",
            "phases": {
                "design": {"status": "complete", "completed_at": "2026-02-27T10:00:00Z"},
                "audit": {"status": "in_progress", "completed_at": None},
                "evaluation": {"status": "pending", "completed_at": None},
                "execution": {"status": "pending", "completed_at": None},
                "analysis": {"status": "pending", "completed_at": None},
                "publication": {"status": "pending", "completed_at": None},
            },
            "conditions": ["gpt-4", "claude-3"],
            "subject_type": "llm",
            "evaluation_method": "automated",
        }
        state_file.write_text(json.dumps(data))
        state = load_state(str(state_file))
        assert state.experiment_id == "2026-02-27-test"
        assert state.rigor_tier == "pilot"
        assert state.phases["design"].status == "complete"
        assert state.phases["audit"].status == "in_progress"
        assert state.conditions == ["gpt-4", "claude-3"]

    def test_missing_optional_fields_use_defaults(self, tmp_path: Path) -> None:
        state_file = tmp_path / "experiment-state.json"
        data = {
            "experiment_id": "",
            "title": "",
            "rigor_tier": "exploratory",
            "created_at": "",
            "phases": {
                "design": {"status": "pending", "completed_at": None},
                "audit": {"status": "pending", "completed_at": None},
                "evaluation": {"status": "pending", "completed_at": None},
                "execution": {"status": "pending", "completed_at": None},
                "analysis": {"status": "pending", "completed_at": None},
                "publication": {"status": "pending", "completed_at": None},
            },
        }
        state_file.write_text(json.dumps(data))
        state = load_state(str(state_file))
        assert state.conditions == []
        assert state.subject_type == ""


class TestSaveState:
    def test_writes_valid_json(self, tmp_path: Path) -> None:
        state = ExperimentState(
            experiment_id="test-123",
            title="My Test",
            rigor_tier="exploratory",
            created_at="2026-02-27T10:00:00Z",
            phases={
                "design": PhaseState(status="complete", completed_at="2026-02-27T10:00:00Z"),
                "audit": PhaseState(status="in_progress"),
                "evaluation": PhaseState(),
                "execution": PhaseState(),
                "analysis": PhaseState(),
                "publication": PhaseState(),
            },
        )
        out = tmp_path / "state.json"
        save_state(state, str(out))
        data = json.loads(out.read_text())
        assert data["experiment_id"] == "test-123"
        assert data["phases"]["design"]["status"] == "complete"
        assert data["phases"]["evaluation"]["status"] == "pending"

    def test_save_load_round_trip(self, tmp_path: Path) -> None:
        original = ExperimentState(
            experiment_id="rt-test",
            title="Round Trip",
            rigor_tier="confirmatory",
            created_at="2026-02-27T12:00:00Z",
            phases={name: PhaseState() for name in [
                "design", "audit", "evaluation",
                "execution", "analysis", "publication",
            ]},
            conditions=["a", "b"],
            subject_type="code",
            evaluation_method="human",
        )
        out = tmp_path / "state.json"
        save_state(original, str(out))
        loaded = load_state(str(out))
        assert loaded.experiment_id == original.experiment_id
        assert loaded.rigor_tier == original.rigor_tier
        assert loaded.conditions == original.conditions
        assert loaded.subject_type == original.subject_type

    def test_file_ends_with_newline(self, tmp_path: Path) -> None:
        state = ExperimentState(
            phases={name: PhaseState() for name in [
                "design", "audit", "evaluation",
                "execution", "analysis", "publication",
            ]},
        )
        out = tmp_path / "state.json"
        save_state(state, str(out))
        assert out.read_text().endswith("\n")
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_experiment_state.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'wos.experiment_state'`

**Step 3: Write the module**

Create `wos/experiment_state.py` with this exact content:

```python
"""Experiment state management.

Provides dataclasses for experiment state and functions for
loading, saving, querying phase status, checking artifact gates,
and formatting progress displays.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

PHASE_ORDER = (
    "design", "audit", "evaluation",
    "execution", "analysis", "publication",
)

VALID_TIERS = {"pilot", "exploratory", "confirmatory"}


@dataclass
class PhaseState:
    """Status of a single experiment phase."""

    status: str = "pending"
    completed_at: Optional[str] = None


@dataclass
class ExperimentState:
    """Machine-readable experiment state from experiment-state.json."""

    experiment_id: str = ""
    title: str = ""
    rigor_tier: str = "exploratory"
    created_at: str = ""
    phases: Dict[str, PhaseState] = field(default_factory=dict)
    conditions: List[str] = field(default_factory=list)
    subject_type: str = ""
    evaluation_method: str = ""


def load_state(path: str) -> ExperimentState:
    """Load experiment state from a JSON file."""
    with open(path) as f:
        data = json.load(f)

    phases = {}
    for name in PHASE_ORDER:
        phase_data = data.get("phases", {}).get(name, {})
        phases[name] = PhaseState(
            status=phase_data.get("status", "pending"),
            completed_at=phase_data.get("completed_at"),
        )

    return ExperimentState(
        experiment_id=data.get("experiment_id", ""),
        title=data.get("title", ""),
        rigor_tier=data.get("rigor_tier", "exploratory"),
        created_at=data.get("created_at", ""),
        phases=phases,
        conditions=data.get("conditions", []),
        subject_type=data.get("subject_type", ""),
        evaluation_method=data.get("evaluation_method", ""),
    )


def save_state(state: ExperimentState, path: str) -> None:
    """Save experiment state to a JSON file."""
    data = {
        "experiment_id": state.experiment_id,
        "title": state.title,
        "rigor_tier": state.rigor_tier,
        "created_at": state.created_at,
        "phases": {
            name: {
                "status": ps.status,
                "completed_at": ps.completed_at,
            }
            for name, ps in state.phases.items()
        },
        "conditions": state.conditions,
        "subject_type": state.subject_type,
        "evaluation_method": state.evaluation_method,
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
```

**Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_experiment_state.py -v`
Expected: 8 tests PASS

**Step 5: Commit**

```bash
git add wos/experiment_state.py tests/test_experiment_state.py
git commit -m "feat(experiment): add ExperimentState dataclass and JSON serialization (#74)"
```

---

### Task 2: Phase Progression Logic

**Files:**
- Modify: `wos/experiment_state.py` — add `new_state()`, `current_phase()`, `advance_phase()`
- Modify: `tests/test_experiment_state.py` — add test classes

**Context:** Three new functions. `new_state()` creates a fresh state with design phase in_progress. `current_phase()` returns first non-complete phase. `advance_phase()` marks a phase complete and starts the next. All modify/query `ExperimentState` in place.

**Step 1: Add tests**

Append these imports and test classes to `tests/test_experiment_state.py`. Add `pytest` to existing imports, and add `PHASE_ORDER`, `advance_phase`, `current_phase`, `new_state` to the import from `wos.experiment_state`.

```python
import pytest

from wos.experiment_state import (
    PHASE_ORDER,
    ExperimentState,
    PhaseState,
    advance_phase,
    current_phase,
    load_state,
    new_state,
    save_state,
)


class TestCurrentPhase:
    def test_all_pending_returns_first(self) -> None:
        state = ExperimentState(
            phases={name: PhaseState() for name in PHASE_ORDER},
        )
        assert current_phase(state) == "design"

    def test_first_complete_returns_second(self) -> None:
        state = ExperimentState(
            phases={name: PhaseState() for name in PHASE_ORDER},
        )
        state.phases["design"].status = "complete"
        assert current_phase(state) == "audit"

    def test_all_complete_returns_none(self) -> None:
        state = ExperimentState(
            phases={
                name: PhaseState(status="complete")
                for name in PHASE_ORDER
            },
        )
        assert current_phase(state) is None


class TestAdvancePhase:
    def test_marks_phase_complete(self) -> None:
        state = ExperimentState(
            phases={name: PhaseState() for name in PHASE_ORDER},
        )
        state.phases["design"].status = "in_progress"
        advance_phase(state, "design")
        assert state.phases["design"].status == "complete"
        assert state.phases["design"].completed_at is not None

    def test_sets_next_phase_in_progress(self) -> None:
        state = ExperimentState(
            phases={name: PhaseState() for name in PHASE_ORDER},
        )
        state.phases["design"].status = "in_progress"
        advance_phase(state, "design")
        assert state.phases["audit"].status == "in_progress"

    def test_last_phase_no_error(self) -> None:
        state = ExperimentState(
            phases={
                name: PhaseState(status="complete")
                for name in PHASE_ORDER
            },
        )
        state.phases["publication"].status = "in_progress"
        advance_phase(state, "publication")
        assert state.phases["publication"].status == "complete"

    def test_unknown_phase_raises(self) -> None:
        state = ExperimentState(
            phases={name: PhaseState() for name in PHASE_ORDER},
        )
        with pytest.raises(ValueError, match="Unknown phase"):
            advance_phase(state, "nonexistent")

    def test_does_not_overwrite_in_progress_next(self) -> None:
        state = ExperimentState(
            phases={name: PhaseState() for name in PHASE_ORDER},
        )
        state.phases["design"].status = "in_progress"
        state.phases["audit"].status = "in_progress"
        advance_phase(state, "design")
        assert state.phases["audit"].status == "in_progress"


class TestNewState:
    def test_creates_with_design_in_progress(self) -> None:
        state = new_state(tier="exploratory", title="Test")
        assert state.rigor_tier == "exploratory"
        assert state.title == "Test"
        assert state.phases["design"].status == "in_progress"
        assert state.phases["audit"].status == "pending"
        assert state.experiment_id != ""
        assert state.created_at != ""

    def test_invalid_tier_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid tier"):
            new_state(tier="invalid", title="Test")

    def test_all_valid_tiers(self) -> None:
        for tier in ("pilot", "exploratory", "confirmatory"):
            state = new_state(tier=tier, title="T")
            assert state.rigor_tier == tier
```

**Step 2: Run tests to verify new tests fail**

Run: `uv run python -m pytest tests/test_experiment_state.py -v`
Expected: 8 PASS (Task 1), 11 FAIL (`ImportError` for `current_phase`, `advance_phase`, `new_state`)

**Step 3: Add implementation**

Append these three functions to `wos/experiment_state.py` (after `save_state`):

```python
def new_state(tier: str, title: str) -> ExperimentState:
    """Create a fresh experiment state with design phase in_progress."""
    if tier not in VALID_TIERS:
        raise ValueError(
            f"Invalid tier: {tier}. "
            f"Must be one of: {', '.join(sorted(VALID_TIERS))}"
        )
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    slug = title.lower().replace(" ", "-")[:50]
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    phases = {name: PhaseState() for name in PHASE_ORDER}
    phases["design"] = PhaseState(status="in_progress")

    return ExperimentState(
        experiment_id=f"{date_str}-{slug}",
        title=title,
        rigor_tier=tier,
        created_at=now,
        phases=phases,
    )


def current_phase(state: ExperimentState) -> Optional[str]:
    """Return the first non-complete phase, or None if all done."""
    for name in PHASE_ORDER:
        if state.phases.get(name, PhaseState()).status != "complete":
            return name
    return None


def advance_phase(state: ExperimentState, phase: str) -> None:
    """Mark a phase complete and set the next phase to in_progress.

    Modifies state in place.
    """
    if phase not in PHASE_ORDER:
        raise ValueError(f"Unknown phase: {phase}")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    state.phases[phase].status = "complete"
    state.phases[phase].completed_at = now

    idx = PHASE_ORDER.index(phase)
    if idx + 1 < len(PHASE_ORDER):
        next_name = PHASE_ORDER[idx + 1]
        if state.phases[next_name].status == "pending":
            state.phases[next_name].status = "in_progress"
```

**Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_experiment_state.py -v`
Expected: 19 tests PASS

**Step 5: Commit**

```bash
git add wos/experiment_state.py tests/test_experiment_state.py
git commit -m "feat(experiment): add phase progression logic (#74)"
```

---

### Task 3: Artifact Gate Checking

**Files:**
- Modify: `wos/experiment_state.py` — add `ARTIFACT_GATES` constant and `check_gate()`
- Modify: `tests/test_experiment_state.py` — add `TestCheckGate` class

**Context:** Gates are artifact-existence checks. Each phase (except design) requires specific files/directories to exist before entry. `data/raw/` is a directory gate — it must contain files other than `.gitkeep`.

**Step 1: Add tests**

Add `ARTIFACT_GATES` and `check_gate` to the import from `wos.experiment_state`. Append this test class to `tests/test_experiment_state.py`:

```python
from wos.experiment_state import ARTIFACT_GATES, check_gate


class TestCheckGate:
    def test_design_has_no_gates(self, tmp_path: Path) -> None:
        assert check_gate(str(tmp_path), "design") == []

    def test_audit_missing_both(self, tmp_path: Path) -> None:
        missing = check_gate(str(tmp_path), "audit")
        assert "protocol/hypothesis.md" in missing
        assert "protocol/design.md" in missing

    def test_audit_satisfied(self, tmp_path: Path) -> None:
        proto = tmp_path / "protocol"
        proto.mkdir()
        (proto / "hypothesis.md").write_text("# H")
        (proto / "design.md").write_text("# D")
        assert check_gate(str(tmp_path), "audit") == []

    def test_analysis_empty_data_dir_fails(self, tmp_path: Path) -> None:
        raw = tmp_path / "data" / "raw"
        raw.mkdir(parents=True)
        (raw / ".gitkeep").write_text("")
        missing = check_gate(str(tmp_path), "analysis")
        assert "data/raw/" in missing

    def test_analysis_data_dir_with_files_passes(self, tmp_path: Path) -> None:
        raw = tmp_path / "data" / "raw"
        raw.mkdir(parents=True)
        (raw / "results.csv").write_text("condition,outcome\na,1")
        assert check_gate(str(tmp_path), "analysis") == []

    def test_analysis_no_data_dir_fails(self, tmp_path: Path) -> None:
        missing = check_gate(str(tmp_path), "analysis")
        assert "data/raw/" in missing

    def test_unknown_phase_returns_empty(self, tmp_path: Path) -> None:
        assert check_gate(str(tmp_path), "nonexistent") == []
```

**Step 2: Run tests to verify new tests fail**

Run: `uv run python -m pytest tests/test_experiment_state.py::TestCheckGate -v`
Expected: FAIL — `ImportError` for `ARTIFACT_GATES`, `check_gate`

**Step 3: Add implementation**

Add `ARTIFACT_GATES` constant after `VALID_TIERS` and `check_gate()` function after `advance_phase()` in `wos/experiment_state.py`:

```python
ARTIFACT_GATES: Dict[str, List[str]] = {
    "audit": ["protocol/hypothesis.md", "protocol/design.md"],
    "evaluation": ["protocol/audit.md"],
    "execution": ["evaluation/criteria.md"],
    "analysis": ["data/raw/"],
    "publication": ["results/analysis.md"],
}


def check_gate(root: str, phase: str) -> List[str]:
    """Check artifact gates for entering a phase.

    Returns list of missing artifact paths (empty if all satisfied).
    Paths ending with '/' are directories that must contain files
    other than .gitkeep.
    """
    gates = ARTIFACT_GATES.get(phase, [])
    missing = []
    for gate in gates:
        path = os.path.join(root, gate)
        if gate.endswith("/"):
            if not os.path.isdir(path):
                missing.append(gate)
            else:
                files = [f for f in os.listdir(path) if f != ".gitkeep"]
                if not files:
                    missing.append(gate)
        else:
            if not os.path.isfile(path):
                missing.append(gate)
    return missing
```

**Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_experiment_state.py -v`
Expected: 26 tests PASS

**Step 5: Commit**

```bash
git add wos/experiment_state.py tests/test_experiment_state.py
git commit -m "feat(experiment): add artifact gate checking (#74)"
```

---

### Task 4: Progress Formatting

**Files:**
- Modify: `wos/experiment_state.py` — add `format_progress()`
- Modify: `tests/test_experiment_state.py` — add `TestFormatProgress` class

**Context:** Human-readable progress display showing title, tier, progress bar, and phase list with status indicators. Used by both CLI and skill.

**Step 1: Add tests**

Add `format_progress` to the import. Append this test class to `tests/test_experiment_state.py`:

```python
from wos.experiment_state import format_progress


class TestFormatProgress:
    def test_fresh_state(self) -> None:
        state = ExperimentState(
            title="My Test",
            rigor_tier="exploratory",
            phases={name: PhaseState() for name in PHASE_ORDER},
        )
        state.phases["design"].status = "in_progress"
        output = format_progress(state)
        assert "My Test" in output
        assert "Exploratory" in output
        assert "Phase 1 of 6" in output
        assert "[Design]" in output

    def test_midway_state(self) -> None:
        state = ExperimentState(
            title="Midway",
            rigor_tier="pilot",
            phases={name: PhaseState() for name in PHASE_ORDER},
        )
        state.phases["design"].status = "complete"
        state.phases["audit"].status = "complete"
        state.phases["evaluation"].status = "in_progress"
        output = format_progress(state)
        assert "Phase 3 of 6" in output
        assert "\u2713" in output  # checkmark

    def test_all_complete(self) -> None:
        state = ExperimentState(
            title="Done",
            rigor_tier="confirmatory",
            phases={
                name: PhaseState(status="complete")
                for name in PHASE_ORDER
            },
        )
        output = format_progress(state)
        assert "Phase 6 of 6" in output
        assert "Complete" in output

    def test_progress_bar_characters(self) -> None:
        state = ExperimentState(
            title="Bar Test",
            rigor_tier="exploratory",
            phases={name: PhaseState() for name in PHASE_ORDER},
        )
        state.phases["design"].status = "complete"
        state.phases["audit"].status = "in_progress"
        output = format_progress(state)
        assert "\u2588" in output  # filled block
        assert "\u2591" in output  # empty block
```

**Step 2: Run tests to verify new tests fail**

Run: `uv run python -m pytest tests/test_experiment_state.py::TestFormatProgress -v`
Expected: FAIL — `ImportError` for `format_progress`

**Step 3: Add implementation**

Append to `wos/experiment_state.py`:

```python
def format_progress(state: ExperimentState) -> str:
    """Format a human-readable progress display."""
    cur = current_phase(state)
    completed = sum(
        1 for name in PHASE_ORDER
        if state.phases.get(name, PhaseState()).status == "complete"
    )
    total = len(PHASE_ORDER)

    filled = "\u2588" * completed
    empty = "\u2591" * (total - completed)

    parts = []
    for name in PHASE_ORDER:
        status = state.phases.get(name, PhaseState()).status
        label = name.title()
        if status == "complete":
            parts.append(f"{label} (\u2713)")
        elif status == "in_progress":
            parts.append(f"[{label}]")
        else:
            parts.append(label)

    tier = state.rigor_tier.title() if state.rigor_tier else "Unknown"
    title = state.title or "Untitled"

    if cur:
        phase_num = PHASE_ORDER.index(cur) + 1
        phase_label = cur.title()
    else:
        phase_num = total
        phase_label = "Complete"

    return (
        f"Experiment: {title} ({tier})\n"
        f"Progress: {filled}{empty} Phase {phase_num} of {total}"
        f" \u2014 {phase_label}\n"
        f"Completed: {' \u2192 '.join(parts)}"
    )
```

**Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_experiment_state.py -v`
Expected: 30 tests PASS

**Step 5: Commit**

```bash
git add wos/experiment_state.py tests/test_experiment_state.py
git commit -m "feat(experiment): add progress formatting (#74)"
```

---

### Task 5: CLI Script

**Files:**
- Create: `scripts/experiment_state.py`
- Create: `tests/test_experiment_state_script.py`

**Context:** Follow the exact pattern from `scripts/audit.py` — PEP 723 header, `sys.path` injection, deferred imports, argparse with subcommands. Test pattern follows `tests/test_audit.py` — `_run_cli()` helper that patches `sys.argv` and captures stdout/stderr/exitcode.

**Step 1: Create the test file**

Create `tests/test_experiment_state_script.py` with this exact content:

```python
"""Tests for scripts/experiment_state.py CLI."""

from __future__ import annotations

import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch


def _run_cli(*args: str) -> tuple[str, str, int]:
    """Run experiment_state.main() with given CLI args."""
    captured_stdout = StringIO()
    captured_stderr = StringIO()
    exit_code = 0

    with patch.object(sys, "argv", ["experiment_state.py", *args]):
        with patch("sys.stdout", captured_stdout), \
             patch("sys.stderr", captured_stderr):
            try:
                from scripts.experiment_state import main

                main()
            except SystemExit as exc:
                exit_code = exc.code if exc.code is not None else 0

    return captured_stdout.getvalue(), captured_stderr.getvalue(), exit_code


class TestInit:
    def test_creates_state_file(self, tmp_path: Path) -> None:
        stdout, _, code = _run_cli(
            "--root", str(tmp_path), "init",
            "--tier", "exploratory", "--title", "Test Experiment",
        )
        assert code == 0
        state_file = tmp_path / "experiment-state.json"
        assert state_file.exists()
        data = json.loads(state_file.read_text())
        assert data["rigor_tier"] == "exploratory"
        assert data["title"] == "Test Experiment"
        assert data["phases"]["design"]["status"] == "in_progress"

    def test_output_shows_progress(self, tmp_path: Path) -> None:
        stdout, _, _ = _run_cli(
            "--root", str(tmp_path), "init",
            "--tier", "pilot", "--title", "Quick Test",
        )
        assert "Quick Test" in stdout
        assert "Pilot" in stdout


class TestStatus:
    def test_shows_progress(self, tmp_path: Path) -> None:
        _run_cli(
            "--root", str(tmp_path), "init",
            "--tier", "exploratory", "--title", "Status Test",
        )
        stdout, _, code = _run_cli("--root", str(tmp_path), "status")
        assert code == 0
        assert "Status Test" in stdout
        assert "Exploratory" in stdout

    def test_missing_state_file_exits_1(self, tmp_path: Path) -> None:
        _, stderr, code = _run_cli("--root", str(tmp_path), "status")
        assert code == 1
        assert "No experiment-state.json" in stderr


class TestAdvance:
    def test_advances_phase(self, tmp_path: Path) -> None:
        _run_cli(
            "--root", str(tmp_path), "init",
            "--tier", "exploratory", "--title", "Advance Test",
        )
        stdout, _, code = _run_cli(
            "--root", str(tmp_path), "advance", "--phase", "design",
        )
        assert code == 0
        data = json.loads((tmp_path / "experiment-state.json").read_text())
        assert data["phases"]["design"]["status"] == "complete"
        assert data["phases"]["audit"]["status"] == "in_progress"


class TestCheckGates:
    def test_missing_artifacts_exits_1(self, tmp_path: Path) -> None:
        _run_cli(
            "--root", str(tmp_path), "init",
            "--tier", "exploratory", "--title", "Gate Test",
        )
        _run_cli("--root", str(tmp_path), "advance", "--phase", "design")
        stdout, _, code = _run_cli(
            "--root", str(tmp_path), "check-gates",
        )
        assert code == 1
        assert "Missing" in stdout

    def test_satisfied_gates_exits_0(self, tmp_path: Path) -> None:
        _run_cli(
            "--root", str(tmp_path), "init",
            "--tier", "exploratory", "--title", "Gate Test",
        )
        proto = tmp_path / "protocol"
        proto.mkdir()
        (proto / "hypothesis.md").write_text("# H")
        (proto / "design.md").write_text("# D")
        _run_cli("--root", str(tmp_path), "advance", "--phase", "design")
        stdout, _, code = _run_cli(
            "--root", str(tmp_path), "check-gates",
        )
        assert code == 0
        assert "satisfied" in stdout
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_experiment_state_script.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.experiment_state'`

**Step 3: Create the CLI script**

Create `scripts/experiment_state.py` with this exact content:

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Experiment state management CLI.

Usage:
    uv run scripts/experiment_state.py --root . status
    uv run scripts/experiment_state.py --root . init --tier exploratory --title "My Experiment"
    uv run scripts/experiment_state.py --root . advance --phase design
    uv run scripts/experiment_state.py --root . check-gates [--phase audit]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure `import wos` works whether pip-installed or run from plugin cache.
_plugin_root = Path(__file__).resolve().parent.parent
if str(_plugin_root) not in sys.path:
    sys.path.insert(0, str(_plugin_root))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Experiment state management.",
    )
    parser.add_argument("--root", default=".", help="Experiment repo root")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show experiment progress")

    init_p = sub.add_parser("init", help="Initialize experiment state")
    init_p.add_argument(
        "--tier",
        required=True,
        choices=["pilot", "exploratory", "confirmatory"],
    )
    init_p.add_argument("--title", required=True)

    adv_p = sub.add_parser("advance", help="Mark a phase complete")
    adv_p.add_argument(
        "--phase",
        required=True,
        choices=[
            "design", "audit", "evaluation",
            "execution", "analysis", "publication",
        ],
    )

    gates_p = sub.add_parser("check-gates", help="Check artifact gates")
    gates_p.add_argument("--phase", help="Phase to check (default: current)")

    args = parser.parse_args()

    # Deferred imports — keeps --help fast
    from wos.experiment_state import (
        advance_phase,
        check_gate,
        current_phase,
        format_progress,
        load_state,
        new_state,
        save_state,
    )

    root = Path(args.root).resolve()
    state_path = root / "experiment-state.json"

    if args.command == "status":
        if not state_path.is_file():
            print(
                "No experiment-state.json found. Not an experiment repo.",
                file=sys.stderr,
            )
            sys.exit(1)
        state = load_state(str(state_path))
        print(format_progress(state))

    elif args.command == "init":
        state = new_state(tier=args.tier, title=args.title)
        save_state(state, str(state_path))
        print(format_progress(state))

    elif args.command == "advance":
        if not state_path.is_file():
            print("No experiment-state.json found.", file=sys.stderr)
            sys.exit(1)
        state = load_state(str(state_path))
        advance_phase(state, args.phase)
        save_state(state, str(state_path))
        print(format_progress(state))

    elif args.command == "check-gates":
        if not state_path.is_file():
            print("No experiment-state.json found.", file=sys.stderr)
            sys.exit(1)
        state = load_state(str(state_path))
        phase = args.phase or current_phase(state)
        if not phase:
            print("All phases complete.")
            return
        missing = check_gate(str(root), phase)
        if missing:
            print(f"Missing for {phase}: {', '.join(missing)}")
            sys.exit(1)
        else:
            print(f"Gates satisfied for {phase}.")


if __name__ == "__main__":
    main()
```

**Step 4: Make the script executable**

```bash
chmod +x scripts/experiment_state.py
```

**Step 5: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_experiment_state_script.py -v`
Expected: 6 tests PASS

**Step 6: Commit**

```bash
git add scripts/experiment_state.py tests/test_experiment_state_script.py
git commit -m "feat(experiment): add CLI script with init/status/advance/check-gates (#74)"
```

---

### Task 6: SKILL.md

**Files:**
- Create: `skills/experiment/SKILL.md`

**Context:** Follow the pattern from `skills/audit/SKILL.md` and `skills/research/SKILL.md`. SKILL.md has YAML frontmatter, references the shared preflight check, and provides Claude-facing instructions for orchestrating experiments. No `references/` subdirectory needed for Phase 1 — the skill is self-contained.

**Step 1: Create the skill directory**

```bash
mkdir -p skills/experiment
```

**Step 2: Write SKILL.md**

Create `skills/experiment/SKILL.md` with this exact content:

```markdown
---
name: experiment
description: >
  This skill should be used when the user wants to "run an experiment",
  "test a hypothesis", "compare approaches", "validate a claim",
  "set up an experiment", "check experiment status", "experiment progress",
  or any request to conduct a structured empirical investigation using
  the experiment template.
argument-hint: "[action: status, init, or phase name]"
user-invocable: true
compatibility: "Requires Python 3 (stdlib only), experiment-template repo"
---

# Experiment Skill

Orchestrate structured experiments using repos created from the
[experiment-template](https://github.com/bcbeidel/experiment-template).
Guides users through 6 phases with tier-appropriate depth
(Pilot / Exploratory / Confirmatory).

## Routing

| Situation | Action |
|-----------|--------|
| No `experiment-state.json` | Tell user to create repo from template |
| Has state, user says "status" | Show progress |
| Has state, all phases pending | Initialize (tier selection) |
| Has state, phases in progress | Route to current phase |

**Prerequisite:** Before running any `uv run` command below, follow the
preflight check in the [preflight reference](../_shared/references/preflight.md).

## Detection

Check for `experiment-state.json` in the current directory:

    uv run <plugin-scripts-dir>/experiment_state.py --root . status

If missing: "This doesn't appear to be an experiment repo. Create one from
the template: https://github.com/bcbeidel/experiment-template"

## Initialize

Ask: **"What's the intent of this experiment?"**

| Choice | Tier |
|--------|------|
| Quick test or feasibility check | `pilot` |
| Learn something real, might share results | `exploratory` |
| Testing a specific hypothesis for decisions | `confirmatory` |

Then ask for a short title and run:

    uv run <plugin-scripts-dir>/experiment_state.py --root . init --tier <tier> --title "<title>"

**Escalation prompt:** If the user picks Pilot but mentions sharing results
or making decisions, suggest Exploratory tier.

## Progress Display

Show at each interaction:

    uv run <plugin-scripts-dir>/experiment_state.py --root . status

## Phase Routing

| Phase | Key Files | Guidance |
|-------|-----------|----------|
| design | `protocol/hypothesis.md`, `protocol/design.md` | Fill in research question, variables, conditions, sample size |
| audit | `protocol/audit.md` | Complete the tier-appropriate checklist |
| evaluation | `evaluation/criteria.md`, `evaluation/blinding-manifest.json` | Define metrics, rubrics, blinding setup |
| execution | `data/raw/`, `protocol/prompts/` | Collect data, save raw results |
| analysis | `results/analysis.md` | Run `python scripts/analyze.py`, interpret results |
| publication | `CONCLUSION.md`, `README.md` | Write verdict, update README |

### Gate Checking

Before advancing:

    uv run <plugin-scripts-dir>/experiment_state.py --root . check-gates

If satisfied:

    uv run <plugin-scripts-dir>/experiment_state.py --root . advance --phase <phase>

## Key Rules

- **Don't skip phases.** All tiers use all 6 phases. Depth varies, not count.
- **Check gates before advancing.** Artifact-existence gates prevent premature progression.
- **Show progress every interaction.** Users need to see where they are.
- **Respect tier choice.** Don't impose Confirmatory ceremony on Pilot experiments.
```

**Step 3: Verify frontmatter parses**

Run: `uv run python -c "from wos.frontmatter import parse_frontmatter; text = open('skills/experiment/SKILL.md').read(); fm, _ = parse_frontmatter(text); print(fm['name'])"`
Expected output: `experiment`

**Step 4: Commit**

```bash
git add skills/experiment/SKILL.md
git commit -m "feat(experiment): add SKILL.md for /wos:experiment (#74)"
```

---

### Task 7: Integration Verification

**Files:** None (read-only verification)

**Context:** Run the full test suite, linter, and end-to-end CLI to confirm everything works together. This task catches any cross-task integration issues.

**Step 1: Run full test suite**

Run: `uv run python -m pytest tests/ -v`
Expected: All tests pass (171 existing + ~36 new = ~207 total), 0 failures

**Step 2: Run linter**

Run: `uv run --extra dev ruff check wos/ tests/ scripts/`
Expected: Clean (no errors). If ruff isn't available locally, note this — CI will catch it.

**Step 3: End-to-end CLI verification in a temp directory**

```bash
TMPDIR=$(mktemp -d)
uv run scripts/experiment_state.py --root "$TMPDIR" init --tier exploratory --title "Integration Test"
uv run scripts/experiment_state.py --root "$TMPDIR" status
uv run scripts/experiment_state.py --root "$TMPDIR" check-gates
uv run scripts/experiment_state.py --root "$TMPDIR" advance --phase design
uv run scripts/experiment_state.py --root "$TMPDIR" status
rm -rf "$TMPDIR"
```

Expected:
- `init`: Shows progress with "Integration Test (Exploratory)", Phase 1 of 6
- `status`: Same output
- `check-gates`: Exit 1, "Missing for audit: protocol/hypothesis.md, protocol/design.md"
- `advance`: Shows Phase 2 of 6, design marked complete
- `status`: Confirms Phase 2

**Step 4: Verify skill frontmatter parses**

Run: `uv run python -c "from wos.frontmatter import parse_frontmatter; text = open('skills/experiment/SKILL.md').read(); fm, _ = parse_frontmatter(text); print(fm['name'], fm.get('user-invocable'))"`
Expected: `experiment True`

**Step 5: Final commit (plan doc update)**

Update this plan doc — mark all tasks complete. Commit:

```bash
git add docs/plans/2026-02-27-experiment-skill-phase1-plan.md
git commit -m "docs: mark experiment skill phase 1 plan complete (#74)"
```

**Step 6: Create PR**

```bash
gh pr create --title "feat: add /wos:experiment skill skeleton (#74)" --body "$(cat <<'EOF'
## Summary

Phase 1 of the experiment framework (#67). Adds:

- `wos/experiment_state.py` — ExperimentState dataclass, JSON I/O, phase progression, artifact gates, progress formatting
- `scripts/experiment_state.py` — CLI with init/status/advance/check-gates subcommands
- `skills/experiment/SKILL.md` — Claude-facing skill definition
- ~36 new tests (all passing)

## Test plan

- [ ] `uv run python -m pytest tests/ -v` — all tests pass
- [ ] `ruff check wos/ tests/ scripts/` — clean
- [ ] CLI end-to-end: init → status → check-gates → advance → status
- [ ] SKILL.md frontmatter parses correctly

Closes #74

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```
