import typing as t
from sqlalchemy import UniqueConstraint
from pydantic import field_validator
from pydantic_core import PydanticCustomError
from sqlmodel import Field, SQLModel, Relationship

from geoparser.annotator.db.models.toponym import Toponym


class Document(SQLModel, table=True):
    id: t.Optional[int] = Field(default=None, primary_key=True)
    session: t.Optional["Session"] = Relationship(back_populates="documents")
    doc_index: int
    filename: str
    spacy_model: str
    spacy_applied: t.Optional[bool] = False
    text: str
    toponyms: list[Toponym] = Relationship(back_populates="document")

    # @field_validator("toponyms", mode="after")
    # @classmethod
    # def sort_toponyms(cls, value: list[Toponym]) -> list[Toponym]:
    #     return sorted(value, key=lambda x: x.start)

    # @field_validator("toponyms", mode="after")
    # @classmethod
    # def overlapping_toponyms(cls, value: list[Toponym]) -> list[Toponym]:
    #     toponym_bigrams = [(value[i], value[i + 1]) for i in range(len(value) - 1)]
    #     for first, second in toponym_bigrams:
    #         if first.end >= second.start:
    #             raise PydanticCustomError(
    #                 "overlapping_toponyms",
    #                 "toponyms (start={start1}, end={end1}, text={text1}) and (start={start2}, end={end2}, text={text2}) are overlapping",
    #                 {
    #                     "start1": first.start,
    #                     "end1": first.end,
    #                     "text1": first.text,
    #                     "start2": second.start,
    #                     "end2": second.end,
    #                     "text2": second.text,
    #                 },
    #             )
    #     return value
