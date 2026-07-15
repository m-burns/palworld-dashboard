import asyncio
from datetime import UTC, datetime

from app.clients.palworld import (
    PalworldApiError,
    PalworldClient,
)
from app.models import PlayerSummary, ServerStatus


class StatusService:
    def __init__(self, client: PalworldClient) -> None:
        self._client = client

    async def get_status(self) -> ServerStatus:
        checked_at = datetime.now(UTC)

        try:
            info, metrics = await asyncio.gather(
                self._client.get_info(),
                self._client.get_metrics(),
            )
        except PalworldApiError:
            return ServerStatus(
                online=False,
                checked_at=checked_at,
                players=PlayerSummary(
                    current=0,
                    maximum=0,
                ),
            )

        return ServerStatus(
            online=True,
            checked_at=checked_at,
            name=info.get("servername"),
            version=info.get("version"),
            players=PlayerSummary(
                current=int(
                    metrics.get("currentplayernum", 0)
                ),
                maximum=int(
                    metrics.get("maxplayernum", 0)
                ),
            ),
            server_fps=metrics.get("serverfps"),
            frame_time_ms=metrics.get("serverframetime"),
            uptime_seconds=metrics.get("uptime"),
            world_day=metrics.get("days"),
            base_count=metrics.get("basecampnum"),
        )
