"""Tests for detect_python_profile."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import detect_python_profile  # noqa: E402

detect = detect_python_profile.detect
main = detect_python_profile.main


LIBRARY_FIXTURE = '''"""A library module — imported, not invoked."""

from __future__ import annotations

__all__ = ["greet"]


def greet(name: str) -> str:
    """Return a greeting."""
    return f"hello, {name}"
'''

CLI_FIXTURE = '''#!/usr/bin/env python3
"""A CLI script.

Example:
    ./greet.py --name world
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    args = parser.parse_args(argv)
    print(f"hello, {args.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

SKILL_HELPER_FIXTURE = '''#!/usr/bin/env python3
"""A skill-helper script — JSON over stdio."""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args(argv)
    payload = json.loads(sys.stdin.read())
    print(json.dumps({"received": payload}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

# Has shebang + main_def but no argparse/stdin/json — falls through to cli
AMBIGUOUS_FIXTURE = '''#!/usr/bin/env python3
"""An ambiguous script."""


def main():
    print("hi")


if __name__ == "__main__":
    main()
'''


def test_detect_library():
    assert detect(LIBRARY_FIXTURE) == "library"


def test_detect_cli():
    assert detect(CLI_FIXTURE) == "cli"


def test_detect_skill_helper():
    assert detect(SKILL_HELPER_FIXTURE) == "skill-helper"


def test_detect_ambiguous_defaults_to_cli():
    assert detect(AMBIGUOUS_FIXTURE) == "cli"


def test_empty_text_is_library():
    # No shebang, no main, no main_def
    assert detect("") == "library"


def test_main_with_path_argument(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    script = tmp_path / "fixture.py"
    script.write_text(LIBRARY_FIXTURE)
    rc = main([str(script)])
    assert rc == 0
    assert capsys.readouterr().out.strip() == "library"


def test_main_profile_override_wins(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    # Library content but --profile=cli wins
    script = tmp_path / "fixture.py"
    script.write_text(LIBRARY_FIXTURE)
    rc = main(["--profile=cli", str(script)])
    assert rc == 0
    assert capsys.readouterr().out.strip() == "cli"


def test_main_invalid_profile_value(capsys: pytest.CaptureFixture[str]):
    rc = main(["--profile=notaprofile", "/dev/null"])
    assert rc == 2  # argparse usage-error contract


def test_main_unreadable_path_returns_1(capsys: pytest.CaptureFixture[str]):
    rc = main(["/nonexistent/path/that/does/not/exist.py"])
    assert rc == 1
    assert "cannot read" in capsys.readouterr().err
