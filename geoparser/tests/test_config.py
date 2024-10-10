import pydantic
import pytest

from geoparser.config import get_gazetteer_configs
from geoparser.config.models import (
    Column,
    GazetteerConfig,
    GazetteerData,
    ToponymColumn,
)
from geoparser.tests.utils import get_static_test_file


def test_get_gazetteer_configs_valid(monkeypatch):
    monkeypatch.setattr(
        "geoparser.config.config.get_config_file",
        lambda _: get_static_test_file("gazetteers_config_valid.yaml"),
    )
    expected = {
        "test-full": GazetteerConfig(
            name="test-full",
            location_identifier="testid",
            location_columns=[
                Column(name="testid", type="INTEGER", primary=True),
                Column(name="testname", type="TEXT"),
            ],
            data=[
                GazetteerData(
                    name="data1",
                    url="https://data1.org/path/to/data1.zip",
                    extracted_files=["data1.txt"],
                    columns=[
                        Column(name="testid", type="INTEGER", primary=True),
                        Column(name="testname", type="TEXT"),
                    ],
                    skiprows=50,
                ),
                GazetteerData(
                    name="data2",
                    url="https://data2.org/path/to/data2.zip",
                    extracted_files=["data2.txt"],
                    columns=[
                        Column(name="testcode", type="TEXT", primary=True),
                        Column(name="testname", type="TEXT"),
                    ],
                    toponym_columns=[
                        ToponymColumn(name="testminimal"),
                        ToponymColumn(name="testseparator", separator=","),
                    ],
                ),
            ],
        ),
        "test-minimal": GazetteerConfig(
            name="test-minimal",
            location_identifier="testid",
            location_columns=[Column(name="testid", type="INTEGER", primary=True)],
            data=[
                GazetteerData(
                    name="data1",
                    url="https://data1.org/path/to/data1.zip",
                    extracted_files=["data1.txt"],
                    columns=[Column(name="testid", type="INTEGER", primary=True)],
                ),
            ],
        ),
    }
    actual = get_gazetteer_configs()
    assert actual == expected


def test_get_gazetteer_configs_invalid(monkeypatch):
    monkeypatch.setattr(
        "geoparser.config.config.get_config_file",
        lambda _: get_static_test_file("gazetteers_config_invalid.yaml"),
    )
    with pytest.raises(pydantic.ValidationError):
        _ = get_gazetteer_configs()
