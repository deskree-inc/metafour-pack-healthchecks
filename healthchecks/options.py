"""The Healthchecks options mapper: what the collector reads as ``ctx.source.options``.

It forwards every config field, and ``tetrix-pack check`` fails when one is dropped. The token is
added when the connection's secret resolves.
"""

from __future__ import annotations

from typing import Any


def build_options(config: dict[str, Any], secrets: dict[str, str]) -> dict[str, Any]:
    options = dict(config)
    if "token" in secrets:
        options["token"] = secrets["token"]
    return options
