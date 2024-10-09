import os
import re
import typing as t

import geopandas as gpd
import pandas as pd

from geoparser.gazetteer import LocalDBGazetteer


class SwissNames3D(LocalDBGazetteer):
    def __init__(self):
        super().__init__("swissnames3d")
        self.location_description_template = lambda x: (
            f'{x["NAME"] if x["NAME"] else ""}'
            f'{" (" + x["OBJEKTART"] + ")" if x["OBJEKTART"] else ""}'
            f'{" in" if any((x["GEMEINDE_NAME"], x["BEZIRK_NAME"], x["KANTON_NAME"])) else ""}'
            f'{" " + x["GEMEINDE_NAME"] + "," if x["GEMEINDE_NAME"] else ""}'
            f'{" " + x["BEZIRK_NAME"] + "," if x["BEZIRK_NAME"] else ""}'
            f'{" " + x["KANTON_NAME"] if x["KANTON_NAME"] else ""}'
        ).strip(" ,")

    def read_file(
        self,
        file_path: str,
        columns: list[str] = None,
        skiprows: t.Union[int, list[int], t.Callable] = None,
        chunksize: int = 100000,
    ) -> t.Tuple[t.Iterator[pd.DataFrame], int]:

        gdf = gpd.read_file(file_path)
        df = pd.DataFrame(gdf)
        df = df[columns]

        chunks = [df]
        return (chunk for chunk in chunks), 1

    @LocalDBGazetteer.close
    @LocalDBGazetteer.commit
    @LocalDBGazetteer.connect
    def populate_locations_table(self):
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
                return geometry.x, geometry.y
            else:
                centroid = geometry.centroid
                return centroid.x, centroid.y

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

        locations_gdf.to_sql("locations", self.conn, if_exists="append", index=False)
