from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database.base import Base
from app.database.models import PlayerRecord, PlayerSession
from app.repositories.players import PlayerRepository


class ActivityTimelineTests(unittest.IsolatedAsyncioTestCase):
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
        self.repository = PlayerRepository()

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()
        self.database_path.unlink(missing_ok=True)

    async def test_returns_join_and_leave_events_newest_first(self) -> None:
        started_at = datetime(2026, 8, 1, 12, tzinfo=UTC)
        ended_at = started_at + timedelta(minutes=45)

        async with self.sessions() as session:
            player = PlayerRecord(
                player_key="lamball",
                display_name="Lamball",
                first_seen_at=started_at,
                last_seen_at=ended_at,
            )
            session.add(player)
            await session.flush()
            session.add(
                PlayerSession(
                    player_id=player.id,
                    started_at=started_at,
                    ended_at=ended_at,
                    duration_seconds=2700,
                )
            )
            await session.commit()

        async with self.sessions() as session:
            events = await self.repository.get_activity_timeline(
                session,
                limit=10,
            )

        self.assertEqual([event.event_type for event in events], ["left", "joined"])
        self.assertEqual(events[0].player_key, "lamball")
        self.assertEqual(events[0].session_duration_seconds, 2700)
        self.assertEqual(events[1].session_duration_seconds, None)
        self.assertEqual(events[0].occurred_at, ended_at)

    async def test_limit_applies_after_combining_event_types(self) -> None:
        started_at = datetime(2026, 8, 1, 12, tzinfo=UTC)

        async with self.sessions() as session:
            player = PlayerRecord(
                player_key="chikipi",
                display_name="Chikipi",
                first_seen_at=started_at,
                last_seen_at=started_at,
            )
            session.add(player)
            await session.flush()
            session.add(
                PlayerSession(
                    player_id=player.id,
                    started_at=started_at,
                )
            )
            await session.commit()

        async with self.sessions() as session:
            events = await self.repository.get_activity_timeline(
                session,
                limit=1,
            )

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "joined")


if __name__ == "__main__":
    unittest.main()
