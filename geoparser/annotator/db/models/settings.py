from sqlalchemy import Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from geoparser.annotator.db.models.base import Base
from geoparser.constants import DEFAULT_SESSION_SETTINGS


class SessionSettings(Base):
    __tablename__ = "session_settings"

    id: Mapped[str] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.session_id"))
    session: Mapped["Session"] = relationship(back_populates="settings")
    auto_close_annotation_modal: Mapped[bool] = mapped_column(
        Boolean, default=DEFAULT_SESSION_SETTINGS["auto_close_annotation_modal"]
    )
    one_sense_per_discourse: Mapped[bool] = mapped_column(
        Boolean, default=DEFAULT_SESSION_SETTINGS["one_sense_per_discourse"]
    )
