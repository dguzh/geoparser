import pandas as pd
import pytest

from geoparser.swissnames3d import SwissNames3D
from geoparser.tests.utils import get_static_test_file


@pytest.fixture(scope="session")
def test_chunk_shp() -> pd.DataFrame:
    data = {
        "UUID": ["{C3DF411C-0083-494F-8FF6-B2BB0B8AB2B2}"],
        "OBJEKTART": ["Haltestelle Bahn"],
        "OBJEKTKLAS": ["TLM_HALTESTELLE"],
        "HOEHE": [-999998.0000000001],
        "GEBAEUDENU": ["k_W"],
        "NAME_UUID": ["{2B6C2710-CD80-47B1-B9B7-9C01BCD35EAF}"],
        "NAME": ["St. Gallen Marktplatz"],
        "STATUS": ["offiziell"],
        "SPRACHCODE": ["Hochdeutsch inkl. Lokalsprachen"],
        "NAMEN_TYP": ["einfacher Name"],
        "NAMENGRUPP": [None],
    }
    return pd.DataFrame.from_dict(data)


@pytest.mark.parametrize(
    "location,expected",
    [
        (  # base case
            {
                "NAME": "Burg im Leimental",
                "OBJEKTART": "Ortschaft",
                "GEMEINDE_NAME": "Burg im Leimental",
                "BEZIRK_NAME": "Laufen",
                "KANTON_NAME": "Basel-Landschaft",
            },
            "Burg im Leimental (Ortschaft) in Burg im Leimental, Laufen, Basel-Landschaft",
        ),
        (  # Kanton can be missing
            {
                "NAME": "Burg im Leimental",
                "OBJEKTART": "Ortschaft",
                "GEMEINDE_NAME": "Burg im Leimental",
                "BEZIRK_NAME": "Laufen",
            },
            "Burg im Leimental (Ortschaft) in Burg im Leimental, Laufen",
        ),
        (  # Bezirk can be missing
            {
                "NAME": "Burg im Leimental",
                "OBJEKTART": "Ortschaft",
                "GEMEINDE_NAME": "Burg im Leimental",
                "KANTON_NAME": "Basel-Landschaft",
            },
            "Burg im Leimental (Ortschaft) in Burg im Leimental, Basel-Landschaft",
        ),
        (  # Gemeinde can be missing
            {
                "NAME": "Burg im Leimental",
                "OBJEKTART": "Ortschaft",
                "BEZIRK_NAME": "Laufen",
                "KANTON_NAME": "Basel-Landschaft",
            },
            "Burg im Leimental (Ortschaft) in Laufen, Basel-Landschaft",
        ),
    ],
)
def test_create_location_description_base(
    swissnames3d_patched: SwissNames3D, location: dict, expected: str
):
    actual = swissnames3d_patched.create_location_description(location)
    assert actual == expected


@pytest.mark.parametrize(
    "location,expected",
    [
        (  # Kantons are not part of any further administrative divisions
            {
                "NAME": "Zürich",
                "OBJEKTART": "Kanton",
                "KANTON_NAME": "Zürich",
            },
            "Zürich (Kanton)",
        ),
        (  # description for Kantosn will not include Bezirk and Gemeinde even if part of location
            {
                "NAME": "Zürich",
                "OBJEKTART": "Kanton",
                "GEMEINDE_NAME": "asdf",
                "BEZIRK_NAME": "asdf",
                "KANTON_NAME": "Zürich",
            },
            "Zürich (Kanton)",
        ),
        (  # Bezirks are only part of a Kanton
            {
                "NAME": "Laufen",
                "OBJEKTART": "Bezirk",
                "KANTON_NAME": "Basel-Landschaft",
            },
            "Laufen (Bezirk) in Basel-Landschaft",
        ),
        (  # description for Bezirk will not include Bezirk and Gemeinde even if part of location
            {
                "NAME": "Laufen",
                "OBJEKTART": "Bezirk",
                "GEMEINDE_NAME": "asdf",
                "BEZIRK_NAME": "Laufen",
                "KANTON_NAME": "Basel-Landschaft",
            },
            "Laufen (Bezirk) in Basel-Landschaft",
        ),
        (  # Gemeindes are only part of a Kanton and a Bezirk
            {
                "NAME": "Burg im Leimental",
                "OBJEKTART": "Gemeindegebiet",
                "BEZIRK_NAME": "Laufen",
                "KANTON_NAME": "Basel-Landschaft",
            },
            "Burg im Leimental (Gemeindegebiet) in Laufen, Basel-Landschaft",
        ),
        (  # description for Gemeindes will not include Gemeinde even if part of location
            {
                "NAME": "Burg im Leimental",
                "OBJEKTART": "Gemeindegebiet",
                "GEMEINDE_NAME": "Burg im Leimental",
                "BEZIRK_NAME": "Laufen",
                "KANTON_NAME": "Basel-Landschaft",
            },
            "Burg im Leimental (Gemeindegebiet) in Laufen, Basel-Landschaft",
        ),
    ],
)
def test_create_location_description_divisions(
    swissnames3d_patched: SwissNames3D, location: dict, expected: str
):
    actual = swissnames3d_patched.create_location_description(location)
    assert actual == expected


def test_read_file(swissnames3d_patched: SwissNames3D, test_chunk_shp: pd.DataFrame):
    file = get_static_test_file("minimal.shp")
    columns = [
        "UUID",
        "OBJEKTART",
        "OBJEKTKLAS",
        "HOEHE",
        "GEBAEUDENU",
        "NAME_UUID",
        "NAME",
        "STATUS",
        "SPRACHCODE",
        "NAMEN_TYP",
        "NAMENGRUPP",
    ]
    file_content, n_chunks = swissnames3d_patched.read_file(
        file,
        columns,
    )
    file_content = list(file_content)
    assert len(file_content) == n_chunks
    assert file_content[0].equals(test_chunk_shp)
