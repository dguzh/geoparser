"""
CLI entry point for the Irchel Geoparser Annotator.

This module allows launching the annotator web application from the command line:
    python -m geoparser.annotator
"""

import argparse

from geoparser.annotator.app import run


def main():
    """Main entry point for the annotator CLI."""
    parser = argparse.ArgumentParser(
        description="Launch the Irchel Geoparser Annotator web application"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development (watches for file changes)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to run the server on (default: 5000)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind the server to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't automatically open browser on startup",
    )

    args = parser.parse_args()

    # Pass arguments to the run function
    print(f"Starting Irchel Geoparser Annotator on http://{args.host}:{args.port}")
    print("Press CTRL+C to quit")

    run(
        use_reloader=args.reload,
        host=args.host,
        port=args.port,
        open_browser=not args.no_browser,
    )


if __name__ == "__main__":
    main()
