import typing as t
import uuid

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


class BaseResponse(BaseModel):
    status: t.Optional[str] = "success"
    message: t.Optional[str] = None


class LegacyFilesResponse(BaseResponse):
    files_found: int = 0
    files_loaded: int = 0
    files_failed: list[str] = []


class ParsingResponse(BaseResponse):
    parsed: bool


class PreAnnotatedTextResponse(BaseResponse):
    pre_annotated_text: str


class ProgressResponse(BaseResponse):
    filename: str
    doc_index: int
    doc_id: uuid.UUID
    annotated_toponyms: int
    total_toponyms: int
    progress_percentage: float
