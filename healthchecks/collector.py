"""The Healthchecks.io collector: one ``ext:x-healthchecks:check`` row per check.

``discover`` lists the checks and ``fetch`` lists them again and keeps the ones it was given, so a
run costs two calls whatever the number of checks. Every natural key comes from ``ext_key`` over the
check's ``unique_key``. The ``service`` attribute is what the pack's join rule matches against a
service's name.
"""

from __future__ import annotations

from typing import Any

from collector_sdk.base import Collector, Context, ResourceRef, SourceConfig
from collector_sdk.normalize import Category, NormalizedEdge, NormalizedEntity
from collector_sdk.packs.keys import ext_key

from healthchecks import api

PACK_ID = "x-healthchecks"
KIND = "ext:x-healthchecks:check"
#: The check fields kept as attributes when the API returns them. The uuid, ping and update URLs a
#: read-write key returns are left out: they are the check's ping secret.
KEPT = ("slug", "desc", "status", "last_ping", "grace", "timeout", "schedule", "tz")


class HealthchecksCollector(Collector):
    category = Category.OBSERVABILITY
    source = PACK_ID

    def source_id(self, cfg: SourceConfig) -> str:
        return cfg.instance_id

    def discover_sync(self, ctx: Context) -> list[ResourceRef]:
        return [ResourceRef(natural_key=ext_key(PACK_ID, "check", api.unique_key(check)), kind=KIND,
                            name=api.unique_key(check))
                for check in api.list_checks(ctx.source.options, ctx.http_usage)]

    def fetch_sync(
        self, ctx: Context, refs: list[ResourceRef]
    ) -> tuple[list[NormalizedEntity], list[NormalizedEdge]]:
        checks = {api.unique_key(c): c for c in api.list_checks(ctx.source.options, ctx.http_usage)}
        entities = [self._entity(ctx, ref, checks[ref.name]) for ref in refs if ref.name in checks]
        return entities, []

    def _entity(self, ctx: Context, ref: ResourceRef, check: dict[str, Any]) -> NormalizedEntity:
        attributes: dict[str, Any] = {key: check[key] for key in KEPT if check.get(key) is not None}
        attributes["tags"] = str(check.get("tags") or "").split()
        watched = api.service(check)
        if watched:
            attributes["service"], attributes["service_from"] = watched
        name = check.get("name") or check.get("slug") or ref.name
        about = f" of the service {watched[0]}" if watched else ""
        return NormalizedEntity(
            source=self.source, category=Category.OBSERVABILITY, kind=KIND,
            natural_key=ref.natural_key, name=name, owner=ctx.source.owner,
            attributes=attributes,
            text=f"Healthchecks.io check {name}{about}, status {check.get('status', 'unknown')}",
        )
