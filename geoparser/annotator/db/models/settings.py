import typing as t
import uuid

from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.annotator.db.models.session import Session


class SessionSettingsBase(SQLModel):
    auto_close_annotation_modal: bool
    one_sense_per_discourse: bool


class SessionSettings(SessionSettingsBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key="session.id")
    session: t.Optional["Session"] = Relationship(back_populates="settings")


class SessionSettingsCreate(SessionSettingsBase):
    pass


class SessionSettingsGet(SessionSettingsBase):
    id: uuid.UUID


class SessionSettingsUpdate(SessionSettingsGet):
    auto_close_annotation_modal: t.Optional[bool]
    one_sense_per_discourse: t.Optional[bool]
