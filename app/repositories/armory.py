from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.armory_models import ArmorySnapshotImport
from app.database.models import (
    ArmoryPlayer,
    ArmoryPlayerSnapshot,
    ArmorySnapshot,
    ArmorySpeciesSnapshot,
)


class ArmoryRepository:
    async def snapshot_exists(
        self,
        session: AsyncSession,
        snapshot_sha256: str,
    ) -> bool:
        result = await session.execute(
            select(ArmorySnapshot.id).where(
                ArmorySnapshot.snapshot_sha256 == snapshot_sha256
            )
        )
        return result.scalar_one_or_none() is not None

    async def add_snapshot(
        self,
        session: AsyncSession,
        payload: ArmorySnapshotImport,
    ) -> None:
        snapshot_time = payload.snapshot_created_at.astimezone(UTC)
        snapshot = ArmorySnapshot(
            snapshot_sha256=payload.snapshot_sha256,
            snapshot_created_at=snapshot_time,
            schema_version=payload.schema_version,
            catalog_source_commit=payload.catalog_source_commit,
            completion_total=payload.completion_total,
            player_count=len(payload.players),
        )
        session.add(snapshot)
        await session.flush()

        for imported_player in payload.players:
            player = await self._get_player(
                session,
                imported_player.internal_player_key,
            )
            if player is None:
                player = ArmoryPlayer(
                    internal_player_key=imported_player.internal_player_key,
                    first_seen_at=snapshot_time,
                    last_seen_at=snapshot_time,
                )
                session.add(player)
                await session.flush()
            else:
                player.first_seen_at = min(
                    self._as_utc(player.first_seen_at), snapshot_time
                )
                player.last_seen_at = max(
                    self._as_utc(player.last_seen_at), snapshot_time
                )

            player_snapshot = ArmoryPlayerSnapshot(
                snapshot_id=snapshot.id,
                player_id=player.id,
                completed_entries=imported_player.completed_entries,
                completion_total=imported_player.completion_total,
                completion_percent=imported_player.completion_percent,
                encountered_entries=imported_player.encountered_entries,
                total_captures=imported_player.total_captures,
                unmapped_species_count=imported_player.unmapped_species_count,
            )
            session.add(player_snapshot)
            await session.flush()

            session.add_all(
                ArmorySpeciesSnapshot(
                    player_snapshot_id=player_snapshot.id,
                    catalog_key=species.catalog_key,
                    name=species.name,
                    paldeck_number=species.paldeck_number,
                    capture_count=species.capture_count,
                    discovered=species.discovered,
                    counts_toward_completion=species.counts_toward_completion,
                    catalog_status=species.catalog_status,
                )
                for species in imported_player.species
            )

    async def _get_player(
        self,
        session: AsyncSession,
        internal_player_key: str,
    ) -> ArmoryPlayer | None:
        result = await session.execute(
            select(ArmoryPlayer).where(
                ArmoryPlayer.internal_player_key == internal_player_key
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
