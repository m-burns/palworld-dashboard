from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ArmorySpeciesImport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    catalog_key: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=255)
    paldeck_number: str | None = Field(
        default=None,
        pattern=r"^[0-9]+B?$",
        max_length=16,
    )
    capture_count: int = Field(ge=0)
    discovered: bool
    counts_toward_completion: bool
    catalog_status: Literal["mapped", "unmapped"]


class ArmoryPlayerImport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    internal_player_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    completed_entries: int = Field(ge=0)
    completion_total: int = Field(gt=0)
    completion_percent: float = Field(ge=0, le=100)
    encountered_entries: int = Field(ge=0)
    total_captures: int = Field(ge=0)
    unmapped_species_count: int = Field(ge=0)
    species: list[ArmorySpeciesImport]

    @model_validator(mode="after")
    def validate_totals(self) -> "ArmoryPlayerImport":
        expected_percent = round(
            self.completed_entries / self.completion_total * 100,
            2,
        )
        if self.completion_percent != expected_percent:
            raise ValueError("completion percentage does not match totals")
        if len({entry.catalog_key for entry in self.species}) != len(self.species):
            raise ValueError("player contains duplicate catalog entries")
        if self.completed_entries > self.completion_total:
            raise ValueError("completed entries exceed the catalog total")
        expected_completed = sum(
            entry.counts_toward_completion and entry.capture_count > 0
            for entry in self.species
        )
        expected_encountered = sum(entry.discovered for entry in self.species)
        expected_captures = sum(entry.capture_count for entry in self.species)
        expected_unmapped = sum(
            entry.catalog_status == "unmapped" for entry in self.species
        )
        if self.completed_entries != expected_completed:
            raise ValueError("completed entry total does not match species")
        if self.encountered_entries != expected_encountered:
            raise ValueError("encountered entry total does not match species")
        if self.total_captures != expected_captures:
            raise ValueError("capture total does not match species")
        if self.unmapped_species_count != expected_unmapped:
            raise ValueError("unmapped entry total does not match species")
        return self


class ArmorySnapshotImport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[2]
    snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    snapshot_created_at: datetime
    catalog_source_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    completion_total: int = Field(gt=0)
    players: list[ArmoryPlayerImport]

    @model_validator(mode="after")
    def validate_snapshot(self) -> "ArmorySnapshotImport":
        keys = [player.internal_player_key for player in self.players]
        if len(set(keys)) != len(keys):
            raise ValueError("snapshot contains duplicate players")
        if any(
            player.completion_total != self.completion_total
            for player in self.players
        ):
            raise ValueError("player completion total does not match catalog")
        if self.snapshot_created_at.tzinfo is None:
            raise ValueError("snapshot timestamp must include a timezone")
        return self


class ArmoryLeaderboardEntry(BaseModel):
    rank: int
    player_id: int
    display_name: str
    completed_entries: int
    completion_total: int
    completion_percent: float
    encountered_entries: int
    total_captures: int


class ArmoryLeaderboardResponse(BaseModel):
    available: bool
    generated_at: datetime
    snapshot_created_at: datetime | None = None
    completion_total: int | None = None
    players: list[ArmoryLeaderboardEntry]


class ArmorySpeciesProgress(BaseModel):
    catalog_key: str
    name: str
    paldeck_number: str | None = Field(
        default=None,
        pattern=r"^[0-9]+B?$",
        max_length=16,
    )
    capture_count: int
    discovered: bool
    counts_toward_completion: bool
    catalog_status: Literal["mapped", "unmapped"]


class ArmoryPlayerProfile(BaseModel):
    player_id: int
    display_name: str
    snapshot_created_at: datetime
    completed_entries: int
    completion_total: int
    completion_percent: float
    encountered_entries: int
    total_captures: int
    unmapped_species_count: int
    species: list[ArmorySpeciesProgress]
