"""SQLAlchemy 2.0 ORM table definitions.

JSON payload columns hold the full Pydantic model; scalar columns mirror the
fields needed for queries (discrimination checks, library dedup, review queue).
Works on SQLite now and PostgreSQL later without change.
"""

from __future__ import annotations

from sqlalchemy import JSON, Boolean, Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CountryORM(Base):
    __tablename__ = "countries"

    iso3: Mapped[str] = mapped_column(String(3), primary_key=True)
    country: Mapped[str] = mapped_column(String)
    region: Mapped[str | None] = mapped_column(String, nullable=True)
    record_type: Mapped[str] = mapped_column(String)
    data_status: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSON)


class ProfileORM(Base):
    __tablename__ = "profiles"

    iso3: Mapped[str] = mapped_column(String(3), primary_key=True)
    country: Mapped[str] = mapped_column(String)
    region: Mapped[str | None] = mapped_column(String, nullable=True)
    record_type: Mapped[str] = mapped_column(String, index=True)
    d1: Mapped[int | None] = mapped_column(Integer, nullable=True)
    d2: Mapped[int | None] = mapped_column(Integer, nullable=True)
    d3: Mapped[int | None] = mapped_column(Integer, nullable=True)
    d4: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON)


class EvidenceORM(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    iso3: Mapped[str] = mapped_column(String(3), index=True)
    dimension: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSON)


class ReferenceORM(Base):
    __tablename__ = "references"

    dedup_key: Mapped[str] = mapped_column(String(32), primary_key=True)
    ref_id: Mapped[str | None] = mapped_column(String, nullable=True)
    citation: Mapped[str] = mapped_column(String)
    source_type: Mapped[str] = mapped_column(String)
    url_or_doi: Mapped[str | None] = mapped_column(String, nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    payload: Mapped[dict] = mapped_column(JSON)


class ValidationORM(Base):
    __tablename__ = "validations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    iso3: Mapped[str | None] = mapped_column(String(3), nullable=True, index=True)
    scope: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSON)


class AuditORM(Base):
    __tablename__ = "audit_traces"

    iso3: Mapped[str] = mapped_column(String(3), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)


class CheckpointORM(Base):
    __tablename__ = "checkpoints"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)


class MetricORM(Base):
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    iso3: Mapped[str | None] = mapped_column(String(3), nullable=True, index=True)
    role: Mapped[str | None] = mapped_column(String, nullable=True)
    provider: Mapped[str] = mapped_column(String)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    api_cost: Mapped[float] = mapped_column(Float, default=0.0)
    payload: Mapped[dict] = mapped_column(JSON)
