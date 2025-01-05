from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from geoparser.annotator.db.models.base import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    session: Mapped["Session"] = relationship(back_populates="documents")
    filename: Mapped[str] = mapped_column(String)
    spacy_model: Mapped[str] = mapped_column(String)
    spacy_applied: Mapped[bool] = mapped_column(Boolean)
    text: Mapped[str] = mapped_column(String)
    toponyms: Mapped[list["Toponym"]] = relationship(back_populates="document")
