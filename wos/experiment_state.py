"""Experiment state management.

Provides dataclasses for experiment state and functions for
loading, saving, querying phase status, checking artifact gates,
and formatting progress displays.
"""

from __future__ import annotations

import json
import os
import random as _random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

PHASE_ORDER = (
    "design", "audit", "evaluation",
    "execution", "analysis", "publication",
)

OPAQUE_IDS = (
    "ALPHA", "BRAVO", "CHARLIE", "DELTA",
    "ECHO", "FOXTROT", "GOLF", "HOTEL",
)

VALID_TIERS = {"pilot", "exploratory", "confirmatory"}

ARTIFACT_GATES: Dict[str, List[str]] = {
    "audit": ["protocol/hypothesis.md", "protocol/design.md"],
    "evaluation": ["protocol/audit.md"],
    "execution": ["evaluation/criteria.md"],
    "analysis": ["data/raw/"],
    "publication": ["results/analysis.md"],
}


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

    arrow = " \u2192 "
    return (
        f"Experiment: {title} ({tier})\n"
        f"Progress: {filled}{empty} Phase {phase_num} of {total}"
        f" \u2014 {phase_label}\n"
        f"Completed: {arrow.join(parts)}"
    )


def generate_manifest(
    conditions: Dict[str, str],
    seed: Optional[int] = None,
) -> dict:
    """Generate a blinding manifest mapping conditions to opaque IDs.

    Args:
        conditions: Mapping of condition_label -> description.
        seed: Randomization seed. If None, a random seed is generated.

    Returns:
        Manifest dict matching the experiment-template schema.
    """
    if len(conditions) < 2:
        raise ValueError("At least 2 conditions required for blinding.")
    if len(conditions) > len(OPAQUE_IDS):
        raise ValueError(
            "Maximum %d conditions supported. Got %d."
            % (len(OPAQUE_IDS), len(conditions))
        )

    if seed is None:
        seed = _random.randint(0, 2**31 - 1)

    rng = _random.Random(seed)
    ids = list(OPAQUE_IDS[:len(conditions)])
    rng.shuffle(ids)

    manifest_conditions = {}
    for (label, description), opaque_id in zip(
        sorted(conditions.items()), ids
    ):
        manifest_conditions[label] = {
            "opaque_id": opaque_id,
            "description": description,
        }

    return {
        "blinding_enabled": True,
        "randomization_seed": seed,
        "conditions": manifest_conditions,
        "assignments": [],
    }
