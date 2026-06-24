from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def uuid_column() -> Uuid:
    return Uuid(as_uuid=True)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False),
        nullable=True,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        uuid_column(),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    plan: Mapped[str] = mapped_column(String(20), nullable=False, default="free")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )

    users: Mapped[list[User]] = relationship(back_populates="tenant")
    contracts: Mapped[list[Contract]] = relationship(back_populates="tenant")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        uuid_column(),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        uuid_column(),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="member")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(back_populates="users")
    contracts: Mapped[list[Contract]] = relationship(back_populates="user")


class Contract(Base, TimestampMixin):
    __tablename__ = "contracts"

    id: Mapped[uuid.UUID] = mapped_column(
        uuid_column(),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        uuid_column(),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        uuid_column(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    page_count: Mapped[int | None] = mapped_column(nullable=True)
    contract_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="uploaded")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    draft_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    draft_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True,
    )

    tenant: Mapped[Tenant] = relationship(back_populates="contracts")
    user: Mapped[User] = relationship(back_populates="contracts")
    reviews: Mapped[list[Review]] = relationship(back_populates="contract")


class Review(Base, TimestampMixin):
    __tablename__ = "reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        uuid_column(),
        primary_key=True,
        default=uuid.uuid4,
    )
    contract_id: Mapped[uuid.UUID] = mapped_column(
        uuid_column(),
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        uuid_column(),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        uuid_column(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="queued",
    )
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_stage: Mapped[str | None] = mapped_column(String(30), nullable=True)
    report_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    schema_version: Mapped[str] = mapped_column(
        String(20), nullable=False, default="1.0",
    )
    reviewed_draft: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True,
    )

    contract: Mapped[Contract] = relationship(back_populates="reviews")


class LawArticle(Base):
    """法律法规条文表，支持 PostgreSQL 全文检索。"""

    __tablename__ = "law_articles"

    id: Mapped[uuid.UUID] = mapped_column(
        uuid_column(),
        primary_key=True,
        default=uuid.uuid4,
    )
    law_name: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True,
    )
    article_number: Mapped[str] = mapped_column(
        String(50), nullable=False,
    )
    article_title: Mapped[str | None] = mapped_column(
        String(300), nullable=True,
    )
    full_text: Mapped[str] = mapped_column(Text, nullable=False)
    keywords: Mapped[str | None] = mapped_column(Text, nullable=True)
    chapter: Mapped[str | None] = mapped_column(String(100), nullable=True)
    section: Mapped[str | None] = mapped_column(String(100), nullable=True)
    effective_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="现行有效",
    )
    # PostgreSQL 全文检索向量（自动生成）
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)

    __table_args__ = (
        Index("idx_law_search_vector", "search_vector", postgresql_using="gin"),
        Index("idx_law_name_number", "law_name", "article_number", unique=True),
    )
