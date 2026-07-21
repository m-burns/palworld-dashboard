from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.armory_models import ArmorySnapshotImport
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

        return ArmoryImportResult(
            imported=not exists,
            snapshot_sha256=payload.snapshot_sha256,
            player_count=len(payload.players),
        )
