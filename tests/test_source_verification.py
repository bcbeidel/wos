"""Tests for wos.source_verification — source URL verification.

All tests use inline data (no fixture files).
"""

from __future__ import annotations

from wos.source_verification import extract_page_title, normalize_title, titles_match


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


# ── extract_page_title ────────────────────────────────────────────


def test_extract_title_tag():
    html = "<html><head><title>My Page</title></head><body></body></html>"
    assert extract_page_title(html) == "My Page"


def test_extract_title_tag_with_whitespace():
    html = "<html><head><title>  My Page  \n</title></head><body></body></html>"
    assert extract_page_title(html) == "My Page"


def test_extract_h1_fallback():
    html = "<html><head></head><body><h1>Main Heading</h1></body></html>"
    assert extract_page_title(html) == "Main Heading"


def test_extract_title_prefers_title_over_h1():
    html = (
        "<html><head><title>Title Tag</title></head>"
        "<body><h1>H1 Heading</h1></body></html>"
    )
    assert extract_page_title(html) == "Title Tag"


def test_extract_no_title_returns_none():
    html = "<html><head></head><body><p>Just a paragraph</p></body></html>"
    assert extract_page_title(html) is None


def test_extract_empty_title_falls_back_to_h1():
    html = (
        "<html><head><title>  </title></head>"
        "<body><h1>Fallback Heading</h1></body></html>"
    )
    assert extract_page_title(html) == "Fallback Heading"


def test_extract_empty_html():
    assert extract_page_title("") is None
