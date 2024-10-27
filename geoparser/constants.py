from enum import Enum

from geoparser.geonames import GeoNames
from geoparser.swissnames3d import SwissNames3D


class GAZETTEERS_CHOICES(str, Enum):
    geonames = "geonames"
    swissnames3d = "swissnames3d"


DEFAULT_TRANSFORMER_MODEL = "dguzh/geo-all-distilroberta-v1"
GAZETTEERS = {
    GAZETTEERS_CHOICES.geonames.value: GeoNames,
    GAZETTEERS_CHOICES.swissnames3d.value: SwissNames3D,
}
MAX_ERROR = 20039  # half Earth's circumference in km
