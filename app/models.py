from datetime import datetime

from pydantic import BaseModel


class PlayerSummary(BaseModel):
    current: int
    maximum: int


class PublicPlayer(BaseModel):
    name: str
    level: int | None = None


class PlayerListResponse(BaseModel):
    checked_at: datetime
    available: bool
    players: list[PublicPlayer]


class InfrastructureMetrics(BaseModel):
    cpu_percent: float | None = None

    memory_used_percent: float | None = None
    memory_used_bytes: int | None = None
    memory_total_bytes: int | None = None

    swap_used_percent: float | None = None
    swap_used_bytes: int | None = None
    swap_total_bytes: int | None = None

    disk_used_percent: float | None = None
    disk_used_bytes: int | None = None
    disk_total_bytes: int | None = None


class BackupStatus(BaseModel):
    exists: bool
    healthy: bool

    created_at: datetime | None = None
    age_seconds: int | None = None
    size_bytes: int | None = None


class ServerStatus(BaseModel):
    online: bool
    checked_at: datetime

    name: str | None = None
    version: str | None = None

    players: PlayerSummary

    server_fps: float | None = None
    frame_time_ms: float | None = None
    uptime_seconds: int | None = None
    world_day: int | None = None
    base_count: int | None = None

    infrastructure: InfrastructureMetrics | None = None
    latest_backup: BackupStatus | None = None

class HistoricalPlayer(BaseModel):
    name: str
    latest_level: int | None = None
    highest_level: int | None = None
    first_seen_at: datetime
    last_seen_at: datetime


class PlayerHistoryResponse(BaseModel):
    players: list[HistoricalPlayer]
