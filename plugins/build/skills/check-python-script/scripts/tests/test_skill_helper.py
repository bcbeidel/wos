"""Tests for check_skill_helper_contract."""

from __future__ import annotations

import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import check_skill_helper_contract  # noqa: E402

main = check_skill_helper_contract.main


CLEAN_SKILL_HELPER = '''#!/usr/bin/env python3
"""A clean skill-helper script."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_USER_ERROR = 2
EXIT_INTERNAL_ERROR = 3


def emit_error(code, message):
    print(json.dumps({"error": code, "message": message}), file=sys.stderr)


def atomic_write(path, content):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content)
    os.replace(tmp, path)


def main(argv=None):
    parser = argparse.ArgumentParser()
    args = parser.parse_args(argv)
    payload = json.loads(sys.stdin.read())
    print(json.dumps({"received": payload}))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
'''

# Reads payload from a file flag instead of stdin — fails the contract.
HELPER_NO_STDIN_JSON = '''#!/usr/bin/env python3
"""A non-conforming script that takes payload via a flag."""

from __future__ import annotations

import argparse
import json
import sys

EXIT_OK = 0
EXIT_USER_ERROR = 2
EXIT_INTERNAL_ERROR = 3


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload-file", required=True)
    args = parser.parse_args(argv)
    with open(args.payload_file) as f:
        payload = json.load(f)
    print(json.dumps(payload))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
'''

# Has stdin-json but no atomic write and only 0/1 exit codes.
HELPER_NON_ATOMIC_AND_FLAT_CODES = '''#!/usr/bin/env python3
"""Script with stdin-json but missing atomic write and distinct codes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    payload = json.loads(sys.stdin.read())
    args.out.write_text(json.dumps(payload))  # not atomic
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


def _run(tmp_path: Path, content: str) -> tuple[int, str]:
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


def test_clean_skill_helper_passes(tmp_path: Path):
    rc, out = _run(tmp_path, CLEAN_SKILL_HELPER)
    assert rc == 0
    # All three envelopes pass
    assert out.count('"overall_status": "pass"') == 3


def test_no_stdin_json_fails(tmp_path: Path):
    rc, out = _run(tmp_path, HELPER_NO_STDIN_JSON)
    assert rc == 1
    assert '"rule_id": "skill-helper-stdin-json"' in out
    # The fail finding text mentions the rule
    assert '"status": "fail"' in out


def test_non_atomic_and_flat_codes_warn(tmp_path: Path):
    rc, out = _run(tmp_path, HELPER_NON_ATOMIC_AND_FLAT_CODES)
    # No fail (stdin-json passes), only warns — exit 0
    assert rc == 0
    assert '"rule_id": "skill-helper-atomic-write"' in out
    assert '"rule_id": "skill-helper-distinct-error-codes"' in out
    # At least 2 warns total
    assert out.count('"status": "warn"') >= 2
