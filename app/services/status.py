import asyncio
from datetime import UTC, datetime

from app.clients.palworld import (
    PalworldApiError,
    PalworldClient,
)
from app.models import PlayerSummary, ServerStatus
from app.services.backups import BackupService
from app.services.infrastructure import InfrastructureService


class StatusService:
    def __init__(
        self,
        palworld_client: PalworldClient,
        infrastructure_service: InfrastructureService,
        backup_service: BackupService,
    ) -> None:
        self._palworld_client = palworld_client
        self._infrastructure_service = infrastructure_service
        self._backup_service = backup_service

    async def get_status(self) -> ServerStatus:
        checked_at = datetime.now(UTC)

        infrastructure = (
            self._infrastructure_service.get_metrics()
        )

        latest_backup = (
            self._backup_service.get_latest_backup()
        )

        try:
            info, metrics = await asyncio.gather(
                self._palworld_client.get_info(),
                self._palworld_client.get_metrics(),
            )
        except PalworldApiError:
            return ServerStatus(
                online=False,
                checked_at=checked_at,
                players=PlayerSummary(
                    current=0,
                    maximum=0,
                ),
                infrastructure=infrastructure,
                latest_backup=latest_backup,
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
            infrastructure=infrastructure,
            latest_backup=latest_backup,
        )
