"""Seed the local Healthchecks instance with one project and four checks, then print its keys.

Run inside the healthchecks container: ``./manage.py shell -c "$(cat dev/seed.py)"``. It prints one JSON line,
``{"ro": <read-only key>, "rw": <read-write key>}``. The keys are made fresh by the instance on every
run and are never committed: the cassettes drop the ``X-Api-Key`` header and redact the key.

The check codes and timestamps are fixed, so a re-recording gives the same bodies. Each check covers
one way the pack derives the service it watches.
"""

import datetime as dt
import json
import uuid

from django.contrib.auth.models import User

from hc.accounts.models import Profile, Project
from hc.api.models import Check

UTC = dt.timezone.utc
user = User.objects.create(username="k20-seed", email="seed@healthchecks.test")
Profile.objects.for_user(user)
project = Project.objects.create(owner=user, name="Reference pack", badge_key="k20-seed")
keys = {"ro": project.set_api_key_readonly(), "rw": project.set_api_key()}
project.save()

CHECKS = [
    # A service: tag names the service.
    dict(code="11dd3f6e-4d55-42bd-8a9d-5a99577a4159", name="Checkout API", slug="checkout-api",
         tags="service:checkout prod", kind="simple", timeout=dt.timedelta(days=3650),
         status="up", n_pings=42, last_ping=dt.datetime(2026, 11, 1, 12, 0, tzinfo=UTC)),
    # No service: tag, so the slug names it.
    dict(code="27731bf7-19e7-47b3-a473-c9a0d71840c1", name="search", slug="search",
         tags="prod nightly", kind="cron", schedule="0 3 * * *", tz="UTC"),
    # Neither a service: tag nor a slug: no service, so the rule has nothing to match.
    dict(code="6722a90d-3abc-4cbd-aa87-7c1f864c9d7c", name="Nightly backup", slug="", tags="ops",
         status="paused"),
    # Two service: tags: the first one wins.
    dict(code="e971ad6f-9bff-4e39-b441-b48d3f00ef41", name="Payments webhook",
         slug="payments-webhook", tags="service:payments service:ledger", status="down",
         n_pings=7, last_ping=dt.datetime(2026, 1, 1, 0, 0, tzinfo=UTC)),
]
for number, fields in enumerate(CHECKS):
    # The badge key is in every check's badge_url, so it is fixed too.
    Check.objects.create(project=project, created=dt.datetime(2026, 1, 1, tzinfo=UTC),
                         badge_key=uuid.UUID(int=number + 1),
                         **{**fields, "code": uuid.UUID(fields["code"])})

print(json.dumps(keys))
