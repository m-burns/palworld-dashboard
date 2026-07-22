from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.armory_models import ArmorySnapshotImport
from app.database.base import Base
from app.database.models import (
    ArmoryPlayer,
    ArmoryPlayerName,
    ArmoryPlayerSnapshot,
    ArmorySnapshot,
    ArmorySpeciesSnapshot,
)
from app.repositories.armory import ArmoryRepository
from app.services.armory import ArmoryService


class ArmoryIngestionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        temporary = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        temporary.close()
        self.database_path = Path(temporary.name)
        self.engine = create_async_engine(
            f"sqlite+aiosqlite:///{self.database_path}"
        )
        self.sessions = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.service = ArmoryService(ArmoryRepository())

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()
        self.database_path.unlink(missing_ok=True)

    async def test_persists_a_valid_snapshot_atomically(self) -> None:
        async with self.sessions() as session:
            result = await self.service.ingest_snapshot(
                session,
                self._payload(),
            )

        self.assertTrue(result.imported)
        async with self.sessions() as session:
            self.assertEqual(await self._count(session, ArmorySnapshot), 1)
            self.assertEqual(await self._count(session, ArmoryPlayer), 1)
            self.assertEqual(await self._count(session, ArmoryPlayerName), 1)
            self.assertEqual(await self._count(session, ArmoryPlayerSnapshot), 1)
            self.assertEqual(await self._count(session, ArmorySpeciesSnapshot), 1)

    async def test_reimporting_a_snapshot_is_a_successful_no_op(self) -> None:
        payload = self._payload()
        async with self.sessions() as session:
            await self.service.ingest_snapshot(session, payload)
        async with self.sessions() as session:
            result = await self.service.ingest_snapshot(session, payload)

        self.assertFalse(result.imported)
        async with self.sessions() as session:
            self.assertEqual(await self._count(session, ArmorySnapshot), 1)

    async def test_reimport_backfills_a_missing_character_name(self) -> None:
        payload = self._payload()
        payload.players[0].display_name = None
        async with self.sessions() as session:
            await self.service.ingest_snapshot(session, payload)

        payload.players[0].display_name = "Recovered Name"
        async with self.sessions() as session:
            result = await self.service.ingest_snapshot(session, payload)
        async with self.sessions() as session:
            leaderboard = await self.service.get_leaderboard(session, limit=10)

        self.assertFalse(result.imported)
        self.assertEqual(leaderboard.players[0].display_name, "Recovered Name")

    async def test_out_of_order_import_preserves_seen_range(self) -> None:
        newest = datetime(2026, 7, 22, 12, tzinfo=UTC)
        oldest = newest - timedelta(hours=4)
        async with self.sessions() as session:
            await self.service.ingest_snapshot(
                session,
                self._payload(created_at=newest),
            )
        async with self.sessions() as session:
            await self.service.ingest_snapshot(
                session,
                self._payload(
                    created_at=oldest,
                    digest="b" * 64,
                ),
            )

        async with self.sessions() as session:
            player = (
                await session.execute(select(ArmoryPlayer))
            ).scalar_one()
            self.assertEqual(player.first_seen_at, oldest.replace(tzinfo=None))
            self.assertEqual(player.last_seen_at, newest.replace(tzinfo=None))

    async def test_database_error_rolls_back_the_whole_snapshot(self) -> None:
        payload = self._payload()

        class FailingRepository(ArmoryRepository):
            async def add_snapshot(self, session, imported_payload) -> None:
                await super().add_snapshot(session, imported_payload)
                raise RuntimeError("simulated failure")

        async with self.sessions() as session:
            with self.assertRaisesRegex(RuntimeError, "simulated failure"):
                await ArmoryService(FailingRepository()).ingest_snapshot(
                    session,
                    payload,
                )

        async with self.sessions() as session:
            self.assertEqual(await self._count(session, ArmorySnapshot), 0)

    async def test_empty_armory_is_reported_as_unavailable(self) -> None:
        async with self.sessions() as session:
            leaderboard = await self.service.get_leaderboard(session, limit=10)

        self.assertFalse(leaderboard.available)
        self.assertEqual(leaderboard.players, [])

    async def test_leaderboard_uses_latest_snapshot_without_private_keys(self) -> None:
        old_payload = self._payload()
        new_payload = self._payload(
            created_at=datetime(2026, 7, 22, 16, tzinfo=UTC),
            digest="e" * 64,
        )
        second_player = new_payload.players[0].model_copy(
            update={"internal_player_key": "f" * 64}
        )
        new_payload.players.append(second_player)

        async with self.sessions() as session:
            await self.service.ingest_snapshot(session, old_payload)
        async with self.sessions() as session:
            await self.service.ingest_snapshot(session, new_payload)
        async with self.sessions() as session:
            leaderboard = await self.service.get_leaderboard(session, limit=10)

        serialized = leaderboard.model_dump_json()
        self.assertTrue(leaderboard.available)
        self.assertEqual(len(leaderboard.players), 2)
        self.assertEqual(leaderboard.players[0].display_name, "Chosen Hero")
        self.assertNotIn("d" * 64, serialized)
        self.assertNotIn("f" * 64, serialized)

    async def test_profile_returns_only_public_progress_fields(self) -> None:
        async with self.sessions() as session:
            await self.service.ingest_snapshot(session, self._payload())
        async with self.sessions() as session:
            profile = await self.service.get_player_profile(session, player_id=1)

        self.assertIsNotNone(profile)
        assert profile is not None
        serialized = profile.model_dump_json()
        self.assertEqual(profile.display_name, "Chosen Hero")
        self.assertEqual(profile.species[0].name, "Lamball")
        self.assertNotIn("d" * 64, serialized)

    async def test_unknown_profile_is_not_returned(self) -> None:
        async with self.sessions() as session:
            await self.service.ingest_snapshot(session, self._payload())
        async with self.sessions() as session:
            profile = await self.service.get_player_profile(
                session,
                player_id=999,
            )

        self.assertIsNone(profile)

    async def test_missing_character_name_uses_private_fallback_label(self) -> None:
        payload = self._payload()
        payload.players[0].display_name = None
        async with self.sessions() as session:
            await self.service.ingest_snapshot(session, payload)
        async with self.sessions() as session:
            leaderboard = await self.service.get_leaderboard(session, limit=10)

        self.assertEqual(leaderboard.players[0].display_name, "Player 001")

    async def test_older_snapshot_does_not_restore_an_old_character_name(self) -> None:
        newest = self._payload(
            created_at=datetime(2026, 7, 22, 16, tzinfo=UTC),
            digest="1" * 64,
        )
        oldest = self._payload(
            created_at=datetime(2026, 7, 22, 12, tzinfo=UTC),
            digest="2" * 64,
        )
        newest.players[0].display_name = "Current Name"
        oldest.players[0].display_name = "Old Name"

        async with self.sessions() as session:
            await self.service.ingest_snapshot(session, newest)
        async with self.sessions() as session:
            await self.service.ingest_snapshot(session, oldest)
        async with self.sessions() as session:
            profile = await self.service.get_player_profile(session, player_id=1)

        self.assertIsNotNone(profile)
        assert profile is not None
        self.assertEqual(profile.display_name, "Current Name")

    @staticmethod
    async def _count(session, model: type) -> int:
        result = await session.execute(select(func.count()).select_from(model))
        return result.scalar_one()

    @staticmethod
    def _payload(
        created_at: datetime | None = None,
        digest: str = "a" * 64,
    ) -> ArmorySnapshotImport:
        return ArmorySnapshotImport.model_validate(
            {
                "schema_version": 3,
                "snapshot_sha256": digest,
                "snapshot_created_at": (
                    created_at or datetime(2026, 7, 22, 12, tzinfo=UTC)
                ).isoformat(),
                "catalog_source_commit": "c" * 40,
                "completion_total": 299,
                "players": [
                    {
                        "internal_player_key": "d" * 64,
                        "display_name": "Chosen Hero",
                        "completed_entries": 1,
                        "completion_total": 299,
                        "completion_percent": 0.33,
                        "encountered_entries": 1,
                        "total_captures": 2,
                        "unmapped_species_count": 0,
                        "species": [
                            {
                                "catalog_key": "paldeck:1",
                                "name": "Lamball",
                                "paldeck_number": "1",
                                "capture_count": 2,
                                "discovered": True,
                                "counts_toward_completion": True,
                                "catalog_status": "mapped",
                            }
                        ],
                    }
                ],
            }
        )


if __name__ == "__main__":
    unittest.main()
