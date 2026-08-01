from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.voting import VotingRepository
from app.voting_models import PollListResponse, PollPublic


class VotingService:
    def __init__(self, repository: VotingRepository) -> None:
        self._repository = repository

    async def list_active(
        self,
        session: AsyncSession,
        limit: int,
    ) -> PollListResponse:
        return PollListResponse(
            generated_at=datetime.now(UTC),
            polls=await self._repository.list_active(session, limit),
        )

    async def vote(
        self,
        session: AsyncSession,
        poll_id: int,
        option_id: int,
        voter_hash: str,
    ) -> PollPublic:
        return await self._repository.vote(
            session,
            poll_id,
            option_id,
            voter_hash,
        )
