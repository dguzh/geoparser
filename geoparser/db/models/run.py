import typing as t
import uuid
from datetime import datetime

from sqlalchemy import UUID, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.session import Session


class RunBase(SQLModel):
    """Base model for Run records"""

    module_name: str
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: t.Optional[datetime] = None
    status: str = "started"  # Possible values: "started", "completed", "failed"
    metadata: t.Optional[str] = None  # JSON string to store additional metadata


class Run(RunBase, table=True):
    """
    Run model for storing information about pipeline module executions.

    Each run represents a single execution of a module on a session.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("session.id", ondelete="CASCADE"), nullable=False
        )
    )
    session: "Session" = Relationship(back_populates="runs")


class RunCreate(RunBase):
    """Model for creating new Run records"""

    pass


class RunUpdate(SQLModel):
    """Model for updating Run records"""

    id: uuid.UUID
    module_name: t.Optional[str] = None
    completed_at: t.Optional[datetime] = None
    status: t.Optional[str] = None
    metadata: t.Optional[str] = None
