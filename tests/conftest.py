"""The inputs the pack's tests share: one ``E2ECase`` per source type.

The cassettes are the ``cassette`` fixture's files under ``tests/cassettes/test_pack/``, so the
in-process tests and ``pack_e2e`` replay the same recordings. ``tetrix-pack run sync --config
tests/config.json --cassette test_pack/test_collect`` replays one too.

They were recorded by ``dev/record.sh record`` against a self-hosted Healthchecks instance that
``dev/compose.yaml`` serves as ``https://healthchecks.test``, seeded by ``dev/seed.py``. That is why
the config names that instance. No Healthchecks.io account was used. The recording passes the
instance's read-only key in ``TETRIX_PACK_CRED_API_KEY``; the cassettes drop the ``X-Api-Key``
header and store ``<redacted:api_key>`` wherever the key occurred. Replay matches whatever key a
test passes, so the default ``replay-key`` works.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tetrix_pack_kit.e2e import E2ECase

CONFIG = json.loads((Path(__file__).parent / "config.json").read_text())

CASE = E2ECase(
    source_type="x-healthchecks",
    config=CONFIG,
    credentials={"api_key": os.environ.get("TETRIX_PACK_CRED_API_KEY", "replay-key")},
    # 32 characters with the read-only prefix, so the instance answers "wrong api key", not
    # "missing api key". Both are 401.
    bad_credentials={"api_key": "hcr_notarealkeynotarealkey000000"},
    cassettes={
        "validate": "test_pack/test_validate_accepts_the_good_key",
        "validate_bad": "test_pack/test_validate_refuses_a_bad_key",
        "sync": "test_pack/test_collect",
        "delta": "test_pack/test_collect",
    },
)


@pytest.fixture
def case() -> E2ECase:
    return CASE


@pytest.fixture
def pack_e2e_cases() -> list[E2ECase]:
    return [CASE]
