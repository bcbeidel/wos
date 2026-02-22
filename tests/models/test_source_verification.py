"""DDD protocol tests for VerificationResult and ReachabilityResult.

These models live in wos/source_verification.py but are tested here
alongside other domain model protocol tests.

Covers: frozen/immutable, hashable, equality, __str__, __repr__,
to_json, from_json, json round-trip, validate_self, is_valid,
and WosDomainObject protocol conformance.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.builders import make_reachability_result, make_verification_result
from wos.models import IssueSeverity, WosDomainObject
from wos.source_verification import ReachabilityResult, VerificationResult


# ══════════════════════════════════════════════════════════════════
# VerificationResult DDD protocol tests
# ══════════════════════════════════════════════════════════════════


class TestVerificationResultProtocol:
    """DDD protocol tests for VerificationResult."""

    # -- Frozen / immutable --

    def test_frozen_rejects_assignment(self):
        vr = make_verification_result()
        with pytest.raises(ValidationError):
            vr.url = "https://other.com"

    def test_hashable(self):
        vr = make_verification_result()
        assert isinstance(hash(vr), int)

    def test_hashable_in_set(self):
        v1 = make_verification_result()
        v2 = make_verification_result()
        assert len({v1, v2}) == 1

    def test_equality_same_values(self):
        v1 = make_verification_result()
        v2 = make_verification_result()
        assert v1 == v2

    def test_equality_different_values(self):
        v1 = make_verification_result(url="https://a.com")
        v2 = make_verification_result(url="https://b.com")
        assert v1 != v2

    # -- __str__ and __repr__ --

    def test_str_format(self):
        vr = make_verification_result(action="ok", url="https://example.com")
        assert str(vr) == "ok: https://example.com"

    def test_repr_format(self):
        vr = make_verification_result(
            action="ok", url="https://example.com", reason="Title matches"
        )
        assert repr(vr) == (
            "VerificationResult(action='ok', url='https://example.com', "
            "reason='Title matches')"
        )

    # -- to_json / from_json / round-trip --

    def test_to_json_returns_dict(self):
        vr = make_verification_result()
        data = vr.to_json()
        assert isinstance(data, dict)
        assert data["url"] == "https://example.com"
        assert data["cited_title"] == "Example"
        assert data["http_status"] == 200
        assert data["page_title"] == "Example Page"
        assert data["title_match"] is True
        assert data["action"] == "ok"
        assert data["reason"] == "Title matches"

    def test_from_json_constructs_instance(self):
        data = {
            "url": "https://example.com",
            "cited_title": "Example",
            "http_status": 200,
            "page_title": "Example Page",
            "title_match": True,
            "action": "ok",
            "reason": "Title matches",
        }
        vr = VerificationResult.from_json(data)
        assert isinstance(vr, VerificationResult)
        assert vr.url == "https://example.com"
        assert vr.action == "ok"

    def test_json_round_trip(self):
        original = make_verification_result()
        restored = VerificationResult.from_json(original.to_json())
        assert restored == original

    # -- validate_self / is_valid --

    def test_validate_self_valid_result(self):
        vr = make_verification_result()
        issues = vr.validate_self()
        assert issues == []

    def test_validate_self_invalid_action(self):
        vr = make_verification_result(action="invalid_action")
        issues = vr.validate_self()
        assert len(issues) == 1
        assert issues[0].severity == IssueSeverity.WARN
        assert "action" in issues[0].issue.lower() or "invalid" in issues[0].issue.lower()

    def test_is_valid_true(self):
        vr = make_verification_result()
        assert vr.is_valid is True

    def test_is_valid_false_bad_action(self):
        vr = make_verification_result(action="unknown")
        assert vr.is_valid is False

    # -- WosDomainObject protocol conformance --

    def test_protocol_conformance(self):
        vr = make_verification_result()
        assert isinstance(vr, WosDomainObject)

    def test_protocol_str(self):
        vr = make_verification_result()
        assert isinstance(str(vr), str)

    def test_protocol_repr(self):
        vr = make_verification_result()
        assert isinstance(repr(vr), str)

    def test_protocol_to_json(self):
        vr = make_verification_result()
        assert isinstance(vr.to_json(), dict)

    def test_protocol_from_json(self):
        data = {
            "url": "https://example.com",
            "cited_title": "Test",
            "http_status": 200,
            "page_title": "Test Page",
            "title_match": True,
            "action": "ok",
            "reason": "OK",
        }
        vr = VerificationResult.from_json(data)
        assert isinstance(vr, WosDomainObject)

    def test_protocol_validate_self(self):
        vr = make_verification_result()
        issues = vr.validate_self()
        assert isinstance(issues, list)

    def test_protocol_is_valid(self):
        vr = make_verification_result()
        assert isinstance(vr.is_valid, bool)


# ══════════════════════════════════════════════════════════════════
# ReachabilityResult DDD protocol tests
# ══════════════════════════════════════════════════════════════════


class TestReachabilityResultProtocol:
    """DDD protocol tests for ReachabilityResult."""

    # -- Frozen / immutable --

    def test_frozen_rejects_assignment(self):
        rr = make_reachability_result()
        with pytest.raises(ValidationError):
            rr.url = "https://other.com"

    def test_hashable(self):
        rr = make_reachability_result()
        assert isinstance(hash(rr), int)

    def test_hashable_in_set(self):
        r1 = make_reachability_result()
        r2 = make_reachability_result()
        assert len({r1, r2}) == 1

    def test_equality_same_values(self):
        r1 = make_reachability_result()
        r2 = make_reachability_result()
        assert r1 == r2

    def test_equality_different_values(self):
        r1 = make_reachability_result(url="https://a.com")
        r2 = make_reachability_result(url="https://b.com")
        assert r1 != r2

    # -- __str__ and __repr__ --

    def test_str_reachable(self):
        rr = make_reachability_result(reachable=True, url="https://example.com")
        assert str(rr) == "reachable: https://example.com"

    def test_str_unreachable(self):
        rr = make_reachability_result(reachable=False, url="https://example.com")
        assert str(rr) == "unreachable: https://example.com"

    def test_repr_format(self):
        rr = make_reachability_result(
            url="https://example.com", reachable=True, reason="OK"
        )
        assert repr(rr) == (
            "ReachabilityResult(reachable=True, url='https://example.com', "
            "reason='OK')"
        )

    # -- to_json / from_json / round-trip --

    def test_to_json_returns_dict(self):
        rr = make_reachability_result()
        data = rr.to_json()
        assert isinstance(data, dict)
        assert data["url"] == "https://example.com"
        assert data["http_status"] == 200
        assert data["reachable"] is True
        assert data["reason"] == "OK"
        assert data["final_url"] == "https://example.com"

    def test_from_json_constructs_instance(self):
        data = {
            "url": "https://example.com",
            "http_status": 200,
            "reachable": True,
            "reason": "OK",
            "final_url": "https://example.com",
        }
        rr = ReachabilityResult.from_json(data)
        assert isinstance(rr, ReachabilityResult)
        assert rr.url == "https://example.com"
        assert rr.reachable is True

    def test_json_round_trip(self):
        original = make_reachability_result()
        restored = ReachabilityResult.from_json(original.to_json())
        assert restored == original

    # -- validate_self / is_valid --

    def test_validate_self_valid_result(self):
        rr = make_reachability_result()
        issues = rr.validate_self()
        assert issues == []

    def test_is_valid_true(self):
        rr = make_reachability_result()
        assert rr.is_valid is True

    # -- WosDomainObject protocol conformance --

    def test_protocol_conformance(self):
        rr = make_reachability_result()
        assert isinstance(rr, WosDomainObject)

    def test_protocol_str(self):
        rr = make_reachability_result()
        assert isinstance(str(rr), str)

    def test_protocol_repr(self):
        rr = make_reachability_result()
        assert isinstance(repr(rr), str)

    def test_protocol_to_json(self):
        rr = make_reachability_result()
        assert isinstance(rr.to_json(), dict)

    def test_protocol_from_json(self):
        data = {
            "url": "https://example.com",
            "http_status": 200,
            "reachable": True,
            "reason": "OK",
            "final_url": "https://example.com",
        }
        rr = ReachabilityResult.from_json(data)
        assert isinstance(rr, WosDomainObject)

    def test_protocol_validate_self(self):
        rr = make_reachability_result()
        issues = rr.validate_self()
        assert isinstance(issues, list)

    def test_protocol_is_valid(self):
        rr = make_reachability_result()
        assert isinstance(rr.is_valid, bool)
