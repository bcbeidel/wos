"""WOS Domain Object Protocol.

Defines the structural typing contract that all WOS domain objects must satisfy.
Uses typing.Protocol (PEP 544) — no inheritance required, checked via
isinstance() at runtime and by mypy/pyright statically.
"""

from __future__ import annotations

from typing import List, Protocol, runtime_checkable


@runtime_checkable
class WosDomainObject(Protocol):
    """Protocol all WOS domain objects must implement.

    Value objects, documents, and aggregates all satisfy this contract.
    Use ``isinstance(obj, WosDomainObject)`` to verify conformance at runtime.
    """

    def __str__(self) -> str:
        """Human-readable display (CLI output, logs)."""
        ...

    def __repr__(self) -> str:
        """Debug representation."""
        ...

    def to_json(self) -> dict:
        """JSON-serializable dict."""
        ...

    @classmethod
    def from_json(cls, data: dict) -> WosDomainObject:
        """Construct from a JSON-compatible dict."""
        ...

    def validate_self(self, **kwargs) -> List:
        """Non-throwing internal consistency check.

        Returns list[ValidationIssue]. Keyword args allow deep=True for I/O checks.
        """
        ...

    @property
    def is_valid(self) -> bool:
        """True if validate_self() returns no issues."""
        ...
