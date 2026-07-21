from __future__ import annotations

import io
import tarfile
import tempfile
import unittest
from pathlib import Path

from armory_parser.extractor import SnapshotError, extract_snapshot


PLAYER_GUID = "0123456789ABCDEF0123456789ABCDEF"
SECRET = b"a-private-test-secret-that-is-long-enough"
TEST_CATALOG = {
    "schema_version": 1,
    "source_commit": "test-commit",
    "completion_total": 2,
    "entries": {
        "paldeck:1": {
            "name": "Lamball",
            "paldeck_number": "1",
            "counts_toward_completion": True,
        },
        "paldeck:2": {
            "name": "Cattiva",
            "paldeck_number": "2",
            "counts_toward_completion": True,
        },
    },
    "aliases": {
        "pinkcat": "paldeck:2",
        "sheepball": "paldeck:1",
    },
}


class ArmoryParserTests(unittest.TestCase):
    def test_extracts_only_allowlisted_paldeck_data(self) -> None:
        archive_path = self._create_archive(
            {
                f"Saved/SaveGames/0/world/Players/{PLAYER_GUID}.sav": b"save",
                "Saved/Config/LinuxServer/Game.ini": b"sensitive",
            }
        )

        result = extract_snapshot(
            archive_path,
            SECRET,
            record_loader=lambda _: {
                "PalCaptureCount": {
                    "value": [
                        {"key": "PinkCat", "value": 11},
                        {"key": "SheepBall", "value": 0},
                    ]
                },
                "PaldeckUnlockFlag": {
                    "value": [
                        {"key": "PinkCat", "value": True},
                        {"key": "SheepBall", "value": True},
                    ]
                },
                "AccountId": "must-not-leak",
            },
            catalog=TEST_CATALOG,
        )

        player = result["players"][0]
        self.assertEqual(player["completed_entries"], 1)
        self.assertEqual(player["completion_total"], 2)
        self.assertEqual(player["completion_percent"], 50.0)
        self.assertEqual(player["encountered_entries"], 2)
        self.assertEqual(player["total_captures"], 11)
        self.assertEqual(player["unmapped_species_count"], 0)
        self.assertEqual(player["species"][0]["name"], "Lamball")
        self.assertEqual(player["species"][1]["name"], "Cattiva")
        self.assertEqual(len(player["internal_player_key"]), 64)
        self.assertNotIn(PLAYER_GUID, str(result))
        self.assertNotIn("must-not-leak", str(result))
        self.assertNotIn("Game.ini", str(result))

    def test_ignores_death_penalty_saves(self) -> None:
        archive_path = self._create_archive(
            {
                f"Saved/Players/{PLAYER_GUID}_dps.sav": b"save",
            }
        )

        with self.assertRaisesRegex(SnapshotError, "no player saves"):
            extract_snapshot(
                archive_path,
                SECRET,
                record_loader=lambda _: {},
                catalog=TEST_CATALOG,
            )

    def test_rejects_short_identity_secret(self) -> None:
        archive_path = self._create_archive(
            {f"Saved/Players/{PLAYER_GUID}.sav": b"save"}
        )

        with self.assertRaisesRegex(SnapshotError, "at least 32 bytes"):
            extract_snapshot(archive_path, b"short", record_loader=lambda _: {})

    def test_rejects_duplicate_player_save(self) -> None:
        archive_path = self._create_archive(
            {
                f"Saved/one/Players/{PLAYER_GUID}.sav": b"one",
                f"Saved/two/Players/{PLAYER_GUID}.sav": b"two",
            }
        )

        with self.assertRaisesRegex(SnapshotError, "duplicate player save"):
            extract_snapshot(
                archive_path,
                SECRET,
                record_loader=lambda _: {},
                catalog=TEST_CATALOG,
            )

    def test_rejects_duplicate_species(self) -> None:
        archive_path = self._create_archive(
            {f"Saved/Players/{PLAYER_GUID}.sav": b"save"}
        )

        with self.assertRaisesRegex(SnapshotError, "duplicate species"):
            extract_snapshot(
                archive_path,
                SECRET,
                record_loader=lambda _: {
                    "PalCaptureCount": {
                        "value": [
                            {"key": "PinkCat", "value": 1},
                            {"key": "PinkCat", "value": 2},
                        ]
                    },
                },
                catalog=TEST_CATALOG,
            )

    def test_maps_aliases_case_insensitively_and_excludes_humans(self) -> None:
        archive_path = self._create_archive(
            {f"Saved/Players/{PLAYER_GUID}.sav": b"save"}
        )

        result = extract_snapshot(
            archive_path,
            SECRET,
            record_loader=lambda _: {
                "PalCaptureCount": {
                    "value": [
                        {"key": "Sheepball", "value": 3},
                        {"key": "Human", "value": 99},
                    ]
                },
            },
            catalog=TEST_CATALOG,
        )

        player = result["players"][0]
        self.assertEqual(player["completed_entries"], 1)
        self.assertEqual(player["total_captures"], 3)
        self.assertEqual(len(player["species"]), 1)
        self.assertEqual(player["species"][0]["catalog_key"], "paldeck:1")

    def _create_archive(self, members: dict[str, bytes]) -> Path:
        temporary = tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False)
        temporary.close()
        archive_path = Path(temporary.name)
        self.addCleanup(archive_path.unlink, missing_ok=True)

        with tarfile.open(archive_path, mode="w:gz") as archive:
            for name, contents in members.items():
                member = tarfile.TarInfo(name=name)
                member.size = len(contents)
                archive.addfile(member, io.BytesIO(contents))

        return archive_path


if __name__ == "__main__":
    unittest.main()
