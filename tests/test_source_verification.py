"""Tests for wos.source_verification — source URL verification.

All tests use inline data (no fixture files).
"""

from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch

import requests

from wos.source_verification import (
    ReachabilityResult,
    VerificationResult,
    check_url_reachability,
    extract_page_title,
    format_summary,
    main,
    normalize_title,
    titles_match,
    verify_source,
    verify_sources,
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


def test_titles_match_empty_cited():
    """Empty cited title (after normalization) should not match anything."""
    assert titles_match("!!!", "Python Tutorial") is False


def test_titles_match_empty_page():
    """Empty page title (after normalization) should not match anything."""
    assert titles_match("Python Tutorial", "!!!") is False


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
def test_request_exception_catchall(mock_get: MagicMock) -> None:
    """Unexpected RequestException (e.g. TooManyRedirects) should be flagged."""
    mock_get.side_effect = requests.exceptions.TooManyRedirects(
        "Exceeded max redirects"
    )
    result = verify_source("https://loop.example.com", "Loop Page")
    assert result.action == "flagged"
    assert result.http_status is None
    assert "request error" in result.reason.lower()


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


# ── verify_sources (batch) ────────────────────────────────────────


@patch("wos.source_verification.requests.get")
def test_batch_mixed(mock_get: MagicMock) -> None:
    """Three sources: one good, one 404, one title mismatch."""

    def side_effect(url: str, **kwargs: object) -> MagicMock:
        if "good" in url:
            return _mock_response(
                text="<html><head><title>Good Page</title></head></html>",
                url=url,
            )
        if "missing" in url:
            return _mock_response(status_code=404, url=url)
        # title mismatch
        return _mock_response(
            text="<html><head><title>Wrong Title</title></head></html>",
            url=url,
        )

    mock_get.side_effect = side_effect
    sources = [
        {"url": "https://example.com/good", "title": "Good Page"},
        {"url": "https://example.com/missing", "title": "Gone"},
        {"url": "https://example.com/mismatch", "title": "Expected Title"},
    ]
    results = verify_sources(sources)
    assert len(results) == 3
    assert results[0].action == "ok"
    assert results[1].action == "removed"
    assert results[2].action == "flagged"


@patch("wos.source_verification.requests.get")
def test_batch_empty(mock_get: MagicMock) -> None:
    results = verify_sources([])
    assert results == []
    mock_get.assert_not_called()


# ── format_summary ────────────────────────────────────────────────


def test_format_summary_counts() -> None:
    results = [
        VerificationResult(
            url="u1", cited_title="t1", http_status=200,
            page_title="t1", title_match=True, action="ok", reason="ok",
        ),
        VerificationResult(
            url="u2", cited_title="t2", http_status=200,
            page_title="t2", title_match=True, action="ok", reason="ok",
        ),
        VerificationResult(
            url="u3", cited_title="t3", http_status=404,
            page_title=None, title_match=None, action="removed", reason="404",
        ),
        VerificationResult(
            url="u4", cited_title="t4", http_status=200,
            page_title="wrong", title_match=False, action="flagged",
            reason="mismatch",
        ),
    ]
    summary = format_summary(results)
    assert summary == {"total": 4, "ok": 2, "removed": 1, "flagged": 1}


# ── CLI (main) ────────────────────────────────────────────────────


@patch("wos.source_verification.requests.get")
def test_cli_json_output(mock_get: MagicMock) -> None:
    """main() writes valid JSON to stdout with results and summary."""
    mock_get.return_value = _mock_response(
        text="<html><head><title>Good Page</title></head></html>",
        url="https://example.com/good",
    )
    stdin_data = json.dumps([
        {"url": "https://example.com/good", "title": "Good Page"},
    ])
    stdout = io.StringIO()
    stderr = io.StringIO()
    with patch("sys.stdin", io.StringIO(stdin_data)), \
         patch("sys.stdout", stdout), \
         patch("sys.stderr", stderr):
        try:
            main()
        except SystemExit as e:
            assert e.code == 0

    output = json.loads(stdout.getvalue())
    assert "results" in output
    assert "summary" in output
    assert len(output["results"]) == 1
    assert output["results"][0]["action"] == "ok"
    assert output["summary"]["total"] == 1


@patch("wos.source_verification.requests.get")
def test_cli_exit_code_zero_when_all_ok(mock_get: MagicMock) -> None:
    mock_get.return_value = _mock_response(
        text="<html><head><title>Good Page</title></head></html>",
        url="https://example.com/good",
    )
    stdin_data = json.dumps([
        {"url": "https://example.com/good", "title": "Good Page"},
    ])
    stdout = io.StringIO()
    stderr = io.StringIO()
    with patch("sys.stdin", io.StringIO(stdin_data)), \
         patch("sys.stdout", stdout), \
         patch("sys.stderr", stderr):
        try:
            main()
            exit_code = 0
        except SystemExit as e:
            exit_code = e.code

    assert exit_code == 0


@patch("wos.source_verification.requests.get")
def test_cli_exit_code_one_when_removed(mock_get: MagicMock) -> None:
    mock_get.return_value = _mock_response(
        status_code=404, url="https://example.com/missing"
    )
    stdin_data = json.dumps([
        {"url": "https://example.com/missing", "title": "Gone Page"},
    ])
    stdout = io.StringIO()
    stderr = io.StringIO()
    with patch("sys.stdin", io.StringIO(stdin_data)), \
         patch("sys.stdout", stdout), \
         patch("sys.stderr", stderr):
        try:
            main()
            exit_code = 0
        except SystemExit as e:
            exit_code = e.code

    assert exit_code == 1


# ── ReachabilityResult ───────────────────────────────────────────


def test_reachability_result_fields():
    r = ReachabilityResult(
        url="https://example.com",
        http_status=200,
        reachable=True,
        reason="OK",
        final_url="https://example.com",
    )
    assert r.url == "https://example.com"
    assert r.reachable is True
    assert r.http_status == 200


# ── check_url_reachability ───────────────────────────────────────


@patch("wos.source_verification.requests.head")
def test_reachability_200(mock_head: MagicMock) -> None:
    mock_head.return_value = _mock_response(
        status_code=200, url="https://example.com/page"
    )
    result = check_url_reachability("https://example.com/page")
    assert result.reachable is True
    assert result.http_status == 200
    assert result.reason == "OK"
    mock_head.assert_called_once()


@patch("wos.source_verification.requests.head")
def test_reachability_404(mock_head: MagicMock) -> None:
    mock_head.return_value = _mock_response(
        status_code=404, url="https://example.com/missing"
    )
    result = check_url_reachability("https://example.com/missing")
    assert result.reachable is False
    assert result.http_status == 404
    assert "404" in result.reason


@patch("wos.source_verification.requests.head")
def test_reachability_403(mock_head: MagicMock) -> None:
    mock_head.return_value = _mock_response(
        status_code=403, url="https://example.com/paid"
    )
    result = check_url_reachability("https://example.com/paid")
    assert result.reachable is False
    assert result.http_status == 403
    assert "403" in result.reason


@patch("wos.source_verification.requests.head")
def test_reachability_5xx(mock_head: MagicMock) -> None:
    mock_head.return_value = _mock_response(
        status_code=502, url="https://example.com/error"
    )
    result = check_url_reachability("https://example.com/error")
    assert result.reachable is False
    assert result.http_status == 502


@patch("wos.source_verification.requests.head")
def test_reachability_connection_error(mock_head: MagicMock) -> None:
    mock_head.side_effect = requests.ConnectionError("DNS failed")
    result = check_url_reachability("https://nonexistent.example.com")
    assert result.reachable is False
    assert result.http_status is None
    assert "connection" in result.reason.lower()


@patch("wos.source_verification.requests.head")
def test_reachability_timeout(mock_head: MagicMock) -> None:
    mock_head.side_effect = requests.Timeout("Timed out")
    result = check_url_reachability("https://slow.example.com")
    assert result.reachable is False
    assert result.http_status is None
    assert "timeout" in result.reason.lower()


@patch("wos.source_verification.requests.head")
def test_reachability_cross_domain_redirect(mock_head: MagicMock) -> None:
    mock_head.return_value = _mock_response(
        status_code=200, url="https://other-domain.com/page"
    )
    result = check_url_reachability("https://example.com/old")
    assert result.reachable is False
    assert "redirect" in result.reason.lower()
    assert result.final_url == "https://other-domain.com/page"


@patch("wos.source_verification.requests.get")
@patch("wos.source_verification.requests.head")
def test_reachability_head_405_falls_back_to_get(
    mock_head: MagicMock, mock_get: MagicMock
) -> None:
    mock_head.return_value = _mock_response(
        status_code=405, url="https://example.com/page"
    )
    mock_get.return_value = _mock_response(
        status_code=200, url="https://example.com/page"
    )
    result = check_url_reachability("https://example.com/page")
    assert result.reachable is True
    assert result.http_status == 200
    mock_head.assert_called_once()
    mock_get.assert_called_once()
