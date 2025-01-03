from pydantic import BaseModel, ConfigDict

from geoparser.constants import DEFAULT_SESSION_SETTINGS


class Annotation(BaseModel):
    start: int
    end: int
    text: str | None
    loc_id: str | None = None


class AnnotationEdit(BaseModel):
    old_start: int
    old_end: int
    old_text: str | None
    new_start: int
    new_end: int
    new_text: str


class CandidatesGet(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    start: int | None = 0
    end: int | None = 0
    toponym_text: str | None = ""
    query_text: str | None = ""


class SessionSettings(BaseModel):
    auto_close_annotation_modal: bool = DEFAULT_SESSION_SETTINGS[
        "auto_close_annotation_modal"
    ]
    one_sense_per_discourse: bool = DEFAULT_SESSION_SETTINGS["one_sense_per_discourse"]
