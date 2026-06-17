"""Repository layer.

Abstract base classes define the contract (so PostgreSQL or another backend can
be dropped in); the SQLAlchemy implementations persist Pydantic models as JSON
payloads alongside queryable scalar columns.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy import delete, select

from folk.models.audit import AuditTrace
from folk.models.country import CountryRecord
from folk.models.enums import Dimension
from folk.models.evidence import DimensionEvidence
from folk.models.profile import CountryProfile
from folk.models.reference import VerifiedReference
from folk.storage.db import Database
from folk.storage.orm import (
    AuditORM,
    CheckpointORM,
    CountryORM,
    EvidenceORM,
    ProfileORM,
    ReferenceORM,
    ValidationORM,
)


# --------------------------------------------------------------------------- #
# Abstract contracts
# --------------------------------------------------------------------------- #
class CountryRepository(ABC):
    @abstractmethod
    def upsert(self, record: CountryRecord) -> None: ...
    @abstractmethod
    def get(self, iso3: str) -> CountryRecord | None: ...
    @abstractmethod
    def all(self) -> list[CountryRecord]: ...


class ProfileRepository(ABC):
    @abstractmethod
    def upsert(self, profile: CountryProfile) -> None: ...
    @abstractmethod
    def get(self, iso3: str) -> CountryProfile | None: ...
    @abstractmethod
    def all(self) -> list[CountryProfile]: ...
    @abstractmethod
    def finalized_vectors(self, exclude_iso3: str | None = None) -> list[dict[str, Any]]: ...
    @abstractmethod
    def review_queue(self) -> list[CountryProfile]: ...
    @abstractmethod
    def count(self) -> int: ...
    @abstractmethod
    def exists(self, iso3: str) -> bool: ...


class EvidenceRepository(ABC):
    @abstractmethod
    def save(self, iso3: str, evidence: list[DimensionEvidence]) -> None: ...
    @abstractmethod
    def get(self, iso3: str) -> list[DimensionEvidence]: ...


class ReferenceRepository(ABC):
    @abstractmethod
    def add_many(self, refs: list[VerifiedReference]) -> None: ...
    @abstractmethod
    def library(self) -> list[VerifiedReference]: ...


class ValidationRepository(ABC):
    @abstractmethod
    def save(self, scope: str, payload: dict, iso3: str | None = None) -> None: ...
    @abstractmethod
    def all(self, scope: str | None = None) -> list[dict]: ...


class AuditRepository(ABC):
    @abstractmethod
    def upsert(self, trace: AuditTrace) -> None: ...
    @abstractmethod
    def get(self, iso3: str) -> AuditTrace | None: ...


class CheckpointRepository(ABC):
    @abstractmethod
    def set(self, key: str, value: dict) -> None: ...
    @abstractmethod
    def get(self, key: str) -> dict | None: ...


# --------------------------------------------------------------------------- #
# SQLAlchemy implementations
# --------------------------------------------------------------------------- #
class SqlCountryRepository(CountryRepository):
    def __init__(self, db: Database) -> None:
        self.db = db

    def upsert(self, record: CountryRecord) -> None:
        with self.db.session() as s:
            obj = s.get(CountryORM, record.iso3)
            payload = record.model_dump(mode="json")
            if obj is None:
                s.add(
                    CountryORM(
                        iso3=record.iso3,
                        country=record.country,
                        region=record.region,
                        record_type=record.record_type.value,
                        data_status=record.data_status.value,
                        payload=payload,
                    )
                )
            else:
                obj.country = record.country
                obj.region = record.region
                obj.record_type = record.record_type.value
                obj.data_status = record.data_status.value
                obj.payload = payload

    def get(self, iso3: str) -> CountryRecord | None:
        with self.db.session() as s:
            obj = s.get(CountryORM, iso3)
            return CountryRecord.model_validate(obj.payload) if obj else None

    def all(self) -> list[CountryRecord]:
        with self.db.session() as s:
            rows = s.execute(select(CountryORM)).scalars().all()
            return [CountryRecord.model_validate(r.payload) for r in rows]


class SqlProfileRepository(ProfileRepository):
    def __init__(self, db: Database) -> None:
        self.db = db

    def upsert(self, profile: CountryProfile) -> None:
        with self.db.session() as s:
            obj = s.get(ProfileORM, profile.iso3)
            scores = {d: (profile.final_scores[d].score if d in profile.final_scores else None)
                      for d in Dimension}
            payload = profile.model_dump(mode="json")
            fields = dict(
                country=profile.country,
                region=profile.region,
                record_type=profile.record_type.value,
                d1=scores[Dimension.D1],
                d2=scores[Dimension.D2],
                d3=scores[Dimension.D3],
                d4=scores[Dimension.D4],
                requires_human_review=profile.requires_human_review,
                payload=payload,
            )
            if obj is None:
                s.add(ProfileORM(iso3=profile.iso3, **fields))
            else:
                for k, v in fields.items():
                    setattr(obj, k, v)

    def get(self, iso3: str) -> CountryProfile | None:
        with self.db.session() as s:
            obj = s.get(ProfileORM, iso3)
            return CountryProfile.model_validate(obj.payload) if obj else None

    def all(self) -> list[CountryProfile]:
        with self.db.session() as s:
            rows = s.execute(select(ProfileORM)).scalars().all()
            return [CountryProfile.model_validate(r.payload) for r in rows]

    def finalized_vectors(self, exclude_iso3: str | None = None) -> list[dict[str, Any]]:
        """Return [{iso3, country, d1..d4}] for countries that have all four scores."""
        with self.db.session() as s:
            rows = s.execute(select(ProfileORM)).scalars().all()
            out: list[dict[str, Any]] = []
            for r in rows:
                if r.iso3 == exclude_iso3:
                    continue
                if None in (r.d1, r.d2, r.d3, r.d4):
                    continue
                out.append({"iso3": r.iso3, "country": r.country,
                            "d1": r.d1, "d2": r.d2, "d3": r.d3, "d4": r.d4})
            return out

    def review_queue(self) -> list[CountryProfile]:
        with self.db.session() as s:
            rows = s.execute(
                select(ProfileORM).where(ProfileORM.requires_human_review.is_(True))
            ).scalars().all()
            return [CountryProfile.model_validate(r.payload) for r in rows]

    def count(self) -> int:
        with self.db.session() as s:
            return len(s.execute(select(ProfileORM.iso3)).scalars().all())

    def exists(self, iso3: str) -> bool:
        with self.db.session() as s:
            return s.get(ProfileORM, iso3) is not None


class SqlEvidenceRepository(EvidenceRepository):
    def __init__(self, db: Database) -> None:
        self.db = db

    def save(self, iso3: str, evidence: list[DimensionEvidence]) -> None:
        with self.db.session() as s:
            s.execute(delete(EvidenceORM).where(EvidenceORM.iso3 == iso3))
            for de in evidence:
                s.add(EvidenceORM(iso3=iso3, dimension=de.dimension.value,
                                  payload=de.model_dump(mode="json")))

    def get(self, iso3: str) -> list[DimensionEvidence]:
        with self.db.session() as s:
            rows = s.execute(select(EvidenceORM).where(EvidenceORM.iso3 == iso3)).scalars().all()
            return [DimensionEvidence.model_validate(r.payload) for r in rows]


class SqlReferenceRepository(ReferenceRepository):
    def __init__(self, db: Database) -> None:
        self.db = db

    def add_many(self, refs: list[VerifiedReference]) -> None:
        with self.db.session() as s:
            for ref in refs:
                key = ref.dedup_key
                obj = s.get(ReferenceORM, key)
                if obj is None:
                    s.add(ReferenceORM(
                        dedup_key=key, ref_id=ref.ref_id or key, citation=ref.citation,
                        source_type=ref.source_type.value, url_or_doi=ref.url_or_doi,
                        verified=ref.verified, payload=ref.model_dump(mode="json"),
                    ))

    def library(self) -> list[VerifiedReference]:
        with self.db.session() as s:
            rows = s.execute(select(ReferenceORM)).scalars().all()
            return [VerifiedReference.model_validate(r.payload) for r in rows]


class SqlValidationRepository(ValidationRepository):
    def __init__(self, db: Database) -> None:
        self.db = db

    def save(self, scope: str, payload: dict, iso3: str | None = None) -> None:
        with self.db.session() as s:
            s.add(ValidationORM(iso3=iso3, scope=scope, payload=payload))

    def all(self, scope: str | None = None) -> list[dict]:
        with self.db.session() as s:
            stmt = select(ValidationORM)
            if scope is not None:
                stmt = stmt.where(ValidationORM.scope == scope)
            return [r.payload for r in s.execute(stmt).scalars().all()]


class SqlAuditRepository(AuditRepository):
    def __init__(self, db: Database) -> None:
        self.db = db

    def upsert(self, trace: AuditTrace) -> None:
        with self.db.session() as s:
            obj = s.get(AuditORM, trace.iso3)
            payload = trace.model_dump(mode="json")
            if obj is None:
                s.add(AuditORM(iso3=trace.iso3, payload=payload))
            else:
                obj.payload = payload

    def get(self, iso3: str) -> AuditTrace | None:
        with self.db.session() as s:
            obj = s.get(AuditORM, iso3)
            return AuditTrace.model_validate(obj.payload) if obj else None


class SqlCheckpointRepository(CheckpointRepository):
    def __init__(self, db: Database) -> None:
        self.db = db

    def set(self, key: str, value: dict) -> None:
        with self.db.session() as s:
            obj = s.get(CheckpointORM, key)
            if obj is None:
                s.add(CheckpointORM(key=key, value=value))
            else:
                obj.value = value

    def get(self, key: str) -> dict | None:
        with self.db.session() as s:
            obj = s.get(CheckpointORM, key)
            return obj.value if obj else None


class Repositories:
    """Convenience bundle wiring all repositories to one Database."""

    def __init__(self, db: Database | None = None) -> None:
        self.db = db or Database()
        self.db.create_all()
        self.countries = SqlCountryRepository(self.db)
        self.profiles = SqlProfileRepository(self.db)
        self.evidence = SqlEvidenceRepository(self.db)
        self.references = SqlReferenceRepository(self.db)
        self.validations = SqlValidationRepository(self.db)
        self.audits = SqlAuditRepository(self.db)
        self.checkpoints = SqlCheckpointRepository(self.db)
