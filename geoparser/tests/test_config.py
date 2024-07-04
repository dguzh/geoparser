from geoparser.config import get_gazetteer_configs
from geoparser.config.models import Column, GazetteerConfig, GazetteerData, VirtualTable
from geoparser.tests.utils import get_static_test_file


def test_get_gazetteer_configs(monkeypatch):
    monkeypatch.setattr(
        "geoparser.config.config.get_config_file",
        lambda _: get_static_test_file("gazetteers_config.yaml"),
    )
    expected = {
        "test_gazetteer": GazetteerConfig(
            name="test_gazetteer",
            data=[
                GazetteerData(
                    name="full",
                    url="https://test.test.org/path/to/file.zip",
                    extracted_file="file.txt",
                    skiprows=50,
                    columns=[
                        Column(name="col1", type="INTEGER", primary=True),
                        Column(name="col2", type="TEXT"),
                    ],
                    virtual_tables=[
                        VirtualTable(
                            name="virtual1",
                            using="anything",
                            args=["name"],
                            kwargs={"kwarg1": "kwarg1", "kwarg2": "kwarg2"},
                        )
                    ],
                ),
                GazetteerData(
                    name="minimal",
                    url="https://test.test.org/path/to/file.zip",
                    extracted_file="file.txt",
                    columns=[Column(name="col1", type="INTEGER")],
                ),
            ],
        )
    }
    actual = get_gazetteer_configs()
    assert actual == expected
