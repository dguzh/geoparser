import typing as t

from pydantic import BaseModel, ConfigDict


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
