"""
backend/models/__init__.py
SQLAlchemy ORM models for DevForge.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id         = Column(String, primary_key=True)
    idea       = Column(Text, nullable=False)
    status     = Column(String, default="IDLE")
    retries_plan     = Column(Integer, default=0)
    retries_test     = Column(Integer, default=0)
    retries_security = Column(Integer, default=0)
    human_approved_arch    = Column(Boolean, default=False)
    human_approved_release = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class SecurityFindingRecord(Base):
    __tablename__ = "security_findings"

    id          = Column(String, primary_key=True)   # "SEC-001"
    project_id  = Column(String, nullable=False)
    milestone_id = Column(String, nullable=False)
    severity    = Column(String, nullable=False)     # CRITICAL|HIGH|MEDIUM|LOW|INFO
    category    = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    file        = Column(String, nullable=False)
    line        = Column(Integer, nullable=False)
    cwe         = Column(String, nullable=False)
    status      = Column(String, default="OPEN")     # OPEN|FIXED
    evidence    = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentResultRecord(Base):
    __tablename__ = "agent_results"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    project_id       = Column(String, nullable=False)
    milestone_id     = Column(String, nullable=False)
    agent            = Column(String, nullable=False)
    status           = Column(String, nullable=False)
    summary          = Column(Text, nullable=True)
    duration_seconds = Column(Float, default=0.0)
    timestamp        = Column(DateTime, default=datetime.utcnow)
