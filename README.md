# Healthchecks.io pack for Metafour

The reference outside pack for Metafour. It was started with `metafour-pack new x-healthchecks`
(then named `tetrix-pack new`), and the first commit is that command's output, unedited. It reads
the checks of one [Healthchecks.io](https://healthchecks.io) project and asks Metafour to link each
check to the service it watches.

| | |
|---|---|
| Pack id | `x-healthchecks`, permanent: every kind and natural key embeds it |
| SDK | `metafour-pack-sdk` 1.x, which builds manifest contract 3 |
| Source | Healthchecks.io Management API v3, hosted or self-hosted |
| Kind | `ext:x-healthchecks:check`, layer `OBSERVABILITY` |
| Join rule | `service_observed_by_check`: `service` `observed_by` check, `review=True` |
| Egress | `healthchecks.io:443`, plus the host of the connection's instance URL |
| Dependencies | none beyond the SDK; the payload is `py3-none-any` |

## The source

[Healthchecks](https://github.com/healthchecks/healthchecks) monitors cron jobs and other
background tasks: each job pings its check, and the check goes down when the pings stop. It is open
source (BSD-3-Clause), runs self-hosted from the `healthchecks/healthchecks` image, and has a free
hosted tier at healthchecks.io. It is not a built-in Metafour source.

The pack calls one endpoint, `GET /api/v3/checks/`, with the project's API key in the `X-Api-Key`
header.

- **Use a read-only key.** In the project's Settings, under API Access Keys, create a read-only
  key. It lists the checks and cannot change them.
- **A read-write key also works.** It returns each check's `uuid` and ping URLs, which let anyone
  ping the check. The pack uses the uuid only to derive the check's `unique_key`, and never stores
  the uuid or the URLs.

## What it writes

One row per check, of the kind `ext:x-healthchecks:check`.

- **Natural key:** `ext:x-healthchecks:check:<unique_key>`. `unique_key` is the stable id that
  Healthchecks gives a read-only key. With a read-write key the pack derives the same value from the
  uuid, so swapping one key for the other keeps the rows.
- **Name:** the check's name, else its slug.
- **Attributes:** `service` and `service_from` (below), `tags` as a list, and `slug`, `desc`,
  `status`, `last_ping`, `grace`, and `timeout` or `schedule` and `tz`, each when the API returns it.

### The service a check watches

The pack takes the service from the check's tags first, then from its slug:

1. **A `service:<name>` tag.** The first such tag wins, so `service:payments service:ledger` gives
   `payments`. `service_from` is `tag`.
2. **Otherwise, the slug.** A check with the slug `search` and no `service:` tag gives `search`.
   `service_from` is `slug`.
3. **Neither.** The row has no `service`, and the rule has nothing to match.

Tag your checks `service:<name>` with the name of the service in Metafour when the slug is not that
name.

### The join rule

`service_observed_by_check` matches a `service` row's `$name` to a check's `service` attribute,
after `strip_lower`, as an `observed_by` edge from the service to the check. A pack's rule edges are
always candidates, never confirmed edges. `review=True` puts each one to an admin as a
`declared_rule_candidate` question.

## Adding it in Metafour

An admin adds the pack by the digest a release prints (see Publishing). Then they create a
connection with:

- **Read-only API key**, required.
- **Instance URL**, optional, `https://healthchecks.io` by default. For a self-hosted instance, give
  its root URL: `https://<host>` or `https://<host>:<port>`, with nothing after the host but an
  optional `/`. The pack refuses any other scheme, a user name or password, a path, a query and a
  fragment, so the key goes only to the host the URL names.

### Egress

The pack reaches `healthchecks.io` on port 443, which `egress` declares. `egress_from_config`
declares the Instance URL's host and port too, so a self-hosted instance is reachable as well, and
nothing else is.

A self-hosted instance must be reachable from Metafour at a public address, over HTTPS, with a
certificate from a public certificate authority. The pack runs in a sandbox that has no DNS of its
own and reaches the internet only through Metafour's egress proxy. The proxy resolves the host and, by default,
refuses private and loopback addresses. The sandbox trusts only public certificate authorities.

### Schedule and budget

The pack syncs on a schedule, hourly by default, every 15 minutes at most. A run makes two
calls, one in discover and one in fetch, whatever the number of checks. Healthchecks.io asks for
at most 100 API requests a minute, and the pack paces itself at one request a second.

## Development

You need Python 3.12. `metafour-pack run` and the `pack_e2e` test also need Linux, as the runner
does; elsewhere `pack_e2e` skips. CI runs everything on Linux.

```sh
python3.12 -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'      # the SDK, pytest and the pack's own dependencies (none)
metafour-pack check            # every problem Metafour or the kit finds, one line each
pytest                       # replays the cassettes; pack_e2e runs on Linux only
metafour-pack build --locked   # the OCI layout in dist/oci; prints the digest to add
METAFOUR_PACK_CRED_API_KEY=replay-key \
  metafour-pack run sync --config tests/config.json --cassette test_pack/test_collect
```

When you change a credential or config field, run `UPDATE_GOLDEN=1 pytest` on Linux to rewrite
`tests/golden/form.json`, and review the diff.

### The cassettes and the local instance

The cassettes under `tests/cassettes/` were recorded against a self-hosted Healthchecks instance,
never against a Healthchecks.io account. `dev/compose.yaml` runs the `healthchecks/healthchecks`
image behind Caddy, which serves it over TLS as `https://healthchecks.test` from its own internal
certificate authority. `tests/config.json` names that URL. `dev/seed.py` creates one project, fresh
API keys and four checks with fixed codes and timestamps. The four checks cover each way the pack
derives a service.

```sh
dev/record.sh record   # re-record tests/cassettes/
dev/record.sh live     # record into a scratch copy; fail if the instance answers differently
```

Both need Docker. The script passes the instance's read-only key to `pytest --record` in
`METAFOUR_PACK_CRED_API_KEY`. The cassette harness drops the `X-Api-Key` header, and it refuses to
write a cassette that still holds the key. The keys exist only while the script runs.

## CI

`.github/workflows/pack.yml` installs only `metafour-pack-sdk[dev]` from PyPI, at the major
`pyproject.toml` pins, and runs these jobs on Linux with Python 3.12:

| Job | Runs |
|---|---|
| `metafour-pack check` | the kit's checks, including the add-time verdict Metafour applies |
| `pytest` | the tests with the cassettes replayed, and `pack_e2e`, which must not skip |
| `build` | `metafour-pack build --locked` for `linux/amd64` and `linux/arm64`, twice, to one digest |
| `run-sync` | `metafour-pack run sync --cassette` through the local runner: no refused row, no egress refusal |
| `live` | manual only (`workflow_dispatch` with `live`): `dev/record.sh live` |
| `publish` | on a tag `v<version>`: `oras cp --from-oci-layout`, then `metafour-pack readback` |

Every action is pinned by commit. Dependabot proposes updates to the actions, the SDK and the
images in `dev/compose.yaml` weekly.

## Publishing

1. Raise `version` in `pack.py`. The pack id and the `contract=3` literal never change.
2. Merge, then tag the commit `v<version>`.
3. The `publish` job checks that the tag equals the version. It builds with `--locked`, pushes the
   layout with `oras cp --from-oci-layout` to `$PACK_REPOSITORY:<version>`, and reads it back with
   `metafour-pack readback`, which prints the reference to add. The job summary shows it.

Settings the publish job reads:

| Name | Kind | What |
|---|---|---|
| `PACK_REPOSITORY` | repository variable | the repository to push to, without a tag, such as `ghcr.io/<org>/metafour-pack-healthchecks` |
| `PACK_REGISTRY_USERNAME`, `PACK_REGISTRY_PASSWORD` | secrets, optional | a login for a registry other than `ghcr.io`; without them the job logs in to `ghcr.io` with `GITHUB_TOKEN` |

The repository must let anyone pull the artifact without logging in, for as long as an install
uses it. If `readback` fails with `registry_auth_required`, the package is not public: make it
public, then re-run the job.

Add the digest `build` printed. Do not push with `crane push --index`: it pushes `index.json` as a
wrapper index, whose digest Metafour refuses as `not_a_pack`.

One commit builds to one digest when the build uses the same `SOURCE_DATE_EPOCH` (default 0) and
no stray file sits under `healthchecks/`. CI builds from a clean checkout. The compressed bytes
come from the build environment's zlib, so the digest the tag's CI prints is the one to add.

## Update policy

The maintainers of this repository rebuild and release the pack. A release is a new version in
`pack.py` and a tag.

- **The runner's interpreter moves.** No rebuild is needed. The pack is pure Python with no
  dependencies, so its payload is `py3-none-any`: it holds no wheels and runs on every interpreter
  the runner carries. If the pack ever gains a dependency with binary wheels, the maintainers must
  rebuild and release it before the runner drops the old interpreter. The runner's diagnostics name
  the packs this affects.
- **A new SDK minor.** No rebuild is needed. Within a major, the runner keeps every name the pack
  imports. Build with the oldest SDK minor you want to support.
- **A new SDK major.** The maintainers rebuild against it when it ships, following its ADR.
- **The Healthchecks API changes.** The manual `live` job compares a fresh recording with the
  cassettes. Re-record with `dev/record.sh record`, fix the pack, and release.
- **Dependencies.** Dependabot opens a pull request each week, and the maintainers merge it when
  CI passes.

## How Metafour trusts this pack

- An admin adds it by digest, as a sideloaded pack, after a warning.
- Its code runs in a sandbox that reaches only its egress hosts, with no DNS and no secret but its
  own connection's.
- Its join rule's links are always candidates, never confirmed edges; `review=True` asks an admin
  about each.
