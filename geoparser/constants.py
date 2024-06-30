from geoparser.config import get_gazetteer_configs
from geoparser.geonames import GeoNames

GAZETTEERS = {"geonames": GeoNames}
GAZETTEERS_CONFIG = get_gazetteer_configs()
MAX_ERROR = 20039  # half Earth's circumference in km
MODES = {"download": "download"}
