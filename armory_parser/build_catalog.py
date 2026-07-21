from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


CATALOG_SCHEMA_VERSION = 1
EXPECTED_CATALOG_SIZE = 299
UNNUMBERED_COMPLETION_NAMES = {
    "Blue Slime",
    "Cave Bat",
    "Demon Eye",
    "Enchanted Sword",
    "Eye of Cthulhu",
    "Green Slime",
    "Illuminant Bat",
    "Illuminant Slime",
    "Purple Slime",
    "Rainbow Slime",
    "Red Slime",
}


class CatalogBuildError(RuntimeError):
    """Raised when upstream game data cannot produce the expected catalog."""


def build_catalog(
    source_path: Path,
    source_commit: str,
    expected_sha256: str,
) -> dict[str, Any]:
    source_bytes = source_path.read_bytes()
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    if source_sha256 != expected_sha256:
        raise CatalogBuildError("Upstream character catalog checksum changed")

    source = json.loads(source_bytes)
    raw_pals = source.get("pals")
    if not isinstance(raw_pals, list):
        raise CatalogBuildError("Upstream character catalog is malformed")

    numbered_rows = [
        pal
        for pal in raw_pals
        if _paldeck_index(pal) > 0
        and "(Summon)" not in str(pal.get("name", ""))
    ]

    rows_by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    names_by_index: dict[int, set[str]] = defaultdict(set)
    for pal in numbered_rows:
        name = _clean_name(pal)
        rows_by_name[name].append(pal)
        names_by_index[_paldeck_index(pal)].add(name)

    canonical_entries: dict[str, dict[str, Any]] = {}
    aliases: dict[str, str] = {}

    for name, rows in rows_by_name.items():
        index = _paldeck_index(rows[0])
        if any(_paldeck_index(row) != index for row in rows):
            raise CatalogBuildError("One Pal name maps to multiple indexes")

        is_variant = (
            len(names_by_index[index]) > 1
            and all("_" in str(row.get("asset", "")) for row in rows)
        )
        paldeck_number = f"{index}{'B' if is_variant else ''}"
        catalog_key = f"paldeck:{paldeck_number}"
        canonical_entries[catalog_key] = {
            "name": name,
            "paldeck_number": paldeck_number,
            "counts_toward_completion": True,
        }
        _add_aliases(aliases, rows, catalog_key)

    for name in sorted(UNNUMBERED_COMPLETION_NAMES):
        rows = [pal for pal in raw_pals if _clean_name(pal) == name]
        if not rows:
            raise CatalogBuildError(f"Missing unnumbered catalog entry: {name}")

        catalog_key = f"extra:{_slug(name)}"
        canonical_entries[catalog_key] = {
            "name": name,
            "paldeck_number": None,
            "counts_toward_completion": True,
        }
        _add_aliases(aliases, rows, catalog_key)

    if len(canonical_entries) != EXPECTED_CATALOG_SIZE:
        raise CatalogBuildError(
            f"Expected {EXPECTED_CATALOG_SIZE} entries, got {len(canonical_entries)}"
        )

    return {
        "schema_version": CATALOG_SCHEMA_VERSION,
        "source_commit": source_commit,
        "source_sha256": source_sha256,
        "completion_total": len(canonical_entries),
        "entries": dict(sorted(canonical_entries.items())),
        "aliases": dict(sorted(aliases.items())),
    }


def _add_aliases(
    aliases: dict[str, str],
    rows: list[dict[str, Any]],
    catalog_key: str,
) -> None:
    for row in rows:
        asset = str(row.get("asset", "")).strip()
        if not asset:
            raise CatalogBuildError("Catalog entry has no internal asset key")
        normalized_asset = asset.casefold()
        existing = aliases.get(normalized_asset)
        if existing is not None and existing != catalog_key:
            raise CatalogBuildError("Internal asset alias maps to multiple entries")
        aliases[normalized_asset] = catalog_key


def _clean_name(pal: dict[str, Any]) -> str:
    name = str(pal.get("name", "")).strip()
    if not name:
        raise CatalogBuildError("Catalog entry has no display name")
    return name


def _paldeck_index(pal: dict[str, Any]) -> int:
    raw_index = pal.get("stats", {}).get("zukan_index", -1)
    return raw_index if isinstance(raw_index, int) else -1


def _slug(name: str) -> str:
    return "-".join(name.casefold().split())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    catalog = build_catalog(
        source_path=args.source,
        source_commit=args.source_commit,
        expected_sha256=args.expected_sha256,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(catalog, separators=(",", ":"), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
