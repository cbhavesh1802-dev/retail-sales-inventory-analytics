from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Float, DateTime, Text, ForeignKey
from typing import Optional, List
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://localhost/adg_db")
engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class Repository(Base):
    __tablename__ = "repositories"
    id:         Mapped[int] = mapped_column(Integer, primary_key=True)
    owner:      Mapped[str] = mapped_column(String(100))
    name:       Mapped[str] = mapped_column(String(100))
    full_name:  Mapped[str] = mapped_column(String(200), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    evaluations: Mapped[List["Evaluation"]] = relationship(back_populates="repository")

class Evaluation(Base):
    __tablename__ = "evaluations"
    id:              Mapped[int]           = mapped_column(Integer, primary_key=True)
    repository_id:   Mapped[int]           = mapped_column(ForeignKey("repositories.id"))
    pr_number:       Mapped[int]           = mapped_column(Integer)
    pr_title:        Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    trust_score:     Mapped[int]           = mapped_column(Integer)
    decision:        Mapped[str]           = mapped_column(String(50))
    dependency_risk: Mapped[int]           = mapped_column(Integer, default=0)
    pr_size_risk:    Mapped[int]           = mapped_column(Integer, default=0)
    branch_age_risk: Mapped[int]           = mapped_column(Integer, default=0)
    rationale:       Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    additions:       Mapped[int]           = mapped_column(Integer, default=0)
    deletions:       Mapped[int]           = mapped_column(Integer, default=0)
    changed_files:   Mapped[int]           = mapped_column(Integer, default=0)
    evaluated_at:    Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    repository:      Mapped["Repository"]        = relationship(back_populates="evaluations")
    vulnerabilities: Mapped[List["Vulnerability"]] = relationship(back_populates="evaluation")

class Vulnerability(Base):
    __tablename__ = "vulnerabilities"
    id:            Mapped[int]           = mapped_column(Integer, primary_key=True)
    evaluation_id: Mapped[int]           = mapped_column(ForeignKey("evaluations.id"))
    package:       Mapped[str]           = mapped_column(String(200))
    version:       Mapped[str]           = mapped_column(String(50))
    severity:      Mapped[str]           = mapped_column(String(20))
    title:         Mapped[str]           = mapped_column(String(500))
    cve:           Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    cvss:          Mapped[float]         = mapped_column(Float, default=0.0)
    fix_version:   Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    evaluation:    Mapped["Evaluation"]  = relationship(back_populates="vulnerabilities")

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
