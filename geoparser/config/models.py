import typing as t

from pydantic import BaseModel


class Column(BaseModel):
    name: str
    type: str
    primary: bool = False


# class VirtualTable(BaseModel):
#     name: str
#     using: t.Optional[str] = None
#     args: list[str]
#     kwargs: dict[str, str]


class NameField(BaseModel):
    field: str
    split: bool
    separator: t.Optional[str] = None


class GazetteerData(BaseModel):
    name: str
    url: str
    extracted_file: str
    columns: list[Column]
    # virtual_tables: list[VirtualTable] = []
    name_fields: list[NameField] = []
    skiprows: t.Optional[int] = None


class GazetteerConfig(BaseModel):
    name: str
    id_field: str
    data: list[GazetteerData]
