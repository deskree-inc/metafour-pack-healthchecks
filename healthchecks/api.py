"""The Healthchecks.io Management API, v3: the one endpoint the pack reads, and what it derives.

Every request goes through ``RateLimitedClient``: it paces calls under the budget, honours the
runner's egress proxy, and is what ``pytest --record`` records and the cassettes replay.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any
from urllib.parse import urlsplit

from collector_sdk.http import RateBudget, RateLimitedClient

DEFAULT_BASE = "https://healthchecks.io"
#: Under the 100 requests a minute Healthchecks.io asks for.
BUDGET = RateBudget(rate_per_sec=1, capacity=2)
SERVICE_TAG = "service:"


class InstanceURLRefused(ValueError):
    """``api_base`` is not a bare ``https://host[:port]`` URL."""


def instance_base(value: Any) -> str:
    """``api_base`` rebuilt from its parsed scheme, host and port, the hosted service when empty.

    The API key goes to this host, so only ``https://host[:port]`` with an optional trailing ``/``
    passes: no other scheme, no user name or password, no path, query or fragment, no whitespace.
    The runner's egress proxy reads the same field with the same parser and opens exactly that host
    and port (``egress_from_config``), so the key cannot reach any other host. Whether the host's
    address is public is the proxy's check, not the pack's.
    """
    text = DEFAULT_BASE if value is None or not str(value).strip() else str(value).strip()
    if any(c.isspace() or not c.isprintable() for c in text):
        raise InstanceURLRefused("api_base: holds whitespace or a control character")
    parts = urlsplit(text)
    if parts.scheme != "https":
        raise InstanceURLRefused("api_base: must be an https:// URL")
    if "@" in parts.netloc:
        raise InstanceURLRefused("api_base: may not hold a user name or password")
    if "?" in text:
        raise InstanceURLRefused("api_base: may not hold a query")
    if "#" in text:
        raise InstanceURLRefused("api_base: may not hold a fragment")
    if parts.path not in ("", "/"):
        raise InstanceURLRefused("api_base: may not hold a path; give the instance's root URL")
    try:
        host, port = parts.hostname, parts.port
    except ValueError as exc:
        raise InstanceURLRefused("api_base: has an invalid port") from exc
    if not host:
        raise InstanceURLRefused("api_base: names no host")
    if port == 0:
        raise InstanceURLRefused("api_base: has an invalid port")
    netloc = f"[{host}]" if ":" in host else host
    return f"https://{netloc}" + (f":{port}" if port not in (None, 443) else "")


def checks_url(options: dict[str, Any]) -> str:
    """The checks list of the instance ``options["api_base"]`` names (:func:`instance_base`)."""
    return f"{instance_base(options.get('api_base'))}/api/v3/checks/"


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
