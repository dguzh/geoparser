import pytest

from geoparser.swissnames3d import SwissNames3D


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
