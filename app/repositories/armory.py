from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.armory_models import (
    ArmoryLeaderboardEntry,
    ArmoryPlayerProfile,
    ArmorySnapshotImport,
    ArmorySpeciesProgress,
)
from app.database.models import (
    ArmoryPlayer,
    ArmoryPlayerName,
    ArmoryPlayerSnapshot,
    ArmorySnapshot,
    ArmorySpeciesSnapshot,
)


class ArmoryRepository:
    async def get_latest_snapshot(
        self,
        session: AsyncSession,
    ) -> ArmorySnapshot | None:
        result = await session.execute(
            select(ArmorySnapshot).order_by(
                ArmorySnapshot.snapshot_created_at.desc(),
                ArmorySnapshot.id.desc(),
            ).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_leaderboard(
        self,
        session: AsyncSession,
        snapshot_id: int,
        limit: int,
    ) -> list[ArmoryLeaderboardEntry]:
        result = await session.execute(
            select(ArmoryPlayerSnapshot, ArmoryPlayer, ArmoryPlayerName)
            .join(
                ArmoryPlayer,
                ArmoryPlayer.id == ArmoryPlayerSnapshot.player_id,
            )
            .outerjoin(
                ArmoryPlayerName,
                ArmoryPlayerName.player_id == ArmoryPlayer.id,
            )
            .where(ArmoryPlayerSnapshot.snapshot_id == snapshot_id)
            .order_by(
                ArmoryPlayerSnapshot.completed_entries.desc(),
                ArmoryPlayerSnapshot.total_captures.desc(),
                ArmoryPlayer.id.asc(),
            )
            .limit(limit)
        )
        return [
            ArmoryLeaderboardEntry(
                rank=rank,
                player_id=player.id,
                display_name=self._display_name(player.id, player_name),
                completed_entries=progress.completed_entries,
                completion_total=progress.completion_total,
                completion_percent=progress.completion_percent,
                encountered_entries=progress.encountered_entries,
                total_captures=progress.total_captures,
            )
            for rank, (progress, player, player_name) in enumerate(
                result.all(), start=1
            )
        ]

    async def get_player_profile(
        self,
        session: AsyncSession,
        snapshot: ArmorySnapshot,
        player_id: int,
    ) -> ArmoryPlayerProfile | None:
        result = await session.execute(
            select(ArmoryPlayerSnapshot, ArmoryPlayer, ArmoryPlayerName)
            .join(
                ArmoryPlayer,
                ArmoryPlayer.id == ArmoryPlayerSnapshot.player_id,
            )
            .outerjoin(
                ArmoryPlayerName,
                ArmoryPlayerName.player_id == ArmoryPlayer.id,
            )
            .where(
                ArmoryPlayerSnapshot.snapshot_id == snapshot.id,
                ArmoryPlayer.id == player_id,
            )
        )
        row = result.one_or_none()
        if row is None:
            return None

        progress, player, player_name = row
        species_result = await session.execute(
            select(ArmorySpeciesSnapshot).where(
                ArmorySpeciesSnapshot.player_snapshot_id == progress.id
            )
        )
        species = [
            ArmorySpeciesProgress(
                catalog_key=entry.catalog_key,
                name=entry.name,
                paldeck_number=entry.paldeck_number,
                capture_count=entry.capture_count,
                discovered=entry.discovered,
                counts_toward_completion=entry.counts_toward_completion,
                catalog_status=entry.catalog_status,
            )
            for entry in species_result.scalars().all()
        ]
        species.sort(key=self._species_sort_key)

        return ArmoryPlayerProfile(
            player_id=player.id,
            display_name=self._display_name(player.id, player_name),
            snapshot_created_at=self._as_utc(snapshot.snapshot_created_at),
            completed_entries=progress.completed_entries,
            completion_total=progress.completion_total,
            completion_percent=progress.completion_percent,
            encountered_entries=progress.encountered_entries,
            total_captures=progress.total_captures,
            unmapped_species_count=progress.unmapped_species_count,
            species=species,
        )

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

            await self._upsert_player_name(
                session,
                player,
                imported_player.display_name,
                snapshot_time,
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

    async def update_player_names(
        self,
        session: AsyncSession,
        payload: ArmorySnapshotImport,
    ) -> None:
        snapshot_time = payload.snapshot_created_at.astimezone(UTC)
        for imported_player in payload.players:
            player = await self._get_player(
                session,
                imported_player.internal_player_key,
            )
            if player is None:
                continue
            await self._upsert_player_name(
                session,
                player,
                imported_player.display_name,
                snapshot_time,
            )

    async def _upsert_player_name(
        self,
        session: AsyncSession,
        player: ArmoryPlayer,
        display_name: str | None,
        observed_at: datetime,
    ) -> None:
        if display_name is None:
            return
        player_name = await self._get_player_name(session, player.id)
        if player_name is None:
            session.add(
                ArmoryPlayerName(
                    player_id=player.id,
                    display_name=display_name,
                    observed_at=observed_at,
                )
            )
        elif self._as_utc(player_name.observed_at) <= observed_at:
            player_name.display_name = display_name
            player_name.observed_at = observed_at

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

    async def _get_player_name(
        self,
        session: AsyncSession,
        player_id: int,
    ) -> ArmoryPlayerName | None:
        result = await session.execute(
            select(ArmoryPlayerName).where(
                ArmoryPlayerName.player_id == player_id
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _display_name(
        player_id: int,
        player_name: ArmoryPlayerName | None,
    ) -> str:
        if player_name is not None:
            return player_name.display_name
        return f"Player {player_id:03d}"

    @staticmethod
    def _species_sort_key(
        species: ArmorySpeciesProgress,
    ) -> tuple[bool, int, str, str]:
        number = species.paldeck_number
        if number is None:
            return (True, 0, "", species.name.casefold())
        suffix = "B" if number.endswith("B") else ""
        index = int(number[:-1] if suffix else number)
        return (False, index, suffix, species.name.casefold())
