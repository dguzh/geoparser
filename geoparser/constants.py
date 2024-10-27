from geoparser.geonames import GeoNames
from geoparser.swissnames3d import SwissNames3D

DEFAULT_TRANSFORMER_MODEL = "dguzh/geo-all-distilroberta-v1"

GAZETTEERS = {"geonames": GeoNames, "swissnames3d": SwissNames3D}
MAX_ERROR = 20039  # half Earth's circumference in km
MODES = {"download": "download", "annotator": "annotator"}
