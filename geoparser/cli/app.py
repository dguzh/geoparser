import typer

from geoparser.cli.annotator import annotator_cli
from geoparser.cli.download import download_cli

app = typer.Typer()
app.command("annotator")(annotator_cli)
app.command("download")(download_cli)
