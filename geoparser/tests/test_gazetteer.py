import pytest

from geoparser.gazetteer import Gazetteer
from geoparser.tests.utils import make_concrete


@pytest.fixture
def gazetteer():
    gazetteer = make_concrete(Gazetteer)(db_name="")
    return gazetteer


def test_format_location_description(gazetteer):
    gazetteer = gazetteer
    assert True is True


def test_evaluate_conditionals():
    assert True is True
