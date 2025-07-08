import typing as t
from abc import abstractmethod

from geoparser.modules.module import Module

if t.TYPE_CHECKING:
    from geoparser.db.models import Reference


class Resolver(Module):
    """
    Abstract class for modules that perform reference resolution.

    These modules link recognized references to specific referents in a gazetteer.
    Resolution modules focus solely on the prediction logic without database interactions.
    """

    # This base class should have NAME set to None since it should not be instantiated directly
    NAME = None

    def __init__(self, **kwargs):
        """
        Initialize a resolution module.

        Args:
            **kwargs: Configuration parameters for this module
        """
        super().__init__(**kwargs)

    @abstractmethod
    def predict_referents(
        self, references: t.List["Reference"]
    ) -> t.List[t.List[t.Tuple[str, str]]]:
        """
        Predict referents for multiple references.

        This abstract method must be implemented by child classes.

        Args:
            references: List of Reference ORM objects to process.
                       Each Reference object provides access to:
                       - reference.text: the actual reference text
                       - reference.start/end: positions in document
                       - reference.document: full Document object
                       - reference.document.text: full document text

        Returns:
            List of lists of tuples containing (gazetteer_name, identifier).
            Each inner list corresponds to referents found for one reference at the same index in the input list.
            The gazetteer_name identifies which gazetteer the identifier refers to,
            and the identifier is the value used to identify the referent in that gazetteer.
        """
