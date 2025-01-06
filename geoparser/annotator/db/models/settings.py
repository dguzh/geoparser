from pydantic import BaseModel
import typing as t
from sqlmodel import SQLModel, Field, Relationship
from geoparser.constants import DEFAULT_SESSION_SETTINGS


class SessionSettings(SQLModel, table=True):
    id: t.Optional[int] = Field(default=None, primary_key=True)
    session: t.Optional["Session"] = Relationship(back_populates="settings")
    auto_close_annotation_modal: bool = DEFAULT_SESSION_SETTINGS[
        "auto_close_annotation_modal"
    ]
    one_sense_per_discourse: bool = DEFAULT_SESSION_SETTINGS["one_sense_per_discourse"]
