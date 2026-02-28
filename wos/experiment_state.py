"""Experiment state management.

Provides dataclasses for experiment state and functions for
loading, saving, querying phase status, checking artifact gates,
and formatting progress displays.
"""

from __future__ import annotations

import json
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
