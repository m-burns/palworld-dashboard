from __future__ import annotations

import hashlib
import hmac
import re
import tarfile
import tempfile
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, BinaryIO


SCHEMA_VERSION = 3
MAX_PLAYER_SAVE_BYTES = 10 * 1024 * 1024
MAX_LEVEL_SAVE_BYTES = 32 * 1024 * 1024
MAX_DISPLAY_NAME_LENGTH = 64
PLAYER_SAVE_PATTERN = re.compile(
    r"(?:^|/)Players/(?P<player_guid>[A-Fa-f0-9]{32})\.sav$"
)
SPECIES_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")
LEVEL_SAVE_PATTERN = re.compile(r"(?:^|/)Level\.sav$")


class SnapshotError(RuntimeError):
    """Raised when a snapshot cannot be safely parsed."""


@dataclass(frozen=True)
class LoadedPlayer:
    record_data: Mapping[str, Any]
    player_uid: str | None = None


RecordLoader = Callable[[Path], Mapping[str, Any] | LoadedPlayer]
WorldPlayerLoader = Callable[[Path], Mapping[str, str]]
Catalog = Mapping[str, Any]


def extract_snapshot(
    archive_path: Path,
    identity_secret: bytes,
    record_loader: RecordLoader | None = None,
    world_player_loader: WorldPlayerLoader | None = None,
    catalog: Catalog | None = None,
) -> dict[str, Any]:
    """Return an allowlisted Paldeck view of player saves in an archive."""
    _validate_secret(identity_secret)

    archive_path = archive_path.resolve(strict=True)
    if not archive_path.is_file():
        raise SnapshotError("Snapshot path is not a regular file")

    loader = record_loader or _load_player_data
    world_loader = world_player_loader or _load_world_players
    resolved_catalog = catalog or load_catalog(
        Path("/app/catalog/pals.json")
    )
    _validate_catalog(resolved_catalog)
    players: list[dict[str, Any]] = []
    seen_guids: set[str] = set()

    try:
        with tarfile.open(archive_path, mode="r:gz") as archive:
            world_players = _extract_world_players(archive, world_loader)
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
                        world_players=world_players,
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
    world_players: Mapping[str, str],
    catalog: Catalog,
) -> dict[str, Any]:
    with tempfile.NamedTemporaryFile(
        prefix="paldeck-player-",
        suffix=".sav",
    ) as temporary_save:
        _copy_limited(
            source,
            temporary_save,
            MAX_PLAYER_SAVE_BYTES,
            "Player save",
        )
        temporary_save.flush()
        loaded_player = record_loader(Path(temporary_save.name))

    if isinstance(loaded_player, LoadedPlayer):
        record_data = loaded_player.record_data
        player_uid = loaded_player.player_uid
    else:
        record_data = loaded_player
        player_uid = None

    display_name = (
        _sanitize_display_name(world_players.get(player_uid))
        if player_uid is not None
        else None
    )

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
        "display_name": display_name,
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


def _load_player_data(save_path: Path) -> LoadedPlayer:
    try:
        from palsav.io import load_sav

        gvas_file = load_sav(save_path)
        save_data = gvas_file.properties["SaveData"]["value"]
        player_uid = save_data["PlayerUId"]["value"]
        return LoadedPlayer(
            record_data=save_data["RecordData"]["value"],
            player_uid=_normalize_player_uid(player_uid),
        )
    except Exception as exc:
        raise SnapshotError("Player save could not be parsed") from exc


def _extract_world_players(
    archive: tarfile.TarFile,
    loader: WorldPlayerLoader,
) -> Mapping[str, str]:
    members = [
        member
        for member in archive.getmembers()
        if LEVEL_SAVE_PATTERN.search(member.name)
    ]
    if not members:
        return {}
    if len(members) != 1:
        raise SnapshotError("Snapshot contains multiple world saves")

    member = members[0]
    if not member.isfile():
        raise SnapshotError("World save archive member is not a file")
    if member.size > MAX_LEVEL_SAVE_BYTES:
        raise SnapshotError("World save exceeds the configured size limit")
    source = archive.extractfile(member)
    if source is None:
        raise SnapshotError("World save could not be read")

    with tempfile.NamedTemporaryFile(
        prefix="paldeck-world-",
        suffix=".sav",
    ) as temporary_save:
        _copy_limited(
            source,
            temporary_save,
            MAX_LEVEL_SAVE_BYTES,
            "World save",
        )
        temporary_save.flush()
        return loader(Path(temporary_save.name))


def _load_world_players(save_path: Path) -> Mapping[str, str]:
    try:
        from palsav.io import load_sav

        world = load_sav(save_path).properties["worldSaveData"]["value"]
        entries = world["CharacterSaveParameterMap"]["value"]
        players: dict[str, str] = {}
        for entry in entries:
            parameters = entry["value"]["RawData"]["value"]["object"][
                "SaveParameter"
            ]["value"]
            if parameters.get("IsPlayer", {}).get("value") is not True:
                continue

            player_uid = _normalize_player_uid(
                entry["key"]["PlayerUId"]["value"]
            )
            display_name = _sanitize_display_name(
                parameters.get("NickName", {}).get("value")
            )
            if display_name is None:
                continue
            if player_uid in players:
                raise SnapshotError("World save contains a duplicate player UID")
            players[player_uid] = display_name
        return players
    except SnapshotError:
        raise
    except Exception as exc:
        raise SnapshotError("World save could not be parsed") from exc


def _normalize_player_uid(value: Any) -> str:
    normalized = str(value).strip().casefold()
    if not normalized:
        raise SnapshotError("Player UID is empty")
    return normalized


def _sanitize_display_name(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    name = unicodedata.normalize("NFKC", value).strip()
    if not name or len(name) > MAX_DISPLAY_NAME_LENGTH:
        return None
    if any(unicodedata.category(character).startswith("C") for character in name):
        return None
    return name


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


def _copy_limited(
    source: BinaryIO,
    destination: BinaryIO,
    limit: int,
    label: str,
) -> None:
    copied = 0
    while chunk := source.read(64 * 1024):
        copied += len(chunk)
        if copied > limit:
            raise SnapshotError(f"{label} exceeds the configured size limit")
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
