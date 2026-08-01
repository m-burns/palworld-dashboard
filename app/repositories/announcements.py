from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.announcement_models import AnnouncementCreate, PublicAnnouncement
from app.database.models import Announcement


class AnnouncementRepository:
    async def create(
        self,
        session: AsyncSession,
        payload: AnnouncementCreate,
    ) -> PublicAnnouncement:
        now = datetime.now(UTC)
        announcement = Announcement(
            title=payload.title.strip(),
            message=payload.message.strip(),
            published_at=now,
            expires_at=payload.expires_at,
            pinned=payload.pinned,
            active=True,
        )
        session.add(announcement)
        await session.commit()
        await session.refresh(announcement)
        return self._to_public(announcement)

    async def list_active(
        self,
        session: AsyncSession,
        limit: int,
    ) -> list[PublicAnnouncement]:
        now = datetime.now(UTC)
        result = await session.execute(
            select(Announcement)
            .where(
                Announcement.active.is_(True),
                Announcement.published_at <= now,
                (
                    Announcement.expires_at.is_(None)
                    | (Announcement.expires_at > now)
                ),
            )
            .order_by(
                Announcement.pinned.desc(),
                Announcement.published_at.desc(),
            )
            .limit(limit)
        )
        return [
            self._to_public(announcement)
            for announcement in result.scalars().all()
        ]

    async def deactivate(
        self,
        session: AsyncSession,
        announcement_id: int,
    ) -> bool:
        announcement = await session.get(Announcement, announcement_id)
        if announcement is None or not announcement.active:
            return False
        announcement.active = False
        await session.commit()
        return True

    @staticmethod
    def _to_public(announcement: Announcement) -> PublicAnnouncement:
        return PublicAnnouncement(
            id=announcement.id,
            title=announcement.title,
            message=announcement.message,
            published_at=AnnouncementRepository._as_utc(
                announcement.published_at
            ),
            expires_at=(
                AnnouncementRepository._as_utc(announcement.expires_at)
                if announcement.expires_at is not None
                else None
            ),
            pinned=announcement.pinned,
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
