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


def main(args: argparse.Namespace):
    if args.mode == MODES["download"]:
        if not args.gazetteer:
            print("Error: 'gazetteer' argument is required for 'download' mode.")
            exit(1)
        for gazetteer_name in args.gazetteer:
            gazetteer = GAZETTEERS[gazetteer_name]()
            gazetteer.setup_database()
    elif args.mode == MODES["annotator"]:
        from geoparser.annotator import GeoparserAnnotator

        annotator = GeoparserAnnotator()
        annotator.run()
    else:
        print(f"Unknown mode: {args.mode}")


if __name__ == "__main__":
    args = parse_args()
    main(args)
