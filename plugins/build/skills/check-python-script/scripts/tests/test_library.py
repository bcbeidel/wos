"""Tests for check_library_discipline."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import check_library_discipline  # noqa: E402

main = check_library_discipline.main


CLEAN_LIBRARY = '''"""A clean library module."""

from __future__ import annotations

__all__ = ["greet"]


def greet(name: str) -> str:
    """Return a greeting."""
    return f"hello, {name}"


class Greeter:
    """A greeter class."""

    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
'''

LIBRARY_WITH_SIDE_EFFECT = '''"""Library with a top-level side effect."""

from __future__ import annotations

__all__ = ["greet"]

print("hello at import time")


def greet(name: str) -> str:
    return f"hello, {name}"
'''

LIBRARY_MISSING_DUNDER_ALL = '''"""Library without __all__."""


def greet(name: str) -> str:
    """Return a greeting."""
    return f"hello, {name}"
'''

LIBRARY_TYPE_CHECKING_OK = '''"""Library that uses TYPE_CHECKING — should be fine."""

from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = ["greet"]

if TYPE_CHECKING:
    from collections.abc import Iterable


def greet(name: str) -> str:
    return f"hello, {name}"
'''


def _run(tmp_path: Path, content: str) -> tuple[int, str]:
    """Write content to a fixture and run the detector; return (rc, stdout)."""
    import io

    fixture = tmp_path / "fixture.py"
    fixture.write_text(content)

    captured = io.StringIO()
    real_stdout = sys.stdout
    sys.stdout = captured
    try:
        rc = main([str(fixture)])
    finally:
        sys.stdout = real_stdout
    return rc, captured.getvalue()


def test_clean_library_passes(tmp_path: Path):
    rc, out = _run(tmp_path, CLEAN_LIBRARY)
    assert rc == 0
    assert '"library-no-side-effects"' in out
    assert '"overall_status": "pass"' in out
    # Public API declared, so no warn either:
    assert out.count('"overall_status": "pass"') == 2


def test_side_effect_fails(tmp_path: Path):
    rc, out = _run(tmp_path, LIBRARY_WITH_SIDE_EFFECT)
    assert rc == 1
    assert '"rule_id": "library-no-side-effects"' in out
    assert '"status": "fail"' in out
    assert "print" in out


def test_missing_dunder_all_warns(tmp_path: Path):
    rc, out = _run(tmp_path, LIBRARY_MISSING_DUNDER_ALL)
    # No fail, only warn — exit 0
    assert rc == 0
    assert '"rule_id": "library-public-api-declared"' in out
    assert '"status": "warn"' in out


def test_type_checking_block_allowed(tmp_path: Path):
    rc, out = _run(tmp_path, LIBRARY_TYPE_CHECKING_OK)
    assert rc == 0
    # Both rules pass
    assert out.count('"overall_status": "pass"') == 2
