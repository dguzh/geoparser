from importlib.resources import files
from pathlib import Path

import typer

from geoparser.gazetteer.artifact import artifact_path, list_artifacts
from geoparser.gazetteer.build import GazetteerBuilder
from geoparser.gazetteer.build.builder import uninstall


def _get_builtin_gazetteers() -> dict[str, Path]:
    """
    Discover all built-in gazetteer configurations.

    Returns:
        Dictionary mapping gazetteer names to their config file paths.
    """
    configs_dir = files("geoparser.gazetteer") / "configs"

    # Get all yaml files in the configs directory
    gazetteers = {}
    for config_file in configs_dir.iterdir():
        if config_file.name.endswith(".yaml"):
            gazetteer_name = config_file.name[:-5]  # Remove .yaml extension
            gazetteers[gazetteer_name] = Path(str(config_file))

    return gazetteers


def install_cli(config: str):
    """
    Install a gazetteer from a configuration file.

    Args:
        config: Either a gazetteer name (e.g., 'geonames', 'swissnames3d') or
                a path to a custom YAML configuration file.
    """
    # Check if config is a built-in gazetteer name
    config_path = Path(config)

    if not config_path.exists():
        # Get available built-in gazetteers
        builtin_gazetteers = _get_builtin_gazetteers()

        if config in builtin_gazetteers:
            config_path = builtin_gazetteers[config]
        else:
            available = "\n".join(
                f"  - {name}" for name in sorted(builtin_gazetteers.keys())
            )
            raise FileNotFoundError(
                f"Gazetteer config not found: {config}\n"
                f"Available built-in gazetteer configs:\n{available}"
            )

    builder = GazetteerBuilder()
    builder.build(config_path)


def list_cli():
    """
    List installed gazetteers.
    """
    names = list_artifacts()
    if not names:
        typer.echo("No gazetteers installed.")
        return
    for name in names:
        size = artifact_path(name).stat().st_size
        typer.echo(f"{name}  ({size / 1024 / 1024:.1f} MB)")


def uninstall_cli(name: str):
    """
    Remove an installed gazetteer.

    Args:
        name: Name of the gazetteer to remove.
    """
    if uninstall(name):
        typer.echo(f"Removed gazetteer '{name}'.")
    else:
        typer.secho(
            f"Gazetteer '{name}' is not installed.", fg=typer.colors.YELLOW, err=True
        )
        raise typer.Exit(code=1)
