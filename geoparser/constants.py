from enum import Enum

from geoparser.gazetteers import GeoNames, SwissNames3D


class GAZETTEERS_CHOICES(str, Enum):
    geonames = "geonames"
    swissnames3d = "swissnames3d"


DEFAULT_GAZETTEER = "geonames"
DEFAULT_SPACY_MODEL = "en_core_web_sm"
DEFAULT_TRANSFORMER_MODEL = "dguzh/geo-all-MiniLM-L6-v2"
GAZETTEERS = {
    GAZETTEERS_CHOICES.geonames.value: GeoNames,
    GAZETTEERS_CHOICES.swissnames3d.value: SwissNames3D,
}
MAX_ERROR = 20039  # half Earth's circumference in km
