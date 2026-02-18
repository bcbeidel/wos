"""Tests for wos.source_verification — source URL verification.

All tests use inline data (no fixture files).
"""

from __future__ import annotations

from wos.source_verification import normalize_title, titles_match


# ── normalize_title ───────────────────────────────────────────────


def test_normalize_lowercases():
    assert normalize_title("Hello World") == "hello world"


def test_normalize_strips_punctuation():
    assert normalize_title("Hello, World!") == "hello world"


def test_normalize_collapses_whitespace():
    assert normalize_title("hello   world") == "hello world"


def test_normalize_strips_unicode_dashes():
    assert normalize_title("hello\u2013world\u2014test") == "hello world test"


# ── titles_match ──────────────────────────────────────────────────


def test_titles_match_exact():
    assert titles_match("Python Tutorial", "Python Tutorial") is True


def test_titles_match_substring_cited_in_page():
    assert titles_match("Python Tutorial", "Python Tutorial - Official Docs") is True


def test_titles_match_substring_page_in_cited():
    assert titles_match("Python Tutorial - Official Docs", "Python Tutorial") is True


def test_titles_match_case_insensitive():
    assert titles_match("python tutorial", "PYTHON TUTORIAL") is True


def test_titles_no_match():
    assert titles_match("Python Tutorial", "Java Reference") is False
