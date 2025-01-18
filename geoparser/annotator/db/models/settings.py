import typing as t
import uuid

from sqlmodel import Field, Relationship, SQLModel, ForeignKey

from geoparser.constants import DEFAULT_SESSION_SETTINGS

if t.TYPE_CHECKING:
    from geoparser.annotator.db.models.session import Session


class SessionSettingsBase(SQLModel):
    auto_close_annotation_modal: bool = DEFAULT_SESSION_SETTINGS[
        "auto_close_annotation_modal"
    ]
    one_sense_per_discourse: bool = DEFAULT_SESSION_SETTINGS["one_sense_per_discourse"]


class SessionSettings(SessionSettingsBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session: t.Optional["Session"] = Relationship(
        back_populates="settings", sa_relationship=ForeignKey("session.id")
    )


class SessionSettingsCreate(SessionSettingsBase):
    pass


class SessionSettingsGet(SessionSettingsBase):
    id: uuid.UUID


class SessionSettingsUpdate(SessionSettingsGet):
    auto_close_annotation_modal: t.Optional[bool]
    one_sense_per_discourse: t.Optional[bool]
