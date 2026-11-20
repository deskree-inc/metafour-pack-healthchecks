#!/usr/bin/env bash
# Run the pack's tests against a local, self-hosted Healthchecks instance over TLS, never a real
# account.
#
#   dev/record.sh record   re-record the cassettes under tests/cassettes/
#   dev/record.sh live     record into a scratch copy and fail if the bodies differ from the
#                          committed cassettes (the manual CI job runs this)
#
# It starts dev/compose.yaml, seeds it with dev/seed.py (fresh keys every run), copies Caddy's root
# certificate out, and runs pytest --record in a python:3.12 container on the compose network, where
# https://healthchecks.test is the instance. The read-only key reaches pytest only as
# TETRIX_PACK_CRED_API_KEY. The cassette harness drops X-Api-Key and refuses to write a key value.
#
# The SDK comes from the index, as in CI: tetrix-pack-sdk[dev] from pyproject.toml. To install it
# from local wheels instead, set PACK_SDK_WHEELS to a directory that holds them.
set -euo pipefail

mode="${1:-record}"
case "$mode" in record|live) ;; *) echo "usage: dev/record.sh record|live" >&2; exit 2 ;; esac
root="$(cd "$(dirname "$0")/.." && pwd)"
compose=(docker compose -f "$root/dev/compose.yaml")
work="$(mktemp -d)"
HC_SECRET_KEY="$(openssl rand -hex 32)"
export HC_SECRET_KEY
# The runner's interpreter, pinned.
python_image="python:3.12@sha256:5411fa1b302c43f510324381162b5f5d0d93b9ee2af538f09d944f0d290ee3cb"

cleanup() { "${compose[@]}" down -v --remove-orphans >/dev/null 2>&1 || true; rm -rf "$work"; }
trap cleanup EXIT

"${compose[@]}" up -d --wait --quiet-pull
"${compose[@]}" exec -T healthchecks ./manage.py shell -c "$(cat "$root/dev/seed.py")" \
  | tail -n 1 > "$work/keys.json"   # Django's shell prints a banner line first
ro_key="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["ro"])' "$work/keys.json")"
for _ in $(seq 1 30); do
  "${compose[@]}" cp tls:/data/caddy/pki/authorities/local/root.crt "$work/root.crt" >/dev/null 2>&1 && break
  sleep 1
done
test -s "$work/root.crt" || { echo "dev/record.sh: no CA certificate from Caddy" >&2; exit 1; }

if [ "$mode" = live ]; then
  mkdir "$work/pack"
  git -C "$root" archive HEAD | tar -x -C "$work/pack"
  target="$work/pack"
else
  target="$root"
fi

wheels=()
if [ -n "${PACK_SDK_WHEELS:-}" ]; then
  wheels=(-v "$PACK_SDK_WHEELS:/wheels:ro" -e PIP_FIND_LINKS=/wheels)
fi
docker run --rm --network pack-healthchecks-dev_default \
  -v "$target:/pack" -v "$work/root.crt:/certs/root.crt:ro" "${wheels[@]}" \
  -e SSL_CERT_FILE=/certs/root.crt -e TETRIX_PACK_CRED_API_KEY="$ro_key" -w /pack \
  "$python_image" \
  bash -c "pip install --quiet --disable-pip-version-check --root-user-action=ignore -e '.[dev]' &&
           python -m pytest -p no:cacheprovider --record -k 'not end_to_end' -q"

if [ "$mode" = live ]; then
  python3 "$root/dev/compare_cassettes.py" "$root/tests/cassettes" "$work/pack/tests/cassettes"
fi
