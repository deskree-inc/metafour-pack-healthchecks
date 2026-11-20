"""The pack's tests. They run offline: a request no cassette answers fails its test.

- ``test_the_kit_finds_no_problem`` is ``metafour-pack check`` as one assertion.
- The validate and collect tests run the pack's code in this process, against the cassettes
  ``tests/conftest.py`` describes.
- ``test_end_to_end`` is ``pack_e2e``: the pack through every step the sandbox takes it, in a child
  process. It runs on Linux with the runner's Python (3.12), as in CI, and skips elsewhere.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from healthchecks import api
from healthchecks.validate import validate

KIND = "ext:x-healthchecks:check"
CASSETTES = Path(__file__).parent / "cassettes" / "test_pack"


def test_the_kit_finds_no_problem(pack_problems):
    assert pack_problems == []


def test_validate_accepts_the_good_key(pack, case, cassette):
    cassette.configure(secrets=case.credentials)
    spec = pack.pack.source_types[0]
    assert validate(spec=spec, credentials=dict(case.credentials), config=dict(case.config)) is True


def test_validate_refuses_a_bad_key(pack, case, cassette):
    cassette.configure(secrets=case.bad_credentials)
    spec = pack.pack.source_types[0]
    assert validate(spec=spec, credentials=dict(case.bad_credentials), config=dict(case.config)) is False


def test_collect(case, cassette, run_collect):
    cassette.configure(secrets=case.credentials)
    out = run_collect(case.source_type, dict(case.config), dict(case.credentials))
    assert out.ok and not out.refused
    rows = {e.name: e for e in out.entities}
    assert {name: (e.attributes.get("service"), e.attributes.get("service_from"))
            for name, e in rows.items()} == {
        "Checkout API": ("checkout", "tag"),          # the service: tag
        "search": ("search", "slug"),                 # no service: tag, so the slug
        "Nightly backup": (None, None),               # neither: nothing for the rule to match
        "Payments webhook": ("payments", "tag"),      # two service: tags: the first
    }
    assert all(e.kind == KIND and e.natural_key.startswith(f"{KIND}:") for e in rows.values())
    assert rows["Checkout API"].attributes["tags"] == ["service:checkout", "prod"]
    assert rows["Payments webhook"].attributes["status"] == "down"
    assert not any(key in e.attributes for e in rows.values()
                   for key in ("uuid", "ping_url", "update_url"))


def test_a_read_write_key_gives_the_natural_key_a_read_only_key_does():
    """A read-write key returns ``uuid`` where a read-only key returns ``unique_key``. The pack
    derives the second from the first, so a connection keeps its rows when its key is swapped.
    The uuid is the seed's fixed code for the check the recording lists first (dev/seed.py)."""
    recorded = json.loads(json.loads((CASSETTES / "test_collect.json").read_text())
                          ["interactions"][0]["response"]["body"])["checks"]
    checkout = next(c for c in recorded if c["name"] == "Checkout API")
    assert api.unique_key({"uuid": "11dd3f6e-4d55-42bd-8a9d-5a99577a4159"}) == checkout["unique_key"]


@pytest.mark.parametrize(("value", "url"), [
    (None, "https://healthchecks.io/api/v3/checks/"),
    ("", "https://healthchecks.io/api/v3/checks/"),
    ("https://hc.example.org", "https://hc.example.org/api/v3/checks/"),
    (" https://HC.Example.org/ ", "https://hc.example.org/api/v3/checks/"),
    ("https://hc.example.org:8443", "https://hc.example.org:8443/api/v3/checks/"),
    ("https://hc.example.org:443/", "https://hc.example.org/api/v3/checks/"),
])
def test_the_instance_url_defaults_to_the_hosted_service_and_takes_a_self_hosted_one(value, url):
    assert api.checks_url({"api_base": value}) == url


@pytest.mark.parametrize("value", [
    "https://hc.example.org", "https://HC.example.org:8443/", "https://[2001:db8::1]:8443",
])
def test_the_url_reaches_exactly_the_host_and_port_the_egress_proxy_opens(value):
    """The proxy reads ``api_base`` with ``urlsplit`` and opens its host on its port, or 443
    (egress_from_config). The pack's URL names the same pair, so the key goes nowhere else."""
    declared, used = urlsplit(value), urlsplit(api.checks_url({"api_base": value}))
    assert (used.hostname, used.port or 443) == (declared.hostname, declared.port or 443)


@pytest.mark.parametrize(("value", "reason"), [
    ("http://hc.example.org", "must be an https:// URL"),
    ("hc.example.org", "must be an https:// URL"),
    ("ftp://hc.example.org", "must be an https:// URL"),
    ("https://user:pass@hc.example.org", "user name or password"),
    ("https://healthchecks.io@evil.example", "user name or password"),
    ("https://hc.example.org/?next=evil.example", "query"),
    ("https://hc.example.org?", "query"),
    ("https://hc.example.org/#frag", "fragment"),
    ("https://hc.example.org/api/v3", "path"),
    ("https://evil.example/hc.example.org", "path"),
    ("https://", "names no host"),
    ("https://hc.example.org:99999", "invalid port"),
    ("https://hc.example.org:0", "invalid port"),
    ("https://hc.example.org\t/", "whitespace or a control character"),
    ("https://hc.exa mple.org", "whitespace or a control character"),
])
def test_an_instance_url_that_could_send_the_key_elsewhere_is_refused(value, reason):
    with pytest.raises(api.InstanceURLRefused, match=reason):
        api.checks_url({"api_base": value})


def test_validate_refuses_a_bad_instance_url_before_any_request(pack):
    """No cassette: a request would fail the test. The refusal fails the call, so no connection is
    created with that URL."""
    with pytest.raises(api.InstanceURLRefused):
        validate(spec=pack.pack.source_types[0], credentials={"api_key": "replay-key"},
                 config={"api_base": "https://hc.example.org/?x=1"})


def test_end_to_end(pack_e2e):
    pack_e2e.run()
