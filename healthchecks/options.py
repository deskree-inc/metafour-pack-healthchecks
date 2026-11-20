"""The Healthchecks.io options mapper: what the collector reads as ``ctx.source.options``.

It forwards every config field, and ``metafour-pack check`` fails when one is dropped. The API key is
added when the connection's secret resolves.
"""

from __future__ import annotations

from typing import Any


def build_options(config: dict[str, Any], secrets: dict[str, str]) -> dict[str, Any]:
    options = dict(config)
    if "api_key" in secrets:
        options["api_key"] = secrets["api_key"]
    return options
