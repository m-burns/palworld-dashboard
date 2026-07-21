from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.armory_models import ArmorySnapshotImport
from app.database.base import Base
from app.repositories.armory import ArmoryRepository
from app.services.armory import ArmoryImportResult, ArmoryService


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest a sanitized Paldeck snapshot into the dashboard database",
    )
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        help="Sanitized JSON file; omit to read standard input",
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get(
            "DATABASE_URL",
            "sqlite+aiosqlite:////app/data/dashboard.db",
        ),
    )
    args = parser.parse_args()

    try:
        raw_payload = (
            args.input.read_text(encoding="utf-8")
            if args.input is not None
            else sys.stdin.read()
        )
        payload = ArmorySnapshotImport.model_validate_json(raw_payload)
        result = asyncio.run(_ingest(args.database_url, payload))
    except ValidationError:
        print("Armory ingestion failed: input validation failed", file=sys.stderr)
        return 1
    except (OSError, json.JSONDecodeError, SQLAlchemyError, ValueError) as exc:
        print(f"Armory ingestion failed: {exc}", file=sys.stderr)
        return 1

    action = "imported" if result.imported else "already imported"
    print(
        f"Snapshot {action}: {result.player_count} pseudonymous players",
        file=sys.stderr,
    )
    return 0


async def _ingest(
    database_url: str,
    payload: ArmorySnapshotImport,
) -> ArmoryImportResult:
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            return await ArmoryService(ArmoryRepository()).ingest_snapshot(
                session,
                payload,
            )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
