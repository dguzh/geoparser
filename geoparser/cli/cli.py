import argparse

from geoparser.constants import GAZETTEERS, MODES


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode",
        type=str,
        choices=MODES.values(),
        help="The setup mode for geoparser",
    )
    parser.add_argument(
        "gazetteer",
        type=str,
        nargs="*",
        choices=list(GAZETTEERS.keys()) + [[]],
        help="Specify the gazetteer to set up (required for 'download' mode)",
    )
    args = parser.parse_args()
    return args
