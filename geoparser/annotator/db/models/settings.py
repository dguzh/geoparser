import typing as t
import uuid

from sqlalchemy import UUID, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

from geoparser.annotator.constants import DEFAULT_SESSION_SETTINGS

if t.TYPE_CHECKING:
    from geoparser.annotator.db.models.session import AnnotatorSession


class AnnotatorSessionSettingsBase(SQLModel):
    auto_close_annotation_modal: t.Optional[bool] = DEFAULT_SESSION_SETTINGS[
        "auto_close_annotation_modal"
    ]
    one_sense_per_discourse: t.Optional[bool] = DEFAULT_SESSION_SETTINGS[
        "one_sense_per_discourse"
    ]


class AnnotatorSessionSettings(AnnotatorSessionSettingsBase, table=True):
    __tablename__ = "annotatorsessionsettings"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("annotatorsession.id", ondelete="CASCADE"), nullable=False
        )
    )
    session: "AnnotatorSession" = Relationship(back_populates="settings")


class AnnotatorSessionSettingsCreate(AnnotatorSessionSettingsBase):
    pass


class AnnotatorSessionSettingsUpdate(SQLModel):
    id: uuid.UUID
    auto_close_annotation_modal: t.Optional[bool] = None
    one_sense_per_discourse: t.Optional[bool] = None
