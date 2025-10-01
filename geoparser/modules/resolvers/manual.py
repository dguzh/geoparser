import typing as t

from geoparser.modules.resolvers import Resolver

if t.TYPE_CHECKING:
    from geoparser.db.models import Reference


class ManualResolver(Resolver):
    """
    A resolution module for manually annotated referents.

    This module doesn't perform actual resolution but serves as a placeholder
    to link manually provided referent annotations to a resolver in the database.
    It should not be used with the run() method.
    """

    NAME = "ManualResolver"

    def __init__(self):
        """
        Initialize the ManualResolver.

        This resolver has no configuration parameters since it doesn't
        perform any actual resolution.
        """
        super().__init__()

    def predict_referents(
        self, references: t.List["Reference"]
    ) -> t.List[t.Tuple[str, str]]:
        """
        This method should not be called for ManualResolver.

        Manual annotations should be provided directly through the Project interface
        rather than through the module's predict method.

        Args:
            references: List of Reference ORM objects

        Returns:
            Empty list

        Raises:
            NotImplementedError: Always, as manual annotations should be provided directly
        """
        raise NotImplementedError(
            "ManualResolver does not support predict_referents(). "
            "Provide annotations directly through the Project.add_documents() interface."
        )
