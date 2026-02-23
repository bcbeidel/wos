"""Tests for wos.url_checker — HTTP HEAD/GET URL reachability checks.

All HTTP calls are mocked. No network traffic in tests.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import requests

from wos.url_checker import UrlCheckResult, check_url, check_urls


# ── UrlCheckResult dataclass ─────────────────────────────────────


def test_url_check_result_reachable() -> None:
    """UrlCheckResult stores reachable=True with status and no reason."""
    result = UrlCheckResult(url="https://example.com", status=200, reachable=True)
    assert result.url == "https://example.com"
    assert result.status == 200
    assert result.reachable is True
    assert result.reason is None


def test_url_check_result_unreachable_with_reason() -> None:
    """UrlCheckResult stores reachable=False with reason string."""
    result = UrlCheckResult(
        url="https://example.com/missing",
        status=404,
        reachable=False,
        reason="HTTP 404: not found",
    )
    assert result.url == "https://example.com/missing"
    assert result.status == 404
    assert result.reachable is False
    assert result.reason == "HTTP 404: not found"


# ── check_url ────────────────────────────────────────────────────


def _mock_response(status_code: int = 200) -> MagicMock:
    """Create a mock requests.Response with the given status code."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    return resp


@patch("wos.url_checker.requests.head")
def test_check_url_200_reachable(mock_head: MagicMock) -> None:
    """HTTP 200 response marks URL as reachable."""
    mock_head.return_value = _mock_response(200)
    result = check_url("https://example.com/page")
    assert result.reachable is True
    assert result.status == 200
    assert result.reason is None
    mock_head.assert_called_once_with(
        "https://example.com/page",
        timeout=10,
        headers={"User-Agent": "wos-url-checker/1.0"},
    )


@patch("wos.url_checker.requests.head")
def test_check_url_404_unreachable(mock_head: MagicMock) -> None:
    """HTTP 404 response marks URL as unreachable."""
    mock_head.return_value = _mock_response(404)
    result = check_url("https://example.com/missing")
    assert result.reachable is False
    assert result.status == 404
    assert result.reason is not None


@patch("wos.url_checker.requests.get")
@patch("wos.url_checker.requests.head")
def test_check_url_head_405_falls_back_to_get(
    mock_head: MagicMock, mock_get: MagicMock
) -> None:
    """HEAD returning 405 triggers a GET fallback with stream=True."""
    mock_head.return_value = _mock_response(405)
    mock_get.return_value = _mock_response(200)
    result = check_url("https://example.com/no-head")
    assert result.reachable is True
    assert result.status == 200
    mock_head.assert_called_once()
    mock_get.assert_called_once_with(
        "https://example.com/no-head",
        timeout=10,
        stream=True,
        headers={"User-Agent": "wos-url-checker/1.0"},
    )


@patch("wos.url_checker.requests.head")
def test_check_url_connection_error(mock_head: MagicMock) -> None:
    """Connection error returns status=0, reachable=False."""
    mock_head.side_effect = requests.ConnectionError("DNS resolution failed")
    result = check_url("https://nonexistent.example.com")
    assert result.reachable is False
    assert result.status == 0
    assert result.reason is not None
    assert "DNS resolution failed" in result.reason


@patch("wos.url_checker.requests.head")
def test_check_url_timeout(mock_head: MagicMock) -> None:
    """Timeout returns status=0, reachable=False."""
    mock_head.side_effect = requests.Timeout("Request timed out")
    result = check_url("https://slow.example.com")
    assert result.reachable is False
    assert result.status == 0
    assert result.reason is not None
    assert "Request timed out" in result.reason


def test_check_url_invalid_scheme() -> None:
    """Non-HTTP/HTTPS URLs return reachable=False immediately."""
    result = check_url("ftp://files.example.com/data.csv")
    assert result.reachable is False
    assert result.status == 0
    assert result.reason is not None
    assert "http" in result.reason.lower() or "https" in result.reason.lower()


# ── check_urls (batch) ───────────────────────────────────────────


@patch("wos.url_checker.requests.head")
def test_check_urls_batch(mock_head: MagicMock) -> None:
    """Batch check returns a result for each unique URL."""

    def side_effect(url: str, **kwargs: object) -> MagicMock:
        if "good" in url:
            return _mock_response(200)
        return _mock_response(404)

    mock_head.side_effect = side_effect

    results = check_urls([
        "https://example.com/good",
        "https://example.com/missing",
    ])
    assert len(results) == 2
    assert results[0].reachable is True
    assert results[1].reachable is False


def test_check_urls_empty_list() -> None:
    """Empty input returns empty output without any HTTP calls."""
    results = check_urls([])
    assert results == []


@patch("wos.url_checker.requests.head")
def test_check_urls_deduplicates(mock_head: MagicMock) -> None:
    """Duplicate URLs are checked only once."""
    mock_head.return_value = _mock_response(200)
    results = check_urls([
        "https://example.com/page",
        "https://example.com/page",
        "https://example.com/page",
    ])
    # Returns one result per unique URL
    assert len(results) == 1
    assert results[0].url == "https://example.com/page"
    # HEAD called only once despite three input URLs
    mock_head.assert_called_once()
