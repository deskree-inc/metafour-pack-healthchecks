"""The Healthchecks pack's manifest. Tetrix reads the data the build makes from it, never this file.

The template source is fictional: api.healthchecks.example stands in for your source's API, so replace the host,
the endpoints in healthchecks/api.py and the kind before you publish. The pack id is permanent: every
kind and natural key embeds it.
"""

from __future__ import annotations

import base64
from pathlib import Path

from collector_sdk.packs import (
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
    version="0.1.0",
    contract=3,                         # a literal, never PACK_CONTRACT_VERSION
    display_name="Healthchecks",
    description="Uptime checks from Healthchecks.",
    packages=(_PKG,),
    python_requires=(),                     # the template needs only the SDK's own httpx
    egress=(EgressHost("api.healthchecks.example"),),
    source_types=(SourceTypeSpec(
        source_type=_ST,
        display_name="Healthchecks",
        description="The uptime checks of one Healthchecks account, and the service each watches.",
        category="Observability",
        icon=_ICON,
        credential_fields=(CredentialField("token", "API token", secret=True, required=True,
                                           help="A read-only token for the account."),),
        capabilities=(_CHECK,),
        kinds=(KindDecl(_CHECK, label="Uptime check", layer="OBSERVABILITY"),),
        connector_module=f"{_PKG}.collector",
        connector_attr="HealthchecksCollector",
        validate_hook=f"{_PKG}.validate:validate",
        options_hook=f"{_PKG}.options:build_options",
        supported_triggers=(TriggerDecl(
            kind="schedule", default=True, min_interval_seconds=900, default_interval_seconds=3600,
            delta="full",
            budget="The template API's quota is not published: a run makes one list call and one "
                   "call per check",
            cadence_rationale="Checks and the services they watch change when someone edits the "
                              "account, a few times a week; hourly keeps the graph current at a "
                              "few dozen calls an hour for a typical account.",
        ),),
    ),),
    join_rules=(JoinRule(
        # A check names the service it watches. A name match is a candidate edge, and review=True
        # asks an admin to confirm it.
        id="service_observed_by_check",
        edge_type="observed_by",
        from_side=RuleSide("service"),
        to_side=RuleSide(_CHECK),
        match_sets=(MatchSet(keys=(MatchKey("service_name", from_attrs=("$name",),
                                            to_attrs=("service",), normalizer="strip_lower"),)),),
        review=True,
    ),),
)
