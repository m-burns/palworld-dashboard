from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.palworld import (
    PalworldApiError,
    PalworldClient,
)
from app.models import (
    PlayerHistoryResponse,
    PlayerListResponse,
    PublicPlayer,
)
from app.repositories.players import PlayerRepository

from app.models import (
    LevelLeaderboardResponse,
    PlayerHistoryResponse,
    PlayerListResponse,
    PublicPlayer,
    PlaytimeLeaderboardResponse,
)


class PlayerService:
    def __init__(
        self,
        palworld_client: PalworldClient,
        player_repository: PlayerRepository,
    ) -> None:
        self._palworld_client = palworld_client
        self._player_repository = player_repository

    async def get_online_players(
        self,
        session: AsyncSession,
    ) -> PlayerListResponse:
        checked_at = datetime.now(UTC)

        try:
            payload = (
                await self._palworld_client.get_players()
            )
        except PalworldApiError:
            return PlayerListResponse(
                checked_at=checked_at,
                available=False,
                players=[],
            )

        raw_players = payload.get("players", [])

        players = [
            self._to_public_player(player)
            for player in raw_players
            if isinstance(player, dict)
        ]

        players.sort(
            key=lambda player: (
                -(player.level or 0),
                player.name.casefold(),
            )
        )

        await self._player_repository.sync_online_players(
            session=session,
            players=players,
        )

        return PlayerListResponse(
            checked_at=checked_at,
            available=True,
            players=players,
        )

    async def get_player_history(
        self,
        session: AsyncSession,
    ) -> PlayerHistoryResponse:
        players = (
            await self._player_repository.list_known_players(
                session=session,
            )
        )

        return PlayerHistoryResponse(
            players=players,
        )
    
    async def get_level_leaderboard(
        self,
        session: AsyncSession,
        limit: int = 10,
    ) -> LevelLeaderboardResponse:
        players = (
            await self._player_repository.get_level_leaderboard(
                session=session,
                limit=limit,
            )
        )

        return LevelLeaderboardResponse(
            generated_at=datetime.now(UTC),
            players=players,
        )

    async def get_playtime_leaderboard(
        self,
        session: AsyncSession,
        limit: int = 10,
    ) -> PlaytimeLeaderboardResponse:
        players = (
            await self._player_repository.get_playtime_leaderboard(
                session=session,
                limit=limit,
            )
        )

        return PlaytimeLeaderboardResponse(
            generated_at=datetime.now(UTC),
            players=players,
        )

    @staticmethod
    def _to_public_player(
        player: dict[str, Any],
    ) -> PublicPlayer:
        raw_level = player.get("level")

        try:
            level = (
                int(raw_level)
                if raw_level is not None
                else None
            )
        except (
            TypeError,
            ValueError,
        ):
            level = None

        raw_name = player.get("name")

        name = (
            str(raw_name).strip()
            if raw_name
            else "Unknown player"
        )

        return PublicPlayer(
            name=name,
            level=level,
        )