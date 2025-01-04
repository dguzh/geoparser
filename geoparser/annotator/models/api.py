import typing as t

from pydantic import BaseModel, ConfigDict

from geoparser.constants import DEFAULT_SESSION_SETTINGS


class Annotation(BaseModel):
    start: int
    end: int
    text: t.Optional[str] = None
    loc_id: t.Optional[str] = None


class AnnotationEdit(BaseModel):
    old_start: int
    old_end: int
    old_text: t.Optional[str] = None
    new_start: int
    new_end: int
    new_text: str


class CandidatesGet(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    start: t.Optional[int] = 0
    end: t.Optional[int] = 0
    text: t.Optional[str] = ""
    query_text: t.Optional[str] = ""


class SessionSettings(BaseModel):
    auto_close_annotation_modal: bool = DEFAULT_SESSION_SETTINGS[
        "auto_close_annotation_modal"
    ]
    one_sense_per_discourse: bool = DEFAULT_SESSION_SETTINGS["one_sense_per_discourse"]
