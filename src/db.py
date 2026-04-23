"""SQLAlchemy async database models and session management.

Provides queryable storage for experiments, human annotations, and async
job tracking — complementing the git snapshot system which stays as the
reproducibility record.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    event,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# ---------------------------------------------------------------------------
# Engine + session factory (configured at startup via init_db)
# ---------------------------------------------------------------------------

_engine: Any = None
_session_factory: Any = None


async def init_db(database_url: str) -> None:
    """Create tables and initialise the async engine / session factory."""
    global _engine, _session_factory

    # SQLite needs special connect args for async
    connect_args: dict[str, Any] = {}
    if "sqlite" in database_url:
        connect_args = {"check_same_thread": False}

    _engine = create_async_engine(
        database_url,
        echo=False,
        connect_args=connect_args,
    )

    # Enable WAL mode for SQLite (much better concurrent read performance)
    if "sqlite" in database_url:
        @event.listens_for(_engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection: Any, _: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_session() -> AsyncSession:
    if _session_factory is None:
        raise RuntimeError("Database not initialised — call init_db() at startup")
    return _session_factory()


# ---------------------------------------------------------------------------
# ORM models
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    pass


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class ExperimentRow(Base):
    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    domain: Mapped[str] = mapped_column(String(200))
    subfield: Mapped[str] = mapped_column(String(200), default="")
    conjecture: Mapped[str] = mapped_column(Text)
    lean_code: Mapped[str] = mapped_column(Text, default="")
    is_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    proved: Mapped[bool] = mapped_column(Boolean, default=False)
    final_proof: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_used: Mapped[str] = mapped_column(String(100))
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    confidence_estimate: Mapped[float] = mapped_column(Float, default=0.5)
    novelty_score: Mapped[float] = mapped_column(Float, default=1.0)
    complexity_formalizability: Mapped[int] = mapped_column(Integer, default=3)
    complexity_proof_difficulty: Mapped[int] = mapped_column(Integer, default=3)
    proof_strategy: Mapped[str] = mapped_column(String(50), default="claude_standard")
    git_sha: Mapped[str | None] = mapped_column(String(40), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class AnnotationRow(Base):
    __tablename__ = "annotations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    experiment_id: Mapped[str] = mapped_column(String(36), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    interesting: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    correct_proof: Mapped[str | None] = mapped_column(Text, nullable=True)
    annotator: Mapped[str] = mapped_column(String(100), default="human")


class JobRow(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now)
    domain: Mapped[str] = mapped_column(String(200))
    n: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|running|done|error
    celery_task_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    result: Mapped[Any] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
