"""The pack's tests. They run offline: a request no cassette answers fails its test.

- ``test_the_kit_finds_no_problem`` is ``tetrix-pack check`` as one assertion.
- The validate and collect tests run the pack's code in this process, against the cassettes
  ``tests/conftest.py`` describes.
- ``test_end_to_end`` is ``pack_e2e``: the pack through every step the sandbox takes it, in a child
  process. It runs on Linux with the runner's Python (3.12), as in CI, and skips elsewhere.
"""

from __future__ import annotations

from healthchecks.validate import validate


def test_the_kit_finds_no_problem(pack_problems):
    assert pack_problems == []


def test_validate_accepts_the_good_token(pack, case, cassette):
    cassette.configure(secrets=case.credentials)
    spec = pack.pack.source_types[0]
    assert validate(spec=spec, credentials=dict(case.credentials), config=dict(case.config)) is True


def test_validate_refuses_a_bad_token(pack, case, cassette):
    cassette.configure(secrets=case.bad_credentials)
    spec = pack.pack.source_types[0]
    assert validate(spec=spec, credentials=dict(case.bad_credentials), config=dict(case.config)) is False


def test_collect(case, cassette, run_collect):
    cassette.configure(secrets=case.credentials)
    out = run_collect(case.source_type, dict(case.config), dict(case.credentials))
    assert out.ok and not out.refused
    assert [(e.natural_key, e.attributes["service"]) for e in out.entities] == [
        ("ext:x-healthchecks:check:chk-1", "checkout"),
        ("ext:x-healthchecks:check:chk-2", "search"),
    ]


def test_end_to_end(pack_e2e):
    pack_e2e.run()
