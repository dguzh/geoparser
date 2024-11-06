import typing as t

from pydantic import BaseModel


class Column(BaseModel):
    name: str
    type: str
    primary: bool = False


class ToponymColumn(BaseModel):
    name: str
    separator: t.Optional[str] = None
    geoqualifier_pattern: t.Optional[str] = None


class LocationCoordinates(BaseModel):
    x_column: str
    y_column: str
    crs: str


class GazetteerData(BaseModel):
    name: str
    url: str
    extracted_files: list[str]
    columns: list[Column]
    toponym_columns: list[ToponymColumn] = []
    skiprows: t.Optional[int] = None


class GazetteerConfig(BaseModel):
    name: str
    location_identifier: str
    location_coordinates: LocationCoordinates
    location_columns: list[Column]
    data: list[GazetteerData]
