import typing as t
from pathlib import Path


def get_config_file(filename: t.Union[str, Path]):
    here = Path(__file__).resolve().parent
    return here / Path(filename)
