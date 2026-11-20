"""The inputs the pack's tests share: one ``E2ECase`` per source type.

The cassettes are the ``cassette`` fixture's files under ``tests/cassettes/test_pack/``, so the
in-process tests and ``pack_e2e`` replay the same recordings. ``tetrix-pack run sync --cassette
test_pack/test_collect`` replays one too.

To record against the real source, put a real token in ``TETRIX_PACK_CRED_TOKEN`` and run
``pytest --record``. The cassettes store ``<redacted:token>`` in its place. Replay matches whatever
token a test passes, so the default ``replay-token`` works. Redaction replaces that value
wherever it occurs in a request, so a replay value must occur nowhere else in a request: not in a
path, a query value or a body.

``cassette.configure`` takes two more arguments. ``secret_headers=("X-Token",)`` drops a header
that carries a credential, besides ``Authorization``, ``Cookie`` and ``X-Api-Key``, which are
always dropped. ``match_headers=("Accept",)`` keeps a header in the cassette and makes a replayed
request match only when its value is the recorded one.
"""

from __future__ import annotations

import os

import pytest

from tetrix_pack_kit.e2e import E2ECase

CASE = E2ECase(
    source_type="x-healthchecks",
    config={},
    credentials={"token": os.environ.get("TETRIX_PACK_CRED_TOKEN", "replay-token")},
    bad_credentials={"token": "replay-bad-token"},
    cassettes={
        "validate": "test_pack/test_validate_accepts_the_good_token",
        "validate_bad": "test_pack/test_validate_refuses_a_bad_token",
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
