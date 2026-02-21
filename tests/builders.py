"""Test builders for WOS domain objects.

Each make_*() function returns a valid domain object with sensible defaults.
Override any field via keyword arguments.
"""
from __future__ import annotations

from wos.models.core import CitedSource


def make_cited_source(**overrides) -> CitedSource:
    defaults = {
        "url": "https://example.com/article",
        "title": "Example Article",
    }
    defaults.update(overrides)
    return CitedSource(**defaults)
