from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from armory_parser.build_catalog import CatalogBuildError, build_catalog


class CatalogBuilderTests(unittest.TestCase):
    def test_builds_numbered_variant_and_unnumbered_entries(self) -> None:
        source_path, source_sha256 = self._write_source(
            [
                self._pal("Lamball", "SheepBall", 1),
                self._pal("Foxparks", "Kitsunebi", 5),
                self._pal("Foxparks Cryst", "Kitsunebi_Ice", 5),
                self._pal("Green Slime", "YakushimaMonster001", -1),
            ]
        )

        with (
            patch("armory_parser.build_catalog.EXPECTED_CATALOG_SIZE", 4),
            patch(
                "armory_parser.build_catalog.UNNUMBERED_COMPLETION_NAMES",
                {"Green Slime"},
            ),
        ):
            catalog = build_catalog(source_path, "test-commit", source_sha256)

        self.assertEqual(catalog["completion_total"], 4)
        self.assertEqual(catalog["entries"]["paldeck:5B"]["name"], "Foxparks Cryst")
        self.assertEqual(
            catalog["aliases"]["yakushimamonster001"],
            "extra:green-slime",
        )

    def test_rejects_a_source_checksum_change(self) -> None:
        source_path, _ = self._write_source([])

        with self.assertRaisesRegex(CatalogBuildError, "checksum changed"):
            build_catalog(source_path, "test-commit", "0" * 64)

    def _write_source(self, pals: list[dict[str, object]]) -> tuple[Path, str]:
        contents = json.dumps({"pals": pals}).encode()
        temporary = tempfile.NamedTemporaryFile(delete=False)
        temporary.write(contents)
        temporary.close()
        path = Path(temporary.name)
        self.addCleanup(path.unlink, missing_ok=True)
        return path, hashlib.sha256(contents).hexdigest()

    @staticmethod
    def _pal(name: str, asset: str, zukan_index: int) -> dict[str, object]:
        return {
            "name": name,
            "asset": asset,
            "stats": {"zukan_index": zukan_index},
        }


if __name__ == "__main__":
    unittest.main()
