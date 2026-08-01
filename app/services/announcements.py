from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.announcement_models import AnnouncementListResponse
from app.repositories.announcements import AnnouncementRepository


class AnnouncementService:
    def __init__(self, repository: AnnouncementRepository) -> None:
        self._repository = repository

    async def list_active(
        self,
        session: AsyncSession,
        limit: int,
    ) -> AnnouncementListResponse:
        announcements = await self._repository.list_active(session, limit)
        return AnnouncementListResponse(
            generated_at=datetime.now(UTC),
            announcements=announcements,
        )
