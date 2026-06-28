import typer


def download_cli(config: str):
    """
    [Deprecated] This command has been renamed to ``install``.

    Use ``install`` instead::

        python -m geoparser install geonames

    Args:
        config: Either a gazetteer name (e.g., 'geonames', 'swissnames3d') or
                a path to a custom YAML configuration file.
    """
    typer.secho(
        f"Use 'install' instead:\n" f"  python -m geoparser install {config}",
        fg=typer.colors.YELLOW,
        err=True,
    )
    raise typer.Exit(code=1)
