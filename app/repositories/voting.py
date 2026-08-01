from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import CommunityPoll, PollOption, PollVote
from app.voting_models import PollOptionPublic, PollPublic


class DuplicateVoteError(Exception):
    pass


class InvalidVoteError(Exception):
    pass


class VotingRepository:
    async def create_poll(
        self,
        session: AsyncSession,
        question: str,
        options: list[str],
        closes_at: datetime | None = None,
    ) -> int:
        poll = CommunityPoll(
            question=question.strip(),
            closes_at=closes_at,
            active=True,
        )
        session.add(poll)
        await session.flush()
        session.add_all(
            [
                PollOption(
                    poll_id=poll.id,
                    label=label.strip(),
                    position=position,
                )
                for position, label in enumerate(options)
            ]
        )
        await session.commit()
        return poll.id

    async def close_poll(self, session: AsyncSession, poll_id: int) -> bool:
        poll = await session.get(CommunityPoll, poll_id)
        if poll is None or not poll.active:
            return False
        poll.active = False
        await session.commit()
        return True

    async def list_active(
        self,
        session: AsyncSession,
        limit: int,
    ) -> list[PollPublic]:
        now = datetime.now(UTC)
        result = await session.execute(
            select(CommunityPoll)
            .where(
                CommunityPoll.active.is_(True),
                (
                    CommunityPoll.closes_at.is_(None)
                    | (CommunityPoll.closes_at > now)
                ),
            )
            .order_by(CommunityPoll.created_at.desc())
            .limit(limit)
        )
        return [
            await self._to_public(session, poll)
            for poll in result.scalars().all()
        ]

    async def get_public(
        self,
        session: AsyncSession,
        poll_id: int,
    ) -> PollPublic | None:
        poll = await session.get(CommunityPoll, poll_id)
        if poll is None:
            return None
        return await self._to_public(session, poll)

    async def vote(
        self,
        session: AsyncSession,
        poll_id: int,
        option_id: int,
        voter_hash: str,
    ) -> PollPublic:
        now = datetime.now(UTC)
        poll = await session.get(CommunityPoll, poll_id)
        if (
            poll is None
            or not poll.active
            or (
                poll.closes_at is not None
                and self._as_utc(poll.closes_at) <= now
            )
        ):
            raise InvalidVoteError("Poll is not active")

        option = await session.get(PollOption, option_id)
        if option is None or option.poll_id != poll_id:
            raise InvalidVoteError("Option does not belong to this poll")

        session.add(
            PollVote(
                poll_id=poll_id,
                option_id=option_id,
                voter_hash=voter_hash,
            )
        )
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise DuplicateVoteError from exc
        return await self._to_public(session, poll)

    async def _to_public(
        self,
        session: AsyncSession,
        poll: CommunityPoll,
    ) -> PollPublic:
        result = await session.execute(
            select(
                PollOption,
                func.count(PollVote.id),
            )
            .outerjoin(PollVote, PollVote.option_id == PollOption.id)
            .where(PollOption.poll_id == poll.id)
            .group_by(PollOption.id)
            .order_by(PollOption.position.asc())
        )
        options = [
            PollOptionPublic(
                id=option.id,
                label=option.label,
                votes=vote_count,
            )
            for option, vote_count in result.all()
        ]
        return PollPublic(
            id=poll.id,
            question=poll.question,
            created_at=self._as_utc(poll.created_at),
            closes_at=(
                self._as_utc(poll.closes_at)
                if poll.closes_at is not None
                else None
            ),
            total_votes=sum(option.votes for option in options),
            options=options,
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
