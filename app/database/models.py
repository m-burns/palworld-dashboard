from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class PlayerRecord(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    player_key: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    display_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    latest_level: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    highest_level: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

class PlayerSession(Base):
    __tablename__ = "player_sessions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    player_id: Mapped[int] = mapped_column(
        Integer,
        index=True,
        nullable=False,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    duration_seconds: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )


class ArmorySnapshot(Base):
    __tablename__ = "armory_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_sha256: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    snapshot_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    catalog_source_commit: Mapped[str] = mapped_column(String(64), nullable=False)
    completion_total: Mapped[int] = mapped_column(Integer, nullable=False)
    player_count: Mapped[int] = mapped_column(Integer, nullable=False)


class ArmoryPlayer(Base):
    __tablename__ = "armory_players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    internal_player_key: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class ArmoryPlayerName(Base):
    __tablename__ = "armory_player_names"

    player_id: Mapped[int] = mapped_column(
        ForeignKey("armory_players.id", ondelete="CASCADE"),
        primary_key=True,
    )
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class ArmoryPlayerSnapshot(Base):
    __tablename__ = "armory_player_snapshots"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "player_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("armory_snapshots.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    player_id: Mapped[int] = mapped_column(
        ForeignKey("armory_players.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    completed_entries: Mapped[int] = mapped_column(Integer, nullable=False)
    completion_total: Mapped[int] = mapped_column(Integer, nullable=False)
    completion_percent: Mapped[float] = mapped_column(Float, nullable=False)
    encountered_entries: Mapped[int] = mapped_column(Integer, nullable=False)
    total_captures: Mapped[int] = mapped_column(Integer, nullable=False)
    unmapped_species_count: Mapped[int] = mapped_column(Integer, nullable=False)


class ArmorySpeciesSnapshot(Base):
    __tablename__ = "armory_species_snapshots"
    __table_args__ = (
        UniqueConstraint("player_snapshot_id", "catalog_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("armory_player_snapshots.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    catalog_key: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    paldeck_number: Mapped[str | None] = mapped_column(String(16), nullable=True)
    capture_count: Mapped[int] = mapped_column(Integer, nullable=False)
    discovered: Mapped[bool] = mapped_column(Boolean, nullable=False)
    counts_toward_completion: Mapped[bool] = mapped_column(Boolean, nullable=False)
    catalog_status: Mapped[str] = mapped_column(String(16), nullable=False)
