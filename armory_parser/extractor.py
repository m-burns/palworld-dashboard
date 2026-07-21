from __future__ import annotations

import hashlib
import hmac
import re
import tarfile
import tempfile
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, BinaryIO


SCHEMA_VERSION = 2
MAX_PLAYER_SAVE_BYTES = 10 * 1024 * 1024
PLAYER_SAVE_PATTERN = re.compile(
    r"(?:^|/)Players/(?P<player_guid>[A-Fa-f0-9]{32})\.sav$"
)
SPECIES_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")


class SnapshotError(RuntimeError):
    """Raised when a snapshot cannot be safely parsed."""


RecordLoader = Callable[[Path], Mapping[str, Any]]
Catalog = Mapping[str, Any]


def extract_snapshot(
    archive_path: Path,
    identity_secret: bytes,
    record_loader: RecordLoader | None = None,
    catalog: Catalog | None = None,
) -> dict[str, Any]:
    """Return an allowlisted Paldeck view of player saves in an archive."""
    _validate_secret(identity_secret)

    archive_path = archive_path.resolve(strict=True)
    if not archive_path.is_file():
        raise SnapshotError("Snapshot path is not a regular file")

    loader = record_loader or _load_record_data
    resolved_catalog = catalog or load_catalog(
        Path("/app/catalog/pals.json")
    )
    _validate_catalog(resolved_catalog)
    players: list[dict[str, Any]] = []
    seen_guids: set[str] = set()

    try:
        with tarfile.open(archive_path, mode="r:gz") as archive:
            for member in archive.getmembers():
                match = PLAYER_SAVE_PATTERN.search(member.name)
                if match is None:
                    continue
                if not member.isfile():
                    raise SnapshotError("Player save archive member is not a file")
                if member.size > MAX_PLAYER_SAVE_BYTES:
                    raise SnapshotError("Player save exceeds the configured size limit")

                player_guid = match.group("player_guid").lower()
                if player_guid in seen_guids:
                    raise SnapshotError("Snapshot contains a duplicate player save")
                seen_guids.add(player_guid)

                source = archive.extractfile(member)
                if source is None:
                    raise SnapshotError("Player save could not be read")

                players.append(
                    _extract_player(
                        source=source,
                        player_guid=player_guid,
                        identity_secret=identity_secret,
                        record_loader=loader,
                        catalog=resolved_catalog,
                    )
                )
    except (tarfile.TarError, OSError) as exc:
        raise SnapshotError("Snapshot archive could not be read") from exc

    if not players:
        raise SnapshotError("Snapshot contains no player saves")

    players.sort(key=lambda player: player["internal_player_key"])

    return {
        "schema_version": SCHEMA_VERSION,
        "snapshot_sha256": _sha256_file(archive_path),
        "snapshot_created_at": datetime.fromtimestamp(
            archive_path.stat().st_mtime,
            tz=UTC,
        ).isoformat(),
        "catalog_source_commit": resolved_catalog["source_commit"],
        "completion_total": resolved_catalog["completion_total"],
        "players": players,
    }


def _extract_player(
    source: BinaryIO,
    player_guid: str,
    identity_secret: bytes,
    record_loader: RecordLoader,
    catalog: Catalog,
) -> dict[str, Any]:
    with tempfile.NamedTemporaryFile(
        prefix="paldeck-player-",
        suffix=".sav",
    ) as temporary_save:
        _copy_limited(source, temporary_save, MAX_PLAYER_SAVE_BYTES)
        temporary_save.flush()
        record_data = record_loader(Path(temporary_save.name))

    captures = _read_entry_map(record_data, "PalCaptureCount", value_type=int)
    unlocks = _read_entry_map(record_data, "PaldeckUnlockFlag", value_type=bool)
    species = _map_species(
        captures=captures,
        unlocks=unlocks,
        catalog=catalog,
    )
    completion_total = int(catalog["completion_total"])
    completed_entries = sum(
        entry["counts_toward_completion"]
        and entry["capture_count"] > 0
        for entry in species
    )

    return {
        "internal_player_key": hmac.new(
            identity_secret,
            player_guid.encode("ascii"),
            hashlib.sha256,
        ).hexdigest(),
        "completed_entries": completed_entries,
        "completion_total": completion_total,
        "completion_percent": round(
            completed_entries / completion_total * 100,
            2,
        ),
        "encountered_entries": sum(entry["discovered"] for entry in species),
        "total_captures": sum(entry["capture_count"] for entry in species),
        "unmapped_species_count": sum(
            entry["catalog_status"] == "unmapped" for entry in species
        ),
        "species": species,
    }


def load_catalog(path: Path) -> dict[str, Any]:
    import json

    try:
        catalog = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SnapshotError("Paldeck catalog could not be loaded") from exc
    if not isinstance(catalog, dict):
        raise SnapshotError("Paldeck catalog has an unexpected structure")
    return catalog


def _map_species(
    captures: Mapping[str, int],
    unlocks: Mapping[str, bool],
    catalog: Catalog,
) -> list[dict[str, Any]]:
    entries = catalog["entries"]
    aliases = catalog["aliases"]
    mapped: dict[str, dict[str, Any]] = {}

    for species_key in sorted(set(captures) | set(unlocks)):
        if species_key.casefold() == "human":
            continue

        catalog_key = aliases.get(species_key.casefold())
        if catalog_key is None:
            catalog_key = f"unmapped:{species_key}"
            catalog_entry = {
                "name": species_key,
                "paldeck_number": None,
                "counts_toward_completion": False,
            }
            catalog_status = "unmapped"
        else:
            catalog_entry = entries[catalog_key]
            catalog_status = "mapped"

        capture_count = captures.get(species_key, 0)
        discovered = bool(
            unlocks.get(species_key, False) or capture_count > 0
        )
        existing = mapped.get(catalog_key)
        if existing is None:
            mapped[catalog_key] = {
                "catalog_key": catalog_key,
                "name": catalog_entry["name"],
                "paldeck_number": catalog_entry["paldeck_number"],
                "capture_count": capture_count,
                "discovered": discovered,
                "counts_toward_completion": catalog_entry[
                    "counts_toward_completion"
                ],
                "catalog_status": catalog_status,
            }
        else:
            existing["capture_count"] += capture_count
            existing["discovered"] = existing["discovered"] or discovered

    return sorted(
        mapped.values(),
        key=lambda entry: (
            entry["paldeck_number"] is None,
            _paldeck_sort_key(entry["paldeck_number"]),
            entry["name"].casefold(),
        ),
    )


def _paldeck_sort_key(number: str | None) -> tuple[int, str]:
    if number is None:
        return (9999, "")
    suffix = "B" if number.endswith("B") else ""
    raw_index = number[:-1] if suffix else number
    return (int(raw_index), suffix)


def _validate_catalog(catalog: Catalog) -> None:
    if catalog.get("schema_version") != 1:
        raise SnapshotError("Unsupported Paldeck catalog version")
    completion_total = catalog.get("completion_total")
    entries = catalog.get("entries")
    aliases = catalog.get("aliases")
    if (
        not isinstance(completion_total, int)
        or completion_total <= 0
        or not isinstance(entries, Mapping)
        or len(entries) != completion_total
        or not isinstance(aliases, Mapping)
        or not isinstance(catalog.get("source_commit"), str)
    ):
        raise SnapshotError("Paldeck catalog has an unexpected structure")


def _load_record_data(save_path: Path) -> Mapping[str, Any]:
    try:
        from palsav.io import load_sav

        gvas_file = load_sav(save_path)
        return gvas_file.properties["SaveData"]["value"]["RecordData"]["value"]
    except Exception as exc:
        raise SnapshotError("Player save could not be parsed") from exc


def _read_entry_map(
    record_data: Mapping[str, Any],
    field_name: str,
    value_type: type[int] | type[bool],
) -> dict[str, int] | dict[str, bool]:
    raw_field = record_data.get(field_name, {})
    if not isinstance(raw_field, Mapping):
        raise SnapshotError("Paldeck field has an unexpected structure")

    raw_entries = raw_field.get("value", [])
    if not isinstance(raw_entries, list):
        raise SnapshotError("Paldeck entries have an unexpected structure")

    entries: dict[str, int] | dict[str, bool] = {}
    for raw_entry in raw_entries:
        if not isinstance(raw_entry, Mapping):
            raise SnapshotError("Paldeck entry has an unexpected structure")

        species_key = raw_entry.get("key")
        raw_value = raw_entry.get("value")
        if (
            not isinstance(species_key, str)
            or SPECIES_KEY_PATTERN.fullmatch(species_key) is None
        ):
            raise SnapshotError("Paldeck entry has an invalid species key")
        if species_key in entries:
            raise SnapshotError("Paldeck field contains a duplicate species")

        if value_type is bool:
            if not isinstance(raw_value, bool):
                raise SnapshotError("Paldeck unlock value is not boolean")
            entries[species_key] = raw_value
            continue

        if isinstance(raw_value, bool) or not isinstance(raw_value, int):
            raise SnapshotError("Paldeck capture count is not an integer")
        if raw_value < 0:
            raise SnapshotError("Paldeck capture count is negative")
        entries[species_key] = raw_value

    return entries


def _copy_limited(source: BinaryIO, destination: BinaryIO, limit: int) -> None:
    copied = 0
    while chunk := source.read(64 * 1024):
        copied += len(chunk)
        if copied > limit:
            raise SnapshotError("Player save exceeds the configured size limit")
        destination.write(chunk)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_secret(identity_secret: bytes) -> None:
    if len(identity_secret) < 32:
        raise SnapshotError("Identity secret must contain at least 32 bytes")
