import json
from datetime import UTC, datetime
from pathlib import Path

from app.models import BackupStatus


class BackupService:
    def __init__(
        self,
        status_file: str,
        max_age_hours: int = 36,
    ) -> None:
        self._status_file = Path(status_file)
        self._max_age_seconds = max_age_hours * 60 * 60

    def get_latest_backup(self) -> BackupStatus:
        try:
            payload = json.loads(
                self._status_file.read_text(encoding="utf-8")
            )
            created_at = datetime.fromisoformat(payload["created_at"])
            created_at = (
                created_at.replace(tzinfo=UTC)
                if created_at.tzinfo is None
                else created_at.astimezone(UTC)
            )
            size_bytes = int(payload["size_bytes"])
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return BackupStatus(exists=False, healthy=False)

        age_seconds = max(
            0,
            int((datetime.now(UTC) - created_at).total_seconds()),
        )
        return BackupStatus(
            exists=True,
            healthy=age_seconds <= self._max_age_seconds,
            created_at=created_at,
            age_seconds=age_seconds,
            size_bytes=max(0, size_bytes),
        )
