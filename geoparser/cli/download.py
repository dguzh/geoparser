from importlib.resources import files
from pathlib import Path

from geoparser.gazetteer.installer.installer import GazetteerInstaller


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


def download_cli(config: str):
    """
    Download and install a gazetteer from a configuration file.

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

    # Install the gazetteer
    installer = GazetteerInstaller()
    installer.install(config_path)
