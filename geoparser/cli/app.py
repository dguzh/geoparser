import typer

from geoparser.cli.annotator import annotator_cli
from geoparser.cli.download import download_cli
from geoparser.cli.install import install_cli, list_cli, uninstall_cli

app = typer.Typer()
app.command("annotator")(annotator_cli)
app.command("install")(install_cli)
app.command("list")(list_cli)
app.command("uninstall")(uninstall_cli)
app.command("download", deprecated=True)(download_cli)
