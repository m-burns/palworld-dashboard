from __future__ import annotations

import argparse
import asyncio
import os
from datetime import datetime

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.announcement_models import AnnouncementCreate
from app.database.base import Base
from app.repositories.announcements import AnnouncementRepository


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage dashboard announcements")
    parser.add_argument(
        "--database-url",
        default=os.environ.get(
            "DATABASE_URL",
            "sqlite+aiosqlite:////app/data/dashboard.db",
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)

    add = commands.add_parser("add", help="Publish an announcement")
    add.add_argument("title")
    add.add_argument("message")
    add.add_argument("--pinned", action="store_true")
    add.add_argument("--expires-at", type=datetime.fromisoformat)

    remove = commands.add_parser("deactivate", help="Hide an announcement")
    remove.add_argument("announcement_id", type=int)

    args = parser.parse_args()
    return asyncio.run(run_command(args))


async def run_command(args: argparse.Namespace) -> int:
    engine = create_async_engine(args.database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    repository = AnnouncementRepository()
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with sessions() as session:
            if args.command == "add":
                announcement = await repository.create(
                    session,
                    AnnouncementCreate(
                        title=args.title,
                        message=args.message,
                        pinned=args.pinned,
                        expires_at=args.expires_at,
                    ),
                )
                print(f"Published announcement {announcement.id}")
                return 0
            removed = await repository.deactivate(
                session,
                args.announcement_id,
            )
            print("Announcement deactivated" if removed else "Announcement not found")
            return 0 if removed else 1
    finally:
        await engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
