from __future__ import annotations

import os
import re
import typing as t

import geopandas as gpd
import pandas as pd

from geoparser.gazetteers.gazetteer import LocalDBGazetteer


class SwissNames3D(LocalDBGazetteer):
    """Gazetteer implementation for SwissNames3D data."""

    def __init__(self):
        """
        Initialize the SwissNames3D gazetteer.

        Inherits from LocalDBGazetteer and sets the gazetteer name to 'swissnames3d'.
        """
        super().__init__("swissnames3d")

    def _create_location_description(self, location: t.Dict[str, t.Any]) -> str:
        """
        Create a textual description for a location using SwissNames3D data.

        Args:
            location (Dict[str, Any]): Dictionary containing location attributes.

        Returns:
            str: Textual description of the location.
        """
        name = location.get("NAME") or ""
        objektart = f' ({location["OBJEKTART"]})' if location.get("OBJEKTART") else ""

        in_condition = any(
            [
                location.get("GEMEINDE_NAME")
                and location.get("OBJEKTART")
                not in [
                    "Gemeindegebiet",
                    "Bezirk",
                    "Kanton",
                ],
                location.get("BEZIRK_NAME")
                and location.get("OBJEKTART")
                not in [
                    "Bezirk",
                    "Kanton",
                ],
                location.get("KANTON_NAME")
                and location.get("OBJEKTART")
                not in [
                    "Kanton",
                ],
            ]
        )
        in_text = " in" if in_condition else ""

        gemeinde = (
            f' {location.get("GEMEINDE_NAME")},'
            if location.get("GEMEINDE_NAME")
            and location.get("OBJEKTART")
            not in [
                "Gemeindegebiet",
                "Bezirk",
                "Kanton",
            ]
            else ""
        )

        bezirk = (
            f' {location.get("BEZIRK_NAME")},'
            if location.get("BEZIRK_NAME")
            and location.get("OBJEKTART")
            not in [
                "Bezirk",
                "Kanton",
            ]
            else ""
        )

        kanton = (
            f' {location.get("KANTON_NAME")}'
            if location.get("KANTON_NAME")
            and location.get("OBJEKTART")
            not in [
                "Kanton",
            ]
            else ""
        )

        return f"{name}{objektart}{in_text}{gemeinde}{bezirk}{kanton}".strip(" ,")

    def _read_file(
        self,
        file_path: str,
        columns: t.Optional[t.List[str]] = None,
        skiprows: t.Optional[t.Union[int, t.List[int], t.Callable]] = None,
        chunksize: int = 100000,
    ) -> t.Tuple[t.Iterator[pd.DataFrame], int]:
        """
        Read a SwissNames3D data file and yield data in chunks.

        Args:
            file_path (str): Path to the data file.
            columns (Optional[List[str]], optional): List of column names.
            skiprows (Optional[Union[int, List[int], Callable]], optional): Rows to skip.
            chunksize (int, optional): Number of rows per chunk.

        Returns:
            Tuple[Iterator[pd.DataFrame], int]: Iterator over DataFrame chunks and total number of chunks.
        """
        gdf = gpd.read_file(file_path)
        df = pd.DataFrame(gdf)
        df = df[columns]

        chunks = [df]
        return (chunk for chunk in chunks), 1

    @LocalDBGazetteer.close
    @LocalDBGazetteer.commit
    @LocalDBGazetteer.connect
    def _populate_locations_table(self) -> None:
        """
        Populate the 'locations' table with data from SwissNames3D datasets.

        Processes geographical data and inserts it into the 'locations' table.
        """
        data_frames = []

        for dataset in self.config.data:
            file_path = os.path.join(self.data_dir, dataset.extracted_files[0])
            gdf = gpd.read_file(file_path)
            data_frames.append(gdf)

        locations_gdf = gpd.GeoDataFrame(pd.concat(data_frames, ignore_index=True))

        gemeinde_path = os.path.join(
            self.data_dir, "swissBOUNDARIES3D_1_5_TLM_HOHEITSGEBIET.shp"
        )
        bezirk_path = os.path.join(
            self.data_dir, "swissBOUNDARIES3D_1_5_TLM_BEZIRKSGEBIET.shp"
        )
        kanton_path = os.path.join(
            self.data_dir, "swissBOUNDARIES3D_1_5_TLM_KANTONSGEBIET.shp"
        )

        gemeinde_gdf = gpd.read_file(gemeinde_path)
        bezirk_gdf = gpd.read_file(bezirk_path)
        kanton_gdf = gpd.read_file(kanton_path)

        gemeinde_gdf["geometry"] = gemeinde_gdf["geometry"].buffer(200)
        bezirk_gdf["geometry"] = bezirk_gdf["geometry"].buffer(200)
        kanton_gdf["geometry"] = kanton_gdf["geometry"].buffer(200)

        locations_gdf = gpd.sjoin(
            locations_gdf,
            gemeinde_gdf[["UUID", "NAME", "geometry"]],
            how="left",
            predicate="within",
            lsuffix=None,
            rsuffix="gemeinde",
        )
        locations_gdf = gpd.sjoin(
            locations_gdf,
            bezirk_gdf[["UUID", "NAME", "geometry"]],
            how="left",
            predicate="within",
            lsuffix=None,
            rsuffix="bezirk",
        )
        locations_gdf = gpd.sjoin(
            locations_gdf,
            kanton_gdf[["UUID", "NAME", "geometry"]],
            how="left",
            predicate="within",
            lsuffix=None,
            rsuffix="kanton",
        )

        def extract_coordinates(geometry):
            if geometry.geom_type == "Point":
                return int(geometry.x), int(geometry.y)
            else:
                centroid = geometry.centroid
                return int(centroid.x), int(centroid.y)

        locations_gdf["E"], locations_gdf["N"] = zip(
            *locations_gdf["geometry"].apply(extract_coordinates)
        )

        locations_gdf.rename(
            columns={
                "UUID": "UUID",
                "NAME": "NAME",
                "OBJEKTART": "OBJEKTART",
                "E": "E",
                "N": "N",
                "UUID_gemeinde": "GEMEINDE_UUID",
                "NAME_gemeinde": "GEMEINDE_NAME",
                "UUID_bezirk": "BEZIRK_UUID",
                "NAME_bezirk": "BEZIRK_NAME",
                "UUID_kanton": "KANTON_UUID",
                "NAME_kanton": "KANTON_NAME",
            },
            inplace=True,
        )

        locations_gdf = locations_gdf[
            [
                "UUID",
                "NAME",
                "OBJEKTART",
                "E",
                "N",
                "GEMEINDE_UUID",
                "GEMEINDE_NAME",
                "BEZIRK_UUID",
                "BEZIRK_NAME",
                "KANTON_UUID",
                "KANTON_NAME",
            ]
        ]

        locations_gdf = (
            locations_gdf.groupby("UUID")
            .agg(
                {
                    "NAME": lambda x: "/".join(sorted(set(x))),
                    "OBJEKTART": "first",
                    "E": "first",
                    "N": "first",
                    "GEMEINDE_UUID": "first",
                    "GEMEINDE_NAME": "first",
                    "BEZIRK_UUID": "first",
                    "BEZIRK_NAME": "first",
                    "KANTON_UUID": "first",
                    "KANTON_NAME": "first",
                }
            )
            .reset_index()
        )

        locations_gdf.to_sql(
            "locations", self._local.conn, if_exists="append", index=False
        )
