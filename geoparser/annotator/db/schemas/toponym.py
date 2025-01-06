import typing as t

from pydantic import BaseModel


class Toponym(BaseModel):
    text: str
    start: int
    end: int
    loc_id: t.Optional[str] = ""
