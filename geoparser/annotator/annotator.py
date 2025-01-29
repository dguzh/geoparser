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

    def annotate_toponyms(
        self,
        toponyms: list[dict],
        annotation: dict,
        one_sense_per_discourse: bool = False,
    ) -> list[dict]:
        toponym = self.get_toponym(toponyms, annotation["start"], annotation["end"])
        # Update the loc_id
        toponym["loc_id"] = (
            annotation["loc_id"] if annotation["loc_id"] is not None else None
        )

        if one_sense_per_discourse and toponym["loc_id"]:
            # Apply the same loc_id to other unannotated toponyms with the same text
            for other_toponym in toponyms:
                if (
                    other_toponym["text"] == toponym["text"]
                    and other_toponym["loc_id"] == ""
                    and other_toponym is not toponym
                ):
                    other_toponym["loc_id"] = toponym["loc_id"]
        return toponyms

    def remove_toponym(self, doc: dict, toponym: dict) -> dict:
        toponyms = doc["toponyms"]
        toponyms.remove(toponym)
        return doc
