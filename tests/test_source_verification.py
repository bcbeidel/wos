"""Tests for wos.source_verification — source URL verification.

All tests use inline data (no fixture files).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import requests

from wos.source_verification import (
    VerificationResult,
    extract_page_title,
    normalize_title,
    titles_match,
    verify_source,
)


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


# ── verify_source helpers ─────────────────────────────────────────


def _mock_response(
    status_code: int = 200,
    text: str = "",
    url: str = "https://example.com",
) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.text = text
    resp.url = url
    return resp


# ── verify_source ─────────────────────────────────────────────────


@patch("wos.source_verification.requests.get")
def test_200_title_match(mock_get: MagicMock) -> None:
    mock_get.return_value = _mock_response(
        text="<html><head><title>Python Tutorial</title></head></html>",
        url="https://example.com/tutorial",
    )
    result = verify_source("https://example.com/tutorial", "Python Tutorial")
    assert result.action == "ok"
    assert result.title_match is True
    assert result.http_status == 200


@patch("wos.source_verification.requests.get")
def test_200_title_mismatch(mock_get: MagicMock) -> None:
    mock_get.return_value = _mock_response(
        text="<html><head><title>Java Reference</title></head></html>",
        url="https://example.com/tutorial",
    )
    result = verify_source("https://example.com/tutorial", "Python Tutorial")
    assert result.action == "flagged"
    assert result.title_match is False
    assert "title mismatch" in result.reason.lower()


@patch("wos.source_verification.requests.get")
def test_200_no_title_tag(mock_get: MagicMock) -> None:
    mock_get.return_value = _mock_response(
        text="<html><body><p>No title here</p></body></html>",
        url="https://example.com/page",
    )
    result = verify_source("https://example.com/page", "Some Title")
    assert result.action == "ok"
    assert result.title_match is None
    assert result.page_title is None


@patch("wos.source_verification.requests.get")
def test_404(mock_get: MagicMock) -> None:
    mock_get.return_value = _mock_response(
        status_code=404, url="https://example.com/missing"
    )
    result = verify_source("https://example.com/missing", "Gone Page")
    assert result.action == "removed"
    assert result.http_status == 404


@patch("wos.source_verification.requests.get")
def test_403_paywall(mock_get: MagicMock) -> None:
    mock_get.return_value = _mock_response(
        status_code=403, url="https://example.com/paid"
    )
    result = verify_source("https://example.com/paid", "Paywalled Article")
    assert result.action == "flagged"
    assert result.http_status == 403
    assert "paywall" in result.reason.lower() or "403" in result.reason


@patch("wos.source_verification.requests.get")
def test_5xx(mock_get: MagicMock) -> None:
    mock_get.return_value = _mock_response(
        status_code=500, url="https://example.com/error"
    )
    result = verify_source("https://example.com/error", "Server Error Page")
    assert result.action == "flagged"
    assert result.http_status == 500


@patch("wos.source_verification.requests.get")
def test_dns_failure(mock_get: MagicMock) -> None:
    mock_get.side_effect = requests.ConnectionError("DNS resolution failed")
    result = verify_source("https://nonexistent.example.com", "Gone Site")
    assert result.action == "removed"
    assert result.http_status is None
    assert "connection" in result.reason.lower()


@patch("wos.source_verification.requests.get")
def test_timeout(mock_get: MagicMock) -> None:
    mock_get.side_effect = requests.Timeout("Request timed out")
    result = verify_source("https://slow.example.com", "Slow Page")
    assert result.action == "removed"
    assert result.http_status is None
    assert "timeout" in result.reason.lower()


@patch("wos.source_verification.requests.get")
def test_redirect_same_domain(mock_get: MagicMock) -> None:
    mock_get.return_value = _mock_response(
        text="<html><head><title>Python Tutorial</title></head></html>",
        url="https://example.com/new-path",
    )
    result = verify_source("https://example.com/old-path", "Python Tutorial")
    assert result.action == "ok"


@patch("wos.source_verification.requests.get")
def test_redirect_different_domain(mock_get: MagicMock) -> None:
    mock_get.return_value = _mock_response(
        text="<html><head><title>Python Tutorial</title></head></html>",
        url="https://other-domain.com/page",
    )
    result = verify_source("https://example.com/old-path", "Python Tutorial")
    assert result.action == "flagged"
    assert "redirect" in result.reason.lower()


@patch("wos.source_verification.requests.get")
def test_title_normalization_match(mock_get: MagicMock) -> None:
    mock_get.return_value = _mock_response(
        text="<html><head><title>PYTHON TUTORIAL!</title></head></html>",
        url="https://example.com/tutorial",
    )
    result = verify_source("https://example.com/tutorial", "python tutorial")
    assert result.action == "ok"
    assert result.title_match is True
