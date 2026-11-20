"""The Healthchecks.io Management API, v3: the one endpoint the pack reads, and what it derives.

Every request goes through ``RateLimitedClient``: it paces calls under the budget, honours the
runner's egress proxy, and is what ``pytest --record`` records and the cassettes replay.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any

from collector_sdk.http import RateBudget, RateLimitedClient

DEFAULT_BASE = "https://healthchecks.io"
#: Under the 100 requests a minute Healthchecks.io asks for.
BUDGET = RateBudget(rate_per_sec=1, capacity=2)
SERVICE_TAG = "service:"


def checks_url(options: dict[str, Any]) -> str:
    """The checks list of the instance ``options["api_base"]`` names, the hosted one by default."""
    base = str(options.get("api_base") or DEFAULT_BASE).strip().rstrip("/")
    return f"{base}/api/v3/checks/"


def client(usage: Any = None) -> RateLimitedClient:
    """A client for one run or call. Pass the run's ``ctx.http_usage`` so Tetrix counts the calls."""
    return RateLimitedClient(budget=BUDGET, usage=usage)


def headers(api_key: str) -> dict[str, str]:
    return {"X-Api-Key": api_key, "Accept": "application/json"}


def list_checks(options: dict[str, Any], usage: Any = None) -> list[dict[str, Any]]:
    response = client(usage).get(checks_url(options), headers=headers(options["api_key"]))
    response.raise_for_status()
    return response.json()["checks"]


def unique_key(check: dict[str, Any]) -> str:
    """The check's stable id, whichever key read it.

    A read-only key gets ``unique_key``; a read-write key gets ``uuid`` instead, and Healthchecks
    derives ``unique_key`` from it as the sha1 of the first 16 hex digits. The uuid is the check's
    ping secret, so it is used here and never stored.
    """
    if check.get("unique_key"):
        return check["unique_key"]
    return hashlib.sha1(uuid.UUID(check["uuid"]).hex[:16].encode()).hexdigest()


def service(check: dict[str, Any]) -> tuple[str, str] | None:
    """The service the check watches and where it came from: the first ``service:<name>`` tag, else
    the slug. None when it has neither."""
    for tag in str(check.get("tags") or "").split():
        if tag.startswith(SERVICE_TAG) and tag[len(SERVICE_TAG):]:
            return tag[len(SERVICE_TAG):], "tag"
    if check.get("slug"):
        return check["slug"], "slug"
    return None
