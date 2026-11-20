"""The Healthchecks credential check: ``GET /v1/account``.

200 is true and 401 or 403 is false. Any other answer raises ``ProbeUnavailable``, which tells Tetrix
the source gave no verdict, so the credential is not reported as wrong.
"""

from __future__ import annotations

from typing import Any

from collector_sdk.packs import SourceTypeSpec
from collector_sdk.packs.errors import ProbeUnavailable

from healthchecks import api


def validate(*, spec: SourceTypeSpec, credentials: dict[str, str], config: dict[str, Any]) -> bool:
    del spec, config
    response = api.client().get(f"{api.BASE_URL}/account", headers=api.headers(credentials["token"]))
    if response.status_code == 200:
        return True
    if response.status_code in (401, 403):
        return False
    raise ProbeUnavailable(f"GET /v1/account answered {response.status_code}")
