from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import PlayerRecord
from app.models import HistoricalPlayer, PublicPlayer


class PlayerRepository:
    async def upsert_online_players(
        self,
        session: AsyncSession,
        players: list[PublicPlayer],
    ) -> None:
        now = datetime.now(UTC)

        for player in players:
            player_key = self._normalise_player_key(
                player.name,
            )

            result = await session.execute(
                select(PlayerRecord).where(
                    PlayerRecord.player_key == player_key,
                )
            )

            record = result.scalar_one_or_none()

            if record is None:
                session.add(
                    PlayerRecord(
                        player_key=player_key,
                        display_name=player.name,
                        latest_level=player.level,
                        highest_level=player.level,
                        first_seen_at=now,
                        last_seen_at=now,
                    )
                )
                continue

            record.display_name = player.name
            record.latest_level = player.level
            record.last_seen_at = now

            if player.level is not None:
                if (
                    record.highest_level is None
                    or player.level > record.highest_level
                ):
                    record.highest_level = player.level

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

        records = result.scalars().all()

        return [
            HistoricalPlayer(
                name=record.display_name,
                latest_level=record.latest_level,
                highest_level=record.highest_level,
                first_seen_at=record.first_seen_at,
                last_seen_at=record.last_seen_at,
            )
            for record in records
        ]

    @staticmethod
    def _normalise_player_key(name: str) -> str:
        return name.strip().casefold()