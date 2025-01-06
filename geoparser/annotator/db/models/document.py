from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from geoparser.annotator.db.models.base import Base


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("session_id", "doc_index", name="document_uniq"),
    )

    session_id: Mapped[int] = mapped_column(
        ForeignKey("sessions.session_id"), primary_key=True, index=True
    )
    session: Mapped["Session"] = relationship(back_populates="documents")
    doc_index: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String)
    spacy_model: Mapped[str] = mapped_column(String)
    spacy_applied: Mapped[bool] = mapped_column(Boolean)
    text: Mapped[str] = mapped_column(String)
    toponyms: Mapped[list["Toponym"]] = relationship(back_populates="document")
