from datetime import datetime

from pydantic import BaseModel


class PlayerSummary(BaseModel):
    current: int
    maximum: int


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
