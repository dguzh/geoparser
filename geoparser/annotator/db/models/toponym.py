import typing as t

from sqlmodel import Field, SQLModel, Relationship


class Toponym(SQLModel, table=True):
    id: t.Optional[int] = Field(default=None, primary_key=True)
    document: t.Optional["Document"] = Relationship(back_populates="toponyms")
    text: str
    start: int
    end: int
    loc_id: t.Optional[str] = ""
