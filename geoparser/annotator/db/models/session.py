from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from geoparser.annotator.db.models.base import Base


class Session(Base):
    __tablename__ = "sessions"

    session_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    last_updated: Mapped[datetime] = mapped_column(DateTime)
    gazetteer: Mapped[str] = mapped_column(String)
    settings: Mapped["SessionSettings"] = relationship(back_populates="session")
    documents: Mapped[list["Document"]] = relationship(back_populates="session")
