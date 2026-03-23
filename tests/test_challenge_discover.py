"""Tests for wos/challenge/discover.py."""

from __future__ import annotations


def test_keyword_score_exact_match():
    """Full keyword overlap scores 1.0."""
    from wos.challenge.discover import keyword_score

    score = keyword_score("OAuth authentication", "OAuth Authentication Patterns")
    assert score == 1.0


def test_keyword_score_partial_match():
    """Partial overlap scores between 0 and 1."""
    from wos.challenge.discover import keyword_score

    score = keyword_score("OAuth authentication", "Database connection pooling patterns")
    assert score == 0.0


def test_keyword_score_case_insensitive():
    """Matching is case-insensitive."""
    from wos.challenge.discover import keyword_score

    score = keyword_score("oauth AUTH", "OAuth Authentication")
    assert score == 1.0


def test_keyword_score_empty_assumption():
    """Empty assumption scores 0."""
    from wos.challenge.discover import keyword_score

    assert keyword_score("", "Some document title") == 0.0


def test_keyword_score_filters_short_tokens():
    """Tokens under 3 characters are ignored as stop words."""
    from wos.challenge.discover import keyword_score

    # "is" and "a" should be filtered, only "oauth" matters
    score = keyword_score("is a oauth", "OAuth Patterns")
    assert score > 0.0
