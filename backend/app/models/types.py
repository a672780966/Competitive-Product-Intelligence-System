"""Type compatibility layer — uses PostgreSQL JSONB/UUID when available,
falls back to standard SQLAlchemy types for testing with SQLite.
"""

from __future__ import annotations

import uuid as _stdlib_uuid

from sqlalchemy import JSON, Uuid
from sqlalchemy.types import TypeDecorator


class GUID(TypeDecorator):
    """Platform-independent GUID type.

    Uses PostgreSQL's UUID type natively when available,
    falls back to a string representation for other databases.
    """

    impl = Uuid
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import UUID as PG_UUID
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(Uuid(as_uuid=True))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, _stdlib_uuid.UUID):
            return value
        return _stdlib_uuid.UUID(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, _stdlib_uuid.UUID):
            return value
        return _stdlib_uuid.UUID(value)


class JSONB(TypeDecorator):
    """Platform-independent 'JSONB' type.

    Uses PostgreSQL's JSONB natively, falls back to JSON for other databases.
    """

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
            return dialect.type_descriptor(PG_JSONB())
        return dialect.type_descriptor(JSON())
