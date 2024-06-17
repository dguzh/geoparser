from spacy.tokens import Doc

from .geospan import GeoSpan

GeoSpan.set_extension("loc_id", default=None)
GeoSpan.set_extension("loc_score", default=None)


class GeoDoc(Doc):

    class Locations:
        def __init__(self, data):
            self.data = data

        def __getitem__(self, key):
            if isinstance(key, tuple):
                return [
                    (
                        tuple(item.get(k, None) for k in key)
                        if item
                        else (None,) * len(key)
                    )
                    for item in self.data
                ]
            else:
                return [item.get(key, None) if item else None for item in self.data]

        def __repr__(self):
            return repr(self.data)

    def __init__(self, geoparser, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geoparser = geoparser

    @property
    def locations(self):
        return self.Locations(
            self.geoparser.gazetteer.query_location_info(
                [toponym._.loc_id for toponym in self.toponyms]
            )
        )

    @property
    def toponyms(self):
        return tuple(
            GeoSpan(self, ent.start, ent.end, label=ent.label_)
            for ent in self.ents
            if ent.label_ in ["GPE", "LOC", "FAC", "ANNOT"]
        )
