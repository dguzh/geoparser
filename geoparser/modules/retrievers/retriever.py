import typing as t
from abc import abstractmethod

from geoparser.db.models.feature import Feature
from geoparser.modules.module import Module


class Retriever(Module):
    """
    Abstract class for modules that perform candidate retrieval.

    These modules query gazetteer data to retrieve candidate features
    for given toponym strings. Retrieval modules focus solely on the
    candidate generation logic without database management.
    """

    # This base class should have NAME set to None since it should not be instantiated directly
    NAME = None

    def __init__(self, gazetteer_name: str, **kwargs):
        """
        Initialize a retrieval module.

        Args:
            gazetteer_name: Name of the gazetteer to query
            **kwargs: Additional configuration parameters for this module
        """
        super().__init__(gazetteer_name=gazetteer_name, **kwargs)
        self.gazetteer_name = gazetteer_name

    @abstractmethod
    def retrieve_candidates(self, toponyms: t.List[str]) -> t.List[t.List[Feature]]:
        """
        Retrieve candidate features for multiple toponyms.

        This abstract method must be implemented by child classes.

        Args:
            toponyms: List of toponym strings to retrieve candidates for

        Returns:
            List of lists of Feature objects. Each inner list corresponds to
            candidate features found for one toponym at the same index in the input list.
        """
