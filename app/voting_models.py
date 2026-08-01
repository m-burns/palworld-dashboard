from datetime import datetime

from pydantic import BaseModel, Field


class PollOptionPublic(BaseModel):
    id: int
    label: str
    votes: int


class PollPublic(BaseModel):
    id: int
    question: str
    created_at: datetime
    closes_at: datetime | None = None
    total_votes: int
    options: list[PollOptionPublic]


class PollListResponse(BaseModel):
    generated_at: datetime
    polls: list[PollPublic]


class VoteRequest(BaseModel):
    option_id: int = Field(gt=0)


class VoteResponse(BaseModel):
    accepted: bool
    poll: PollPublic
