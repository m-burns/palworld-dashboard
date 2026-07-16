from datetime import UTC, datetime
from pathlib import Path

from app.models import BackupStatus


class BackupService:
    def __init__(
        self,
        directory: str,
        max_age_hours: int = 36,
    ) -> None:
        self._directory = Path(directory)
        self._max_age_seconds = max_age_hours * 60 * 60

    def get_latest_backup(self) -> BackupStatus:
        if not self._directory.exists():
            return BackupStatus(
                exists=False,
                healthy=False,
            )

        backup_files = [
            path
            for path in self._directory.rglob("*")
            if path.is_file()
        ]

        if not backup_files:
            return BackupStatus(
                exists=False,
                healthy=False,
            )

        latest = max(
            backup_files,
            key=lambda path: path.stat().st_mtime,
        )

        stat = latest.stat()

        created_at = datetime.fromtimestamp(
            stat.st_mtime,
            tz=UTC,
        )

        age_seconds = max(
            0,
            int(
                (
                    datetime.now(UTC) - created_at
                ).total_seconds()
            ),
        )

        return BackupStatus(
            exists=True,
            healthy=age_seconds <= self._max_age_seconds,
            created_at=created_at,
            age_seconds=age_seconds,
            size_bytes=stat.st_size,
        )
