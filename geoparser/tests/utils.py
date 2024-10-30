import typing as t
from pathlib import Path

from geoparser.gazetteers.gazetteer import LocalDBGazetteer


def execute_query(gazetteer: t.Type[LocalDBGazetteer], query: str) -> list:
    """
    helper function for executing a query for a Gazetteer instance
    with a fresh connection.
    """
    gazetteer._initiate_connection()
    cursor = gazetteer._get_cursor()
    rows = cursor.execute(query).fetchall()
    return rows


def make_concrete(abstract_class):
    class concreteClass(abstract_class):
        pass

    concreteClass.__abstractmethods__ = set()
    return type("ConcreteClass" + abstract_class.__name__, (concreteClass,), {})


def get_static_test_file(filename: t.Union[str, Path]):
    here = Path(__file__).resolve().parent
    return here / Path("static") / Path(filename)
