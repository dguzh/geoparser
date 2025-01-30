import typing as t

from fastapi import UploadFile
from markupsafe import Markup
from pyproj import Transformer
from werkzeug.utils import secure_filename

from geoparser.geoparser import Geoparser


class GeoparserAnnotator(Geoparser):
    """Geoparser subclass without model initialization"""

    def __init__(self, *args, **kwargs):
        # Do not initialize spacy model here
        self.gazetteer = None
        self.nlp = None
        self.transformer = None

    def remove_toponym(self, doc: dict, toponym: dict) -> dict:
        toponyms = doc["toponyms"]
        toponyms.remove(toponym)
        return doc
