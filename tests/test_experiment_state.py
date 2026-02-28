"""Tests for wos.experiment_state — data model and JSON serialization."""

from __future__ import annotations

import json
from pathlib import Path

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
