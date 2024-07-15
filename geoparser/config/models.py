import typing as t

from pydantic import BaseModel


class Column(BaseModel):
    name: str
    type: str
    primary: bool = False


class VirtualTable(BaseModel):
    name: str
    using: t.Optional[str] = None
    args: list[str]
    kwargs: dict[str, str]


class GazetteerData(BaseModel):
    name: str
    url: str
    extracted_file: str
    columns: list[Column]
    virtual_tables: list[VirtualTable] = []
    skiprows: t.Optional[int] = None


class GazetteerConfig(BaseModel):
    name: str
    data: list[GazetteerData]
