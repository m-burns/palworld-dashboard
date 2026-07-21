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
                "schema_version": 2,
                "snapshot_sha256": digest,
                "snapshot_created_at": (
                    created_at or datetime(2026, 7, 22, 12, tzinfo=UTC)
                ).isoformat(),
                "catalog_source_commit": "c" * 40,
                "completion_total": 299,
                "players": [
                    {
                        "internal_player_key": "d" * 64,
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
