import argparse

from geoparser.constants import DEFAULT_TRANSFORMER_MODEL, GAZETTEERS, MODES


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
        choices=GAZETTEERS.keys(),
        nargs="?",
        help="Specify the gazetteer to set up (required for 'download' mode)",
    )
    parser.add_argument(
        "--transformer-model",
        type=str,
        default=DEFAULT_TRANSFORMER_MODEL,
        help="Specify the transformer model in annotator mode",
    )
    args = parser.parse_args()
    return args


def main(args: argparse.Namespace):
    if args.mode == MODES["download"]:
        if not args.gazetteer:
            print("Error: 'gazetteer' argument is required for 'download' mode.")
            exit(1)
        gazetteer = GAZETTEERS[args.gazetteer]()
        gazetteer.setup_database()
    elif args.mode == MODES["annotator"]:
        from geoparser.annotator import GeoparserAnnotator

        annotator = GeoparserAnnotator(args.transformer_model)
        annotator.run()
    else:
        print(f"Unknown mode: {args.mode}")


if __name__ == "__main__":
    args = parse_args()
    main(args)
