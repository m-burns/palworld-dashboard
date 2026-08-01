from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database.base import Base
from app.repositories.voting import (
    DuplicateVoteError,
    InvalidVoteError,
    VotingRepository,
)


class VotingRepositoryTests(unittest.IsolatedAsyncioTestCase):
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
        self.repository = VotingRepository()

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()
        self.database_path.unlink(missing_ok=True)

    async def test_records_one_vote_per_browser_hash(self) -> None:
        async with self.sessions() as session:
            poll_id = await self.repository.create_poll(
                session,
                "Where should we build?",
                ["Desert", "Snow"],
            )
        async with self.sessions() as session:
            poll = (await self.repository.list_active(session, 5))[0]
            option_id = poll.options[0].id
            voted = await self.repository.vote(
                session,
                poll_id,
                option_id,
                "a" * 64,
            )

        self.assertEqual(voted.total_votes, 1)
        self.assertEqual(voted.options[0].votes, 1)

        async with self.sessions() as session:
            with self.assertRaises(DuplicateVoteError):
                await self.repository.vote(
                    session,
                    poll_id,
                    option_id,
                    "a" * 64,
                )

    async def test_rejects_an_option_from_another_poll(self) -> None:
        async with self.sessions() as session:
            first_id = await self.repository.create_poll(
                session,
                "First?",
                ["Yes", "No"],
            )
        async with self.sessions() as session:
            await self.repository.create_poll(
                session,
                "Second?",
                ["One", "Two"],
            )
            polls = await self.repository.list_active(session, 5)
            second = next(poll for poll in polls if poll.id != first_id)

        async with self.sessions() as session:
            with self.assertRaises(InvalidVoteError):
                await self.repository.vote(
                    session,
                    first_id,
                    second.options[0].id,
                    "b" * 64,
                )

    async def test_closed_poll_is_not_listed_or_votable(self) -> None:
        async with self.sessions() as session:
            poll_id = await self.repository.create_poll(
                session,
                "Continue?",
                ["Yes", "No"],
            )
        async with self.sessions() as session:
            poll = (await self.repository.list_active(session, 5))[0]
            option_id = poll.options[0].id
            self.assertTrue(await self.repository.close_poll(session, poll_id))

        async with self.sessions() as session:
            self.assertEqual(await self.repository.list_active(session, 5), [])
            with self.assertRaises(InvalidVoteError):
                await self.repository.vote(
                    session,
                    poll_id,
                    option_id,
                    "c" * 64,
                )


if __name__ == "__main__":
    unittest.main()
