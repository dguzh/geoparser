"""Constants for the annotator application."""

# Available gazetteers for the annotator
# Dictionary format for template compatibility
GAZETTEERS = {
    "geonames": "geonames",
    "swissnames3d": "swissnames3d",
}

# Default session settings
DEFAULT_SESSION_SETTINGS = {
    "auto_close_annotation_modal": False,
    "one_sense_per_discourse": False,
}
