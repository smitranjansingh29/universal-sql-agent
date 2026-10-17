from datetime import datetime
from sqlalchemy import (
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    LargeBinary,
    ForeignKey,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Connection(Base):
    __tablename__ = "connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dialect: Mapped[str] = mapped_column(String(50), nullable=False)
    url_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    date_column: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reference_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SchemaChunk(Base):
    __tablename__ = "schema_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    connection_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("connections.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # table | column | example
    table_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Embedding stored as JSON text for SQLite dev; we swap to vector(1536) on Postgres later
    embedding: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_edited: Mapped[bool] = mapped_column(Boolean, default=False)


class QueryHistory(Base):
    __tablename__ = "query_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    connection_id: Mapped[int] = mapped_column(Integer, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    sql: Mapped[str | None] = mapped_column(Text, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts: Mapped[int] = mapped_column(Integer, default=1)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    starred: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
