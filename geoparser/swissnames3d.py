import re
import typing as t
import geopandas as gpd
import pandas as pd
from geoparser.gazetteer import LocalDBGazetteer

class SwissNames3D(LocalDBGazetteer):
    def __init__(self):
        super().__init__("swissnames3d")
        self.location_description_template = "<NAME> (<OBJEKTART>) COND[in, any{<BEZIRK_NAME>, <KANTON_NAME>}] <BEZIRK_NAME>, <KANTON_NAME>"

    def read_file(
        self,
        file_path: str,
        columns: list[str] = None,
        skiprows: t.Union[int, list[int], t.Callable] = None,
        chunksize: int = 100000,
    ) -> t.Iterator[pd.DataFrame]:
        return self.read_shapefile(file_path, columns, chunksize)

    def read_shapefile(
        self,
        file_path: str,
        columns: list[str] = None,
        chunksize: int = 100000,
    ) -> t.Iterator[pd.DataFrame]:
        
        gdf = gpd.read_file(file_path)
        gdf = gdf.to_wkt()
        if columns:
            gdf = gdf[columns]
        
        total_rows = len(gdf)
        for i in range(0, total_rows, chunksize):
            yield gdf.iloc[i : i + chunksize]

    def query_candidates(
        self,
        toponym: str,
        country_filter: list[str] = None,
        feature_filter: list[str] = None,
    ) -> list[int]:

        toponym = re.sub(r"\"", "", toponym).strip()

        toponym = " ".join([f'"{word}"' for word in toponym.split()])

        location_identifier = self.config.location_identifier

        base_query = f"""
            WITH RankedMatches AS (
                SELECT
                    names_fts.{location_identifier},
                    bm25(names_fts) AS rank
                FROM names_fts
                WHERE names_fts MATCH ?
            ),
            MinRank AS (
                SELECT MIN(rank) AS MinRank FROM RankedMatches
            )
            SELECT {location_identifier}
            FROM RankedMatches
            WHERE RankedMatches.rank = (SELECT MinRank FROM MinRank)
        """

        where_clauses = []
        params = [toponym]

        # # Add country filter if provided
        # if country_filter:
        #     placeholders = ",".join(["?"] * len(country_filter))
        #     where_clauses.append(f"ac.country_code IN ({placeholders})")
        #     params.extend(country_filter)

        # # Add feature class filter if provided
        # if feature_filter:
        #     placeholders = ",".join(["?"] * len(feature_filter))
        #     where_clauses.append(f"ac.feature_class IN ({placeholders})")
        #     params.extend(feature_filter)

        # if where_clauses:
        #     base_query += " AND " + " AND ".join(where_clauses)

        # base_query += f" GROUP BY ac.{location_identifier}"

        result = self.execute_query(base_query, tuple(params))
        return [row[0] for row in result]

    def query_location_info():
        pass