import argparse

from geoparser.constants import GAZETTEERS, MODES


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode",
        type=str,
        choices=MODES.values(),
        help="the setup mode for geoparser",
    )
    parser.add_argument(
        "gazetteer",
        type=str,
        nargs="+",
        choices=GAZETTEERS.keys(),
        help="specify the gazetteer to set up",
    )
    args = parser.parse_args()
    return args


def main(args: argparse.Namespace):
    if args.mode == MODES["download"]:
        for gazetteer_name in args.gazetteer:
            gazetteer = GAZETTEERS[gazetteer_name]()
            gazetteer.setup_database()


if __name__ == "__main__":
    args = parse_args()
    main(args)
