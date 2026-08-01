from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.announcement_models import AnnouncementCreate
from app.database.base import Base
from app.database.models import Announcement
from app.repositories.announcements import AnnouncementRepository


class AnnouncementRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        temporary = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        temporary.close()
        self.database_path = Path(temporary.name)
        self.engine = create_async_engine(
            f"sqlite+aiosqlite:///{self.database_path}"
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.repository = AnnouncementRepository()

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()
        self.database_path.unlink(missing_ok=True)

    async def test_lists_pinned_active_announcements_first(self) -> None:
        async with self.sessions() as session:
            await self.repository.create(
                session,
                AnnouncementCreate(title="Normal", message="Hello"),
            )
            pinned = await self.repository.create(
                session,
                AnnouncementCreate(
                    title="Important",
                    message="Read this",
                    pinned=True,
                ),
            )

        async with self.sessions() as session:
            announcements = await self.repository.list_active(session, 10)

        self.assertEqual(
            [announcement.title for announcement in announcements],
            ["Important", "Normal"],
        )
        self.assertTrue(announcements[0].pinned)
        self.assertEqual(announcements[0].id, pinned.id)

    async def test_hides_expired_and_deactivated_announcements(self) -> None:
        now = datetime.now(UTC)
        async with self.sessions() as session:
            expired = Announcement(
                title="Expired",
                message="Old news",
                published_at=now - timedelta(days=2),
                expires_at=now - timedelta(days=1),
                pinned=False,
                active=True,
            )
            session.add(expired)
            await session.commit()
            active = await self.repository.create(
                session,
                AnnouncementCreate(title="Active", message="Current"),
            )
            self.assertTrue(
                await self.repository.deactivate(session, active.id)
            )

        async with self.sessions() as session:
            announcements = await self.repository.list_active(session, 10)

        self.assertEqual(announcements, [])


if __name__ == "__main__":
    unittest.main()
