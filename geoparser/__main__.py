import argparse

from geoparser.cli.cli import parse_args
from geoparser.constants import GAZETTEERS, MODES


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
