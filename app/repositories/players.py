from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    PlayerRecord,
    PlayerSession,
)
from app.models import (
    HistoricalPlayer,
    LevelLeaderboardEntry,
    PlayerProfile,
    PlaytimeLeaderboardEntry,
    PublicPlayer,
)


class PlayerRepository:
    async def sync_online_players(
        self,
        session: AsyncSession,
        players: list[PublicPlayer],
    ) -> None:
        now = datetime.now(UTC)
        online_keys: set[str] = set()

        for player in players:
            player_key = self._normalise_player_key(
                player.name,
            )
            online_keys.add(player_key)

            record = await self._get_player_by_key(
                session=session,
                player_key=player_key,
            )

            if record is None:
                record = PlayerRecord(
                    player_key=player_key,
                    display_name=player.name,
                    latest_level=player.level,
                    highest_level=player.level,
                    first_seen_at=now,
                    last_seen_at=now,
                )
                session.add(record)
                await session.flush()
            else:
                record.display_name = player.name
                record.latest_level = player.level
                record.last_seen_at = now

                if (
                    player.level is not None
                    and (
                        record.highest_level is None
                        or player.level > record.highest_level
                    )
                ):
                    record.highest_level = player.level

            await self._ensure_open_session(
                session=session,
                player_id=record.id,
                started_at=now,
            )

        await self._close_offline_sessions(
            session=session,
            online_keys=online_keys,
            ended_at=now,
        )

        await session.commit()

    async def list_known_players(
        self,
        session: AsyncSession,
    ) -> list[HistoricalPlayer]:
        result = await session.execute(
            select(PlayerRecord).order_by(
                PlayerRecord.highest_level.desc(),
                PlayerRecord.display_name.asc(),
            )
        )

        return [
            HistoricalPlayer(
                name=record.display_name,
                latest_level=record.latest_level,
                highest_level=record.highest_level,
                first_seen_at=record.first_seen_at,
                last_seen_at=record.last_seen_at,
            )
            for record in result.scalars().all()
        ]

    async def get_level_leaderboard(
        self,
        session: AsyncSession,
        limit: int = 10,
    ) -> list[LevelLeaderboardEntry]:
        result = await session.execute(
            select(PlayerRecord)
            .where(PlayerRecord.highest_level.is_not(None))
            .order_by(
                PlayerRecord.highest_level.desc(),
                PlayerRecord.display_name.asc(),
            )
            .limit(limit)
        )

        records = result.scalars().all()

        return [
            LevelLeaderboardEntry(
                rank=index,
                name=record.display_name,
                highest_level=record.highest_level,
                latest_level=record.latest_level,
                last_seen_at=record.last_seen_at,
            )
            for index, record in enumerate(
                records,
                start=1,
            )
        ]

    async def get_playtime_leaderboard(
        self,
        session: AsyncSession,
        limit: int = 10,
    ) -> list[PlaytimeLeaderboardEntry]:
        now = datetime.now(UTC)

        player_result = await session.execute(
            select(PlayerRecord)
        )
        players = player_result.scalars().all()

        entries: list[PlaytimeLeaderboardEntry] = []

        for player in players:
            session_result = await session.execute(
                select(PlayerSession).where(
                    PlayerSession.player_id == player.id
                )
            )
            tracked_sessions = session_result.scalars().all()

            total_seconds = 0
            currently_online = False

            for tracked_session in tracked_sessions:
                if tracked_session.ended_at is None:
                    currently_online = True
                    started_at = self._as_utc(
                        tracked_session.started_at
                    )
                    total_seconds += max(
                        0,
                        int((now - started_at).total_seconds()),
                    )
                else:
                    total_seconds += (
                        tracked_session.duration_seconds or 0
                    )

            entries.append(
                PlaytimeLeaderboardEntry(
                    rank=0,
                    name=player.display_name,
                    total_seconds=total_seconds,
                    session_count=len(tracked_sessions),
                    currently_online=currently_online,
                    last_seen_at=player.last_seen_at,
                )
            )

        entries.sort(
            key=lambda entry: (
                -entry.total_seconds,
                entry.name.casefold(),
            )
        )

        limited_entries = entries[:limit]

        return [
            entry.model_copy(
                update={"rank": index}
            )
            for index, entry in enumerate(
                limited_entries,
                start=1,
            )
        ]

    async def _get_player_by_key(
        self,
        session: AsyncSession,
        player_key: str,
    ) -> PlayerRecord | None:
        result = await session.execute(
            select(PlayerRecord).where(
                PlayerRecord.player_key == player_key
            )
        )
        return result.scalar_one_or_none()

    async def _ensure_open_session(
        self,
        session: AsyncSession,
        player_id: int,
        started_at: datetime,
    ) -> None:
        result = await session.execute(
            select(PlayerSession).where(
                PlayerSession.player_id == player_id,
                PlayerSession.ended_at.is_(None),
            )
        )

        if result.scalar_one_or_none() is None:
            session.add(
                PlayerSession(
                    player_id=player_id,
                    started_at=started_at,
                )
            )

    async def _close_offline_sessions(
        self,
        session: AsyncSession,
        online_keys: set[str],
        ended_at: datetime,
    ) -> None:
        result = await session.execute(
            select(PlayerSession, PlayerRecord)
            .join(
                PlayerRecord,
                PlayerRecord.id == PlayerSession.player_id,
            )
            .where(PlayerSession.ended_at.is_(None))
        )

        for tracked_session, player in result.all():
            if player.player_key in online_keys:
                continue

            started_at = self._as_utc(
                tracked_session.started_at
            )

            tracked_session.ended_at = ended_at
            tracked_session.duration_seconds = max(
                0,
                int((ended_at - started_at).total_seconds()),
            )
            
    async def get_player_profile(
        self,
        session: AsyncSession,
        player_key: str,
    ) -> PlayerProfile | None:
        normalised_key = self._normalise_player_key(
            player_key,
        )

        player_result = await session.execute(
            select(PlayerRecord).where(
                PlayerRecord.player_key == normalised_key
            )
        )

        player = player_result.scalar_one_or_none()

        if player is None:
            return None

        session_result = await session.execute(
            select(PlayerSession)
            .where(PlayerSession.player_id == player.id)
            .order_by(PlayerSession.started_at.asc())
        )

        tracked_sessions = session_result.scalars().all()

        now = datetime.now(UTC)

        total_seconds = 0
        completed_durations: list[int] = []
        currently_online = False

        for tracked_session in tracked_sessions:
            if tracked_session.ended_at is None:
                currently_online = True

                started_at = self._as_utc(
                    tracked_session.started_at,
                )

                total_seconds += max(
                    0,
                    int(
                        (
                            now - started_at
                        ).total_seconds()
                    ),
                )

                continue

            duration = (
                tracked_session.duration_seconds
                or 0
            )

            duration = max(0, duration)

            total_seconds += duration
            completed_durations.append(duration)

        longest_session_seconds = (
            max(completed_durations)
            if completed_durations
            else 0
        )

        average_session_seconds = (
            int(
                sum(completed_durations)
                / len(completed_durations)
            )
            if completed_durations
            else 0
        )

        return PlayerProfile(
            player_key=player.player_key,
            name=player.display_name,
            latest_level=player.latest_level,
            highest_level=player.highest_level,
            first_seen_at=self._as_utc(
                player.first_seen_at,
            ),
            last_seen_at=self._as_utc(
                player.last_seen_at,
            ),
            currently_online=currently_online,
            total_playtime_seconds=total_seconds,
            session_count=len(tracked_sessions),
            completed_session_count=len(
                completed_durations,
            ),
            longest_session_seconds=(
                longest_session_seconds
            ),
            average_session_seconds=(
                average_session_seconds
            ),
        )

    @staticmethod
    def _normalise_player_key(name: str) -> str:
        return name.strip().casefold()

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)

        return value.astimezone(UTC)