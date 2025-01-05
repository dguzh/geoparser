from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from geoparser.annotator.db.models.base import Base


class Toponym(Base):
    __tablename__ = "toponyms"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    document: Mapped["Document"] = relationship(back_populates="toponyms")
    text: Mapped[str] = mapped_column(String)
    start: Mapped[int] = mapped_column(Integer)
    end: Mapped[int] = mapped_column(Integer)
    loc_id: Mapped[str] = mapped_column(String)
