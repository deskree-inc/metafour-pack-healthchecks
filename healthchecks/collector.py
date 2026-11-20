"""The Healthchecks collector: one ``ext:x-healthchecks:check`` row per uptime check.

``discover`` lists the checks and ``fetch`` reads each one. Every natural key comes from ``ext_key``,
so it starts with ``ext:x-healthchecks:`` as Tetrix requires of a row from this pack. The ``service``
attribute is what the pack's join rule matches against a service's name.
"""

from __future__ import annotations

from collector_sdk.base import Collector, Context, ResourceRef, SourceConfig
from collector_sdk.normalize import Category, NormalizedEdge, NormalizedEntity
from collector_sdk.packs.keys import ext_key

from healthchecks import api

PACK_ID = "x-healthchecks"
KIND = "ext:x-healthchecks:check"


class HealthchecksCollector(Collector):
    category = Category.OBSERVABILITY
    source = PACK_ID

    def source_id(self, cfg: SourceConfig) -> str:
        return cfg.instance_id

    def discover_sync(self, ctx: Context) -> list[ResourceRef]:
        http = api.client(ctx.http_usage)
        response = http.get(f"{api.BASE_URL}/checks", headers=api.headers(ctx.source.options["token"]))
        response.raise_for_status()
        return [ResourceRef(natural_key=ext_key(PACK_ID, "check", check["id"]), kind=KIND,
                            name=check["id"])
                for check in response.json()["checks"]]

    def fetch_sync(
        self, ctx: Context, refs: list[ResourceRef]
    ) -> tuple[list[NormalizedEntity], list[NormalizedEdge]]:
        http = api.client(ctx.http_usage)
        token = ctx.source.options["token"]
        entities = []
        for ref in refs:
            response = http.get(f"{api.BASE_URL}/checks/{ref.name}", headers=api.headers(token))
            response.raise_for_status()
            check = response.json()
            entities.append(NormalizedEntity(
                source=self.source, category=Category.OBSERVABILITY, kind=KIND,
                natural_key=ref.natural_key, name=check["name"], owner=ctx.source.owner,
                attributes={"service": check["service"], "status": check["status"],
                            "url": check["url"]},
                text=f"Uptime check {check['name']} of the service {check['service']}",
            ))
        return entities, []
