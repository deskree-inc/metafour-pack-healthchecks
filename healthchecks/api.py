"""The Healthchecks API, as the template knows it: a fictional host and two endpoints.

Every request goes through ``RateLimitedClient``: it paces calls under the budget, honours the
runner's egress proxy, and is what ``pytest --record`` records and the cassettes replay.
"""

from __future__ import annotations

from typing import Any

from collector_sdk.http import RateBudget, RateLimitedClient

BASE_URL = "https://api.healthchecks.example/v1"
BUDGET = RateBudget(rate_per_sec=5, capacity=5)


def client(usage: Any = None) -> RateLimitedClient:
    """A client for one run or call. Pass the run's ``ctx.http_usage`` so Tetrix counts the calls."""
    return RateLimitedClient(budget=BUDGET, usage=usage)


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}
