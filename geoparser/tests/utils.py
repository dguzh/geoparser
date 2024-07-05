import typing as t
from pathlib import Path


def make_concrete(abstract_class):
    class concreteClass(abstract_class):
        pass

    concreteClass.__abstractmethods__ = set()
    return type("ConcreteClass" + abstract_class.__name__, (concreteClass,), {})


def get_static_test_file(filename: t.Union[str, Path]):
    here = Path(__file__).resolve().parent
    return here / Path("static") / Path(filename)
