"""The Healthchecks.io credential check: ``GET /api/v3/checks/`` with the key.

200 is true and 401 or 403 is false. Any other answer raises ``ProbeUnavailable``, which tells Tetrix
the source gave no verdict, so the key is not reported as wrong.
"""

from __future__ import annotations

from typing import Any

from collector_sdk.packs import SourceTypeSpec
from collector_sdk.packs.errors import ProbeUnavailable

from healthchecks import api


def validate(*, spec: SourceTypeSpec, credentials: dict[str, str], config: dict[str, Any]) -> bool:
    del spec
    response = api.client().get(api.checks_url(config), headers=api.headers(credentials["api_key"]))
    if response.status_code == 200:
        return True
    if response.status_code in (401, 403):
        return False
    raise ProbeUnavailable(f"GET /api/v3/checks/ answered {response.status_code}")
