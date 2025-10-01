import typing as t

from geoparser.modules.recognizers import Recognizer

if t.TYPE_CHECKING:
    from geoparser.db.models import Document


class ManualRecognizer(Recognizer):
    """
    A recognition module for manually annotated references.

    This module doesn't perform actual recognition but serves as a placeholder
    to link manually provided reference annotations to a recognizer in the database.
    It should not be used with the run() method.
    """

    NAME = "ManualRecognizer"

    def __init__(self):
        """
        Initialize the ManualRecognizer.

        This recognizer has no configuration parameters since it doesn't
        perform any actual recognition.
        """
        super().__init__()

    def predict_references(
        self, documents: t.List["Document"]
    ) -> t.List[t.List[t.Tuple[int, int]]]:
        """
        This method should not be called for ManualRecognizer.

        Manual annotations should be provided directly through the Project interface
        rather than through the module's predict method.

        Args:
            documents: List of Document ORM objects

        Returns:
            Empty list for each document

        Raises:
            NotImplementedError: Always, as manual annotations should be provided directly
        """
        raise NotImplementedError(
            "ManualRecognizer does not support predict_references(). "
            "Provide annotations directly through the Project.add_documents() interface."
        )
