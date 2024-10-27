import typer

from geoparser.annotator import GeoparserAnnotator
from geoparser.constants import GAZETTEERS, GAZETTEERS_CHOICES

app = typer.Typer()


@app.command("download")
def download_cli(gazetteers: list[GAZETTEERS_CHOICES]):
    for gazetteer_name in gazetteers:
        gazetteer = GAZETTEERS[gazetteer_name]()
        gazetteer.setup_database()


@app.command("annotator")
def annotator_cli():
    annotator = GeoparserAnnotator()
    annotator.run()


def main():
    app()


if __name__ == "__main__":
    main()
