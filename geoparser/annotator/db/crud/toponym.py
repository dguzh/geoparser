import typing as t
import uuid

from pyproj import Transformer
from sqlmodel import Session as DBSession
from sqlmodel import select

from geoparser.annotator.db.crud.base import BaseRepository
from geoparser.annotator.db.models.toponym import (
    AnnotatorToponym,
    AnnotatorToponymBase,
    AnnotatorToponymCreate,
    AnnotatorToponymUpdate,
)
from geoparser.annotator.exceptions import (
    ToponymNotFoundException,
    ToponymOverlapException,
)
from geoparser.annotator.models.api import CandidatesGet
from geoparser.gazetteer.gazetteer import Gazetteer

if t.TYPE_CHECKING:
    from geoparser.annotator.db.models.document import AnnotatorDocument
    from geoparser.gazetteer.feature import Feature


# _remove_duplicates only ever returns elements of new_toponyms, so it keeps
# whichever kind of toponym model it was handed.
NewToponymT = t.TypeVar("NewToponymT", bound=AnnotatorToponymBase)


class ToponymRepository(BaseRepository[AnnotatorToponym]):
    model = AnnotatorToponym
    exception_factory: t.Callable[[str, uuid.UUID], Exception] = lambda x, y: (
        ToponymNotFoundException(f"{x} with ID {y} not found.")
    )

    # Gazetteer-specific attribute mappings for location descriptions
    GAZETTEER_ATTRIBUTE_MAP: t.ClassVar[dict[str, dict[str, str]]] = {
        "geonames": {
            "name": "name",
            "type": "feature_name",
            "level1": "country_name",
            "level2": "admin1_name",
            "level3": "admin2_name",
        },
        "swissnames3d": {
            "name": "NAME",
            "type": "OBJEKTART",
            "level1": "KANTON_NAME",
            "level2": "BEZIRK_NAME",
            "level3": "GEMEINDE_NAME",
        },
    }

    # Filter attributes for each gazetteer
    GAZETTEER_FILTER_ATTRIBUTES: t.ClassVar[dict[str, list[str]]] = {
        "geonames": [
            "feature_name",
            "country_name",
            "admin1_name",
            "admin2_name",
        ],
        "swissnames3d": [
            "OBJEKTART",
            "KANTON_NAME",
            "BEZIRK_NAME",
            "GEMEINDE_NAME",
        ],
    }

    @classmethod
    def _generate_location_description(
        cls, feature: "Feature", gazetteer_name: str
    ) -> str:
        """
        Generate a lightweight textual description for a feature.

        This is a simplified version that doesn't require loading heavy ML models,
        making it fast for the annotator UI.

        Args:
            feature: Feature object
            gazetteer_name: Name of the gazetteer

        Returns:
            Location description string
        """
        # Get location data
        location_data = feature.data

        if not location_data:
            return feature.identifier

        # Get attribute mappings for this gazetteer
        if gazetteer_name not in cls.GAZETTEER_ATTRIBUTE_MAP:
            return feature.identifier

        attr_map = cls.GAZETTEER_ATTRIBUTE_MAP[gazetteer_name]

        # Extract attributes
        feature_name = location_data.get(attr_map["name"])
        feature_type = location_data.get(attr_map["type"])

        # Build description components
        description_parts = []

        # Add feature name if available
        if feature_name:
            description_parts.append(feature_name)

        # Add feature type in brackets if available
        if feature_type:
            description_parts.append(f"({feature_type})")

        # Build hierarchical context from admin levels
        admin_levels = []
        for level in ["level3", "level2", "level1"]:
            if level in attr_map:
                admin_value = location_data.get(attr_map[level])
                if admin_value:
                    admin_levels.append(admin_value)

        # Combine description parts
        if admin_levels:
            description_parts.append("in")
            description_parts.append(", ".join(admin_levels))

        description = " ".join(description_parts).strip()

        return description if description else feature.identifier

    @classmethod
    def validate_overlap(
        cls,
        db: DBSession,
        toponym: AnnotatorToponymBase | AnnotatorToponymUpdate,
        document_id: uuid.UUID | str | None,
    ) -> bool:
        # A partial update that names no document, or leaves the span alone,
        # cannot introduce an overlap. SQL already behaved this way -- comparing
        # against NULL matched nothing -- so this only makes the outcome explicit.
        if document_id is None or toponym.start is None or toponym.end is None:
            return True
        filter_args = [
            AnnotatorToponym.document_id == document_id,
            (AnnotatorToponym.start < toponym.end)
            & (AnnotatorToponym.end > toponym.start),
        ]
        if hasattr(toponym, "id"):
            filter_args.append(AnnotatorToponym.id != toponym.id)
        overlapping = db.exec(select(AnnotatorToponym).where(*filter_args)).all()
        if overlapping:
            raise ToponymOverlapException(
                f"Toponyms overlap: {overlapping} and {toponym}",
            )
        return True

    @classmethod
    def _remove_duplicates(
        cls,
        old_toponyms: t.Sequence[AnnotatorToponym | AnnotatorToponymCreate],
        new_toponyms: t.Sequence[NewToponymT],
    ) -> list[NewToponymT]:
        toponyms = []
        for new_toponym in new_toponyms:
            # only add the new toponym if there is no existing one
            if not cls._get_toponym(old_toponyms, new_toponym.start, new_toponym.end):
                toponyms.append(new_toponym)
        return sorted(toponyms, key=lambda x: x.start)

    @classmethod
    def _get_wgs84_coordinates(
        cls, feature: "Feature"
    ) -> tuple[float, float] | tuple[None, None]:
        """
        Extract WGS84 (lat, lon) coordinates from a feature's geometry.

        Gazetteer artifacts declare the CRS of their geometries; coordinates
        are transformed to WGS84 when the artifact uses a different CRS.

        Args:
            feature: Feature object with geometry

        Returns:
            Tuple of (latitude, longitude) in WGS84, or (None, None) if unavailable
        """
        if not feature.geometry:
            return None, None

        try:
            # Get the centroid for point representation
            centroid = feature.geometry.centroid

            # If already in WGS84, return as-is
            if feature.crs == "EPSG:4326":
                return centroid.y, centroid.x  # lat, lon

            # Otherwise, transform to WGS84
            transformer = Transformer.from_crs(feature.crs, "EPSG:4326", always_xy=True)
            lon, lat = transformer.transform(centroid.x, centroid.y)
            return lat, lon

        except Exception:
            return None, None

    @classmethod
    def get_candidate_descriptions(
        cls,
        gazetteer_name: str,
        toponym: AnnotatorToponym,
        toponym_text: str,
        query_text: str,
    ) -> tuple[list[dict], bool]:
        # Initialize gazetteer
        gazetteer = Gazetteer(gazetteer_name)

        # Use query_text if provided, else use toponym_text
        search_text = query_text if query_text else toponym_text

        # Get candidates from gazetteer (returns list of Feature objects)
        candidates = gazetteer.search(search_text, method="exact")

        # Prepare candidate descriptions and attributes
        candidate_descriptions = []
        for candidate in candidates:
            # Generate description using lightweight method
            description = cls._generate_location_description(candidate, gazetteer_name)

            # Get coordinates from geometry (with CRS transformation if needed)
            lat, lon = cls._get_wgs84_coordinates(candidate)

            candidate_descriptions.append(
                {
                    "loc_id": candidate.identifier,
                    "description": description,
                    "attributes": candidate.data,  # Include all attributes for filtering
                    "latitude": lat,
                    "longitude": lon,
                }
            )

        # Handle existing annotation if it's not in the candidate list
        existing_loc_id = toponym.loc_id
        candidate_ids = [c.identifier for c in candidates]
        append_existing_candidate = (
            bool(existing_loc_id) and existing_loc_id not in candidate_ids
        )

        if append_existing_candidate:
            # Find the existing location
            existing_feature = gazetteer.find(existing_loc_id)
            if existing_feature:
                existing_description = cls._generate_location_description(
                    existing_feature, gazetteer_name
                )

                # Get coordinates from geometry (with CRS transformation if needed)
                lat, lon = cls._get_wgs84_coordinates(existing_feature)

                existing_annotation = {
                    "loc_id": existing_loc_id,
                    "description": existing_description,
                    "attributes": existing_feature.data,
                    "latitude": lat,
                    "longitude": lon,
                }
                candidate_descriptions.append(existing_annotation)

        return candidate_descriptions, append_existing_candidate

    @classmethod
    # BaseRepository declares the widest input type (SQLModel); each repository
    # deliberately accepts its own Create/Update model. Callers always go
    # through the concrete repository, so the precise signature is worth more
    # here than strict substitutability.
    def create(  # ty: ignore[invalid-method-override]
        cls,
        db: DBSession,
        item: AnnotatorToponymCreate,
        exclude: list[str] | None = None,
        additional: dict[str, t.Any] | None = None,
    ) -> AnnotatorToponym:
        assert additional and "document_id" in additional, (
            "toponym cannot be created without link to document"
        )
        cls.validate_overlap(db, item, additional["document_id"])
        return super().create(db, item, exclude=exclude, additional=additional)

    @classmethod
    def read(cls, db: DBSession, id: uuid.UUID) -> AnnotatorToponym:
        return super().read(db, id)

    @classmethod
    def _get_toponym(
        cls,
        toponyms: t.Sequence[AnnotatorToponym | AnnotatorToponymCreate],
        start: int,
        end: int,
    ) -> AnnotatorToponym | AnnotatorToponymCreate | None:
        return next(
            (t for t in toponyms if t.start == start and t.end == end),
            None,
        )

    @classmethod
    def get_toponym(
        cls, document: "AnnotatorDocument", start: int, end: int
    ) -> AnnotatorToponym | None:
        # document.toponyms holds persisted rows, so the lookup can only yield
        # an AnnotatorToponym or None.
        found = cls._get_toponym(list(document.toponyms), start, end)
        return found if isinstance(found, AnnotatorToponym) else None

    @classmethod
    def read_all(cls, db: DBSession, **filters) -> list[AnnotatorToponym]:
        return super().read_all(db, **filters)

    @classmethod
    def get_candidates(
        cls,
        doc: "AnnotatorDocument",
        gazetteer_name: str,
        candidates_request: CandidatesGet,
    ) -> dict:
        toponym = cls.get_toponym(
            doc, candidates_request.start or 0, candidates_request.end or 0
        )
        if not toponym:
            raise ToponymNotFoundException
        candidate_descriptions, existing_candidate_is_appended = (
            cls.get_candidate_descriptions(
                gazetteer_name,
                toponym,
                candidates_request.text or "",
                candidates_request.query_text or "",
            )
        )

        # Get filter attributes for this gazetteer
        filter_attributes = cls.GAZETTEER_FILTER_ATTRIBUTES.get(gazetteer_name, [])

        return {
            "candidates": candidate_descriptions,
            "filter_attributes": filter_attributes,
            "existing_loc_id": toponym.loc_id,
            "existing_candidate": (
                candidate_descriptions[-1] if existing_candidate_is_appended else None
            ),
        }

    @classmethod
    def update(  # ty: ignore[invalid-method-override]
        cls,
        db: DBSession,
        item: AnnotatorToponymUpdate | AnnotatorToponym,
        document_id: uuid.UUID | str | None = None,
    ) -> AnnotatorToponym:
        cls.validate_overlap(db, item, document_id or item.document_id)
        return super().update(db, item)

    @classmethod
    def annotate_many(
        cls,
        db: DBSession,
        document: "AnnotatorDocument",
        annotation: AnnotatorToponymBase,
    ) -> list[AnnotatorToponym]:
        toponym = cls.get_toponym(document, annotation.start, annotation.end)
        if toponym is None:
            raise ToponymNotFoundException
        one_sense_per_discourse = (
            toponym.document.session.settings.one_sense_per_discourse
        )
        # Update the loc_id
        toponym.loc_id = annotation.loc_id if annotation.loc_id is not None else None
        cls.update(db, toponym)
        if one_sense_per_discourse and toponym.loc_id:
            # Apply the same loc_id to other unannotated toponyms with the same text
            for other_toponym in document.toponyms:
                if (
                    other_toponym.text == toponym.text
                    and other_toponym.loc_id == ""
                    and other_toponym is not toponym
                ):
                    other_toponym.loc_id = toponym.loc_id
                    cls.update(db, other_toponym)
        db.refresh(document)
        return document.toponyms

    @classmethod
    def delete(cls, db: DBSession, id: uuid.UUID) -> AnnotatorToponym:
        return super().delete(db, id)
