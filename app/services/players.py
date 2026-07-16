from datetime import UTC, datetime
from typing import Any

from app.clients.palworld import (
    PalworldApiError,
    PalworldClient,
)
from app.models import (
    PlayerListResponse,
    PublicPlayer,
)


class PlayerService:
    def __init__(
        self,
        palworld_client: PalworldClient,
    ) -> None:
        self._palworld_client = palworld_client

    async def get_online_players(
        self,
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

        return PlayerListResponse(
            checked_at=checked_at,
            available=True,
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
