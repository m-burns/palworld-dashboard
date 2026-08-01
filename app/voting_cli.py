from __future__ import annotations

import argparse
import asyncio
import os
from datetime import datetime

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database.base import Base
from app.repositories.voting import VotingRepository


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage community polls")
    parser.add_argument(
        "--database-url",
        default=os.environ.get(
            "DATABASE_URL",
            "sqlite+aiosqlite:////app/data/dashboard.db",
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create")
    create.add_argument("question")
    create.add_argument("options", nargs="+")
    create.add_argument("--closes-at", type=datetime.fromisoformat)
    close = commands.add_parser("close")
    close.add_argument("poll_id", type=int)
    args = parser.parse_args()
    return asyncio.run(run(args))


async def run(args: argparse.Namespace) -> int:
    engine = create_async_engine(args.database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    repository = VotingRepository()
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with sessions() as session:
            if args.command == "create":
                if len(args.options) < 2:
                    print("A poll requires at least two options")
                    return 1
                poll_id = await repository.create_poll(
                    session,
                    args.question,
                    args.options,
                    args.closes_at,
                )
                print(f"Created poll {poll_id}")
                return 0
            closed = await repository.close_poll(session, args.poll_id)
            print("Poll closed" if closed else "Poll not found")
            return 0 if closed else 1
    finally:
        await engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
