from __future__ import annotations

import typing as t

from spacy.tokens import Doc

from geoparser.geospan import GeoSpan

GeoSpan.set_extension("loc_id", default=None)
GeoSpan.set_extension("loc_score", default=None)
GeoSpan.set_extension("candidate_cache", default={})


class GeoDoc(Doc):
    """Custom spaCy Doc class extended for geoparsing."""

    def __init__(self, geoparser: Geoparser, *args, **kwargs):
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
    def locations(self) -> t.List[t.Dict[str, t.Any]]:
        """
        Get location information for all toponyms in the document.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing location data for toponyms.
        """
        return self.geoparser.gazetteer.query_locations(
            [toponym._.loc_id for toponym in self.toponyms]
        )

    @property
    def toponyms(self) -> t.Tuple[GeoSpan, ...]:
        """
        Retrieve the toponyms identified in the document.

        Returns:
            Tuple[GeoSpan, ...]: Tuple of GeoSpan objects representing toponyms.
        """
        return tuple(
            GeoSpan(self, ent.start, ent.end, label=ent.label_)
            for ent in self.ents
            if ent.label_ in ["GPE", "LOC", "FAC", "ANNOT"]
        )
