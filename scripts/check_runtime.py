#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["httpx"]
# ///
"""Canary: verify uv can run PEP 723 scripts with inline dependencies.

Usage:
    uv run scripts/check_runtime.py
    python3 scripts/check_runtime.py  (will fail without httpx — expected)
"""
from __future__ import annotations

import argparse
import json
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify uv + PEP 723 dependency resolution pipeline.",
    )
    parser.parse_args()

    try:
        import httpx

        print(
            json.dumps(
                {
                    "status": "ok",
                    "python": sys.version.split()[0],
                    "httpx": httpx.__version__,
                }
            )
        )
    except ImportError:
        print(
            json.dumps(
                {
                    "status": "fail",
                    "error": "httpx import failed — uv dependency resolution did not run",
                }
            )
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
