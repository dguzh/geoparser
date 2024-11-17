from spacy.tokens import Doc

from geoparser.geospan import GeoSpan

GeoSpan.set_extension("loc_id", default=None)
GeoSpan.set_extension("loc_score", default=None)
GeoSpan.set_extension("candidate_cache", default={})


class Locations:
    """Class representing a collection of location data with convenient access methods."""

    def __init__(self, data: list[dict]):
        """
        Initialize Locations with a list of location data dictionaries.

        Args:
            data (list[dict]): List of dictionaries containing location information.
        """
        self.data = data

    def __getitem__(self, key):
        """
        Get item(s) from location data based on key(s).

        Args:
            key (str or tuple): The key or tuple of keys to retrieve from each location dict.

        Returns:
            list: List of values or tuples of values corresponding to the key(s).
        """
        if isinstance(key, tuple):
            return [
                (tuple(item.get(k, None) for k in key) if item else (None,) * len(key))
                for item in self.data
            ]
        else:
            return [item.get(key, None) if item else None for item in self.data]

    def __repr__(self):
        """
        Return the string representation of the location data.

        Returns:
            str: String representation of the location data.
        """
        return repr(self.data)


class GeoDoc(Doc):
    """Custom spaCy Doc class extended for geoparsing."""

    def __init__(self, geoparser, *args, **kwargs):
        """
        Initialize GeoDoc with geoparser and standard Doc arguments.

        Args:
            geoparser (Geoparser): The Geoparser instance associated with this document.
            *args: Variable length argument list for the base Doc class.
            **kwargs: Arbitrary keyword arguments for the base Doc class.
        """
        super().__init__(*args, **kwargs)
        self.geoparser = geoparser
        self.transformer_token_count = (
            len(geoparser.transformer.tokenizer.tokenize(self.text, verbose=False))
            if geoparser.transformer
            else -1
        )

    @property
    def locations(self):
        """
        Get location information for all toponyms in the document.

        Returns:
            Locations: A Locations object containing location data for toponyms.
        """
        return Locations(
            self.geoparser.gazetteer.query_location_info(
                [toponym._.loc_id for toponym in self.toponyms]
            )
        )

    @property
    def toponyms(self):
        """
        Retrieve the toponyms identified in the document.

        Returns:
            tuple[GeoSpan]: Tuple of GeoSpan objects representing toponyms.
        """
        return tuple(
            GeoSpan(self, ent.start, ent.end, label=ent.label_)
            for ent in self.ents
            if ent.label_ in ["GPE", "LOC", "FAC", "ANNOT"]
        )
