"""The Healthchecks.io pack's manifest. Metafour reads the data the build makes from it, never this file.

The pack id is permanent: every kind and natural key embeds it.
"""

from __future__ import annotations

import base64
from pathlib import Path

from collector_sdk.packs import (
    ConfigField,
    CredentialField,
    EgressHost,
    JoinRule,
    KindDecl,
    MatchKey,
    MatchSet,
    RuleSide,
    SourcePack,
    SourceTypeSpec,
    TriggerDecl,
)

_ST = "x-healthchecks"
_PKG = "healthchecks"
_CHECK = "ext:x-healthchecks:check"
# The icon is read from the package, because the artifact carries pack.py and the packages only.
_ICON = "data:image/png;base64," + base64.b64encode(
    (Path(__file__).parent / _PKG / "icon.png").read_bytes()).decode("ascii")

PACK = SourcePack(
    id="x-healthchecks",
    version="0.1.1",
    contract=3,                             # a literal, never PACK_CONTRACT_VERSION
    display_name="Healthchecks.io",
    description="Cron and heartbeat checks from Healthchecks.io, hosted or self-hosted.",
    packages=(_PKG,),
    python_requires=(),                     # the SDK's own httpx is all it needs
    egress=(EgressHost("healthchecks.io"),),
    source_types=(SourceTypeSpec(
        source_type=_ST,
        display_name="Healthchecks.io",
        description="The checks of one Healthchecks.io project, and the service each watches.",
        category="Observability",
        icon=_ICON,
        credential_fields=(CredentialField(
            "api_key", "Read-only API key", secret=True, required=True,
            help="Project Settings, API Access Keys: create a read-only key. A read-write key "
                 "works too, but the pack only reads."),),
        config_fields=(ConfigField(
            "api_base", "Instance URL", required=False, default="https://healthchecks.io",
            help="Leave as is for the hosted service. For a self-hosted instance, its https URL."),),
        egress_from_config=("api_base",),
        capabilities=(_CHECK,),
        kinds=(KindDecl(_CHECK, label="Healthchecks.io check", layer="OBSERVABILITY"),),
        connector_module=f"{_PKG}.collector",
        connector_attr="HealthchecksCollector",
        validate_hook=f"{_PKG}.validate:validate",
        options_hook=f"{_PKG}.options:build_options",
        supported_triggers=(TriggerDecl(
            kind="schedule", default=True, min_interval_seconds=900, default_interval_seconds=3600,
            delta="full", quota_calls=100, quota_window_seconds=60, est_calls_per_run=2,
            budget="Healthchecks.io asks for at most 100 API requests a minute (its API docs). A run "
                   "makes two GET calls to /api/v3/checks/, one in discover and one in fetch, "
                   "whatever the number of checks",
            cadence_rationale="Checks, their tags and the services they watch change when someone "
                              "edits the project, a few times a week; hourly keeps the graph "
                              "current at two calls an hour.",
        ),),
    ),),
    join_rules=(JoinRule(
        # A check names the service it watches in a `service:<name>` tag, or else in its slug. A
        # name match is a candidate edge, and review=True asks an admin to confirm it.
        id="service_observed_by_check",
        edge_type="observed_by",
        from_side=RuleSide("service"),
        to_side=RuleSide(_CHECK),
        match_sets=(MatchSet(keys=(MatchKey("service_name", from_attrs=("$name",),
                                            to_attrs=("service",), normalizer="strip_lower"),)),),
        review=True,
    ),),
)
