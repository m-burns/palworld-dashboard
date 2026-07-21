# Paldeck snapshot import

The Armory parser is an isolated, read-only proof of concept. It reads player
saves from a completed Palworld backup and writes a sanitized JSON document to
standard output. It does not read live saves, write to a save archive, connect
to the dashboard database, or publish a web endpoint.

## Privacy boundary

The output is limited to:

- An HMAC-derived internal player key
- Captured and encountered species totals
- Total captures
- Pal species keys, capture counts, and discovery flags
- Canonical names, Paldeck numbers, and completion eligibility
- Snapshot timestamp and SHA-256 digest

It does not emit player GUIDs, save filenames, Steam or platform IDs, account
names, IP addresses, locations, inventories, guild data, or raw save content.
The same private secret must be used for every import so a player receives a
stable internal key. Never commit or print that secret.

## Build the isolated worker

The parser is deliberately separate from the FastAPI image. It uses the
GPL-3.0-or-later `palsav-flex` parser from PalworldSaveTools, pinned to a
reviewed commit in `requirements-armory-parser.txt`.

During the image build, a checksum-pinned game-data file from that same commit
is reduced to a minimal offline catalog. The completion set contains 299
entries: 288 numbered Paldeck entries and 11 unnumbered crossover creatures,
matching the public list at <https://palworld.gg/pals>. Technical aliases are
matched case-insensitively and merged. Humans, summon forms, bosses, and other
unlisted internal creatures do not count toward completion. Unknown future
species remain visible as unmapped entries and also do not affect completion
until the reviewed catalog is updated.

```bash
docker build \
  --file Dockerfile.armory-parser \
  --tag palworld-armory-parser .
```

## Run against a completed backup

Create a persistent secret once and protect it with mode `600`:

```bash
openssl rand -hex 32 > /opt/palworld-dashboard/.armory-id-secret
chmod 600 /opt/palworld-dashboard/.armory-id-secret
```

Run the worker without network access, with a read-only root filesystem and a
read-only snapshot mount:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --network none \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --volume /opt/palworld/palworld/backups:/snapshots:ro \
  --volume /opt/palworld-dashboard/.armory-id-secret:/run/secrets/armory-id:ro \
  --env ARMORY_ID_SECRET_FILE=/run/secrets/armory-id \
  palworld-armory-parser \
  /snapshots/palworld-save-YYYY-MM-DD_HH-MM-SS.tar.gz
```

The caller is responsible for capturing standard output into a mode-`600`
temporary file before a later database import. Parser diagnostics are written
to standard error. A failed run must not replace the last successful snapshot.

## Current scope

Database ingestion, scheduling, retention, opt-out controls, and public Armory
routes are intentionally outside this first step.
