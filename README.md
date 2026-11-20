# Healthchecks

A Tetrix data-source pack, started with `tetrix-pack new x-healthchecks`. It syncs uptime checks as
`ext:x-healthchecks:check` rows and asks Tetrix to link each check to the service it watches.

The source it calls is fictional. `api.healthchecks.example` sits under the reserved `.example` domain, and the
cassettes under `tests/cassettes/` were written by hand. Nothing here reaches a real host until you
change it.

## Edit first

1. **The API.** Set the host and endpoints in `healthchecks/api.py`, and the same host in `egress` in
   `pack.py`. The runner lets the pack reach only the hosts `egress` names.
2. **The rows.** `healthchecks/collector.py` builds one row per check. Rename the kind (`ext:x-healthchecks:check`) in
   `pack.py` and in the collector together, before the first release.
3. **The credential check.** `healthchecks/validate.py` calls `GET /v1/account`.
4. **The cassettes.** Put a real token in `TETRIX_PACK_CRED_TOKEN` and run `pytest --record`. That
   rewrites the cassettes from your source, with the token replaced by `<redacted:token>`.
5. **The form.** When you change the credential or config fields, run `UPDATE_GOLDEN=1 pytest` to
   rewrite `tests/golden/form.json`, and review the diff.

Do not change the pack id, `x-healthchecks`. It is permanent, because every kind and natural key embeds it.
Keep `contract=3` as a number. A constant such as `PACK_CONTRACT_VERSION` would recompute
differently on a newer Tetrix, which would then refuse the pack.

## Commands

```sh
python3.12 -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'      # the SDK, pytest and the pack's own dependencies
tetrix-pack check            # every problem Tetrix or the kit finds, one line each
pytest                       # replays the cassettes; pack_e2e runs on Linux only
tetrix-pack build --locked   # the OCI layout in dist/oci; prints the digest to add
TETRIX_PACK_CRED_TOKEN=replay-token tetrix-pack run sync --cassette test_pack/test_collect
```

`tetrix-pack run` and the `pack_e2e` test need Linux with Python 3.12, the runner's interpreter.
Elsewhere `pack_e2e` skips. CI (`.github/workflows/pack.yml`) runs everything on Linux.

## Dependencies

List a dependency in both `python_requires` in `pack.py` and `[project].dependencies` in
`pyproject.toml`. Then run `pip install -e '.[dev]'` and `tetrix-pack build`, and commit `pack.lock`.
The check imports your hook modules, so a dependency must be installed wherever you check or build.
The runner installs the files `pack.lock` names and nothing else. It provides the SDK, httpx and
pydantic itself, so leave those out or name them with no version.

## Publish

`tetrix-pack build --locked` prints one line on stdout: the digest of the pack's image index. That
is the digest to add. On stderr it prints the command that pushes the layout as built, with
[oras](https://oras.land). For version 0.1.0 that is:

```sh
oras cp --from-oci-layout dist/oci:0.1.0 <registry>/<repository>:0.1.0
```

Then read it back as Tetrix will, anonymously:

```sh
tetrix-pack readback <registry>/<repository>@<digest>
```

It reads the index, each manifest, the config and every payload without a login, hashes each
against `dist/oci`, and prints the reference to add in Tetrix. Do not push with
`crane push --index`: it pushes `index.json` as a wrapper index whose digest Tetrix refuses as
`not_a_pack`, and readback refuses that digest as not the layout's. The registry must let anyone read the artifact without
logging in, for as long as an install uses it. On a tag `v<version>`, CI pushes to this
repository's GitHub container registry and reads it back. If readback fails with
`registry_auth_required`, the package is not public: make it public, then re-run the job.

One commit builds to one digest when two things hold:

- **The same `SOURCE_DATE_EPOCH`.** The default is 0. Leave it unset, or set the same value
  everywhere you build.
- **No stray files.** The build ships every file under `healthchecks/`, so a `.DS_Store` or an editor
  backup changes the digest. `.gitignore` keeps them out of commits, and CI builds from a clean
  checkout.

## How Tetrix trusts this pack

- An admin adds it by digest, as a sideloaded pack, after a warning.
- Its code runs in a sandbox that reaches only its `egress` hosts, with no DNS and no secret but its own connection's.
- Its join rule's links are always candidates, never confirmed edges; `review=True` asks an admin about each.
