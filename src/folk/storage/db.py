"""Database engine/session management."""

from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from folk.config import get_settings
from folk.storage.orm import Base


class Database:
    """Owns the SQLAlchemy engine and session factory.

    Swap to PostgreSQL by setting ``database_url`` to a postgresql:// URL - no
    other code changes required.
    """

    def __init__(self, url: str | None = None) -> None:
        settings = get_settings()
        if url is None:
            settings.ensure_dirs()
            url = settings.database_url
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        self.engine = create_engine(url, future=True, connect_args=connect_args)
        self._session_factory = sessionmaker(bind=self.engine, expire_on_commit=False, future=True)

    def create_all(self) -> None:
        Base.metadata.create_all(self.engine)

    def drop_all(self) -> None:
        Base.metadata.drop_all(self.engine)

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
