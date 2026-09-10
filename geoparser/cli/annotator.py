def annotator_cli():
    """Launch the Irchel Geoparser Annotator web application."""
    # Imported here rather than at module scope: building the FastAPI app
    # pulls in spaCy and torch, which would make every CLI invocation --
    # including `--help` -- pay for a web server nobody asked to start.
    from geoparser.annotator.app import run

    run()
