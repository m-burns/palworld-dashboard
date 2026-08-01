from datetime import datetime

from pydantic import BaseModel, Field


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=2000)
    expires_at: datetime | None = None
    pinned: bool = False


class PublicAnnouncement(BaseModel):
    id: int
    title: str
    message: str
    published_at: datetime
    expires_at: datetime | None = None
    pinned: bool


class AnnouncementListResponse(BaseModel):
    generated_at: datetime
    announcements: list[PublicAnnouncement]
