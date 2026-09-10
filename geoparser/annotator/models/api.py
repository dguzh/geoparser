import uuid

from pydantic import BaseModel, ConfigDict


class AnnotationEdit(BaseModel):
    old_start: int
    old_end: int
    old_text: str | None = None
    new_start: int
    new_end: int
    new_text: str


class CandidatesGet(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    start: int | None = 0
    end: int | None = 0
    text: str | None = ""
    query_text: str | None = ""


class BaseResponse(BaseModel):
    status: str | None = "success"
    message: str | None = None


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
