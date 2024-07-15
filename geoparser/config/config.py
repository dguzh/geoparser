import yaml

from geoparser.config.models import GazetteerConfig
from geoparser.config.utils import get_config_file


def get_gazetteer_configs() -> dict[str, GazetteerConfig]:
    with open(get_config_file("gazetteers.yaml"), "r") as config_file:
        yaml_config = yaml.safe_load(config_file)
    configs = {
        gazetteer_config["name"]: GazetteerConfig(**gazetteer_config)
        for gazetteer_config in yaml_config
    }
    return configs
