from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.armory_models import (
    ArmoryLeaderboardResponse,
    ArmoryPlayerProfile,
    ArmorySnapshotImport,
)
from app.repositories.armory import ArmoryRepository


@dataclass(frozen=True)
class ArmoryImportResult:
    imported: bool
    snapshot_sha256: str
    player_count: int


class ArmoryService:
    def __init__(self, repository: ArmoryRepository) -> None:
        self._repository = repository

    async def ingest_snapshot(
        self,
        session: AsyncSession,
        payload: ArmorySnapshotImport,
    ) -> ArmoryImportResult:
        async with session.begin():
            exists = await self._repository.snapshot_exists(
                session,
                payload.snapshot_sha256,
            )
            if not exists:
                await self._repository.add_snapshot(session, payload)
            else:
                await self._repository.update_player_names(session, payload)

        return ArmoryImportResult(
            imported=not exists,
            snapshot_sha256=payload.snapshot_sha256,
            player_count=len(payload.players),
        )

    async def get_leaderboard(
        self,
        session: AsyncSession,
        limit: int,
    ) -> ArmoryLeaderboardResponse:
        snapshot = await self._repository.get_latest_snapshot(session)
        if snapshot is None:
            return ArmoryLeaderboardResponse(
                available=False,
                generated_at=datetime.now(UTC),
                players=[],
            )

        players = await self._repository.get_leaderboard(
            session,
            snapshot.id,
            limit,
        )
        return ArmoryLeaderboardResponse(
            available=True,
            generated_at=datetime.now(UTC),
            snapshot_created_at=self._as_utc(snapshot.snapshot_created_at),
            completion_total=snapshot.completion_total,
            players=players,
        )

    async def get_player_profile(
        self,
        session: AsyncSession,
        player_id: int,
    ) -> ArmoryPlayerProfile | None:
        snapshot = await self._repository.get_latest_snapshot(session)
        if snapshot is None:
            return None
        return await self._repository.get_player_profile(
            session,
            snapshot,
            player_id,
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
