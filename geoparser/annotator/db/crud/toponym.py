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
    from geoparser.db.models.feature import Feature


class ToponymRepository(BaseRepository):
    model = AnnotatorToponym
    exception_factory: t.Callable[[str, uuid.UUID], Exception] = (
        lambda x, y: ToponymNotFoundException(f"{x} with ID {y} not found.")
    )

    # Gazetteer-specific attribute mappings for location descriptions
    GAZETTEER_ATTRIBUTE_MAP = {
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

    # Coordinate reference systems for each gazetteer
    GAZETTEER_CRS = {
        "geonames": "EPSG:4326",  # WGS84
        "swissnames3d": "EPSG:2056",  # LV95 Swiss coordinate system
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
            return feature.identifier_value

        # Get attribute mappings for this gazetteer
        if gazetteer_name not in cls.GAZETTEER_ATTRIBUTE_MAP:
            return feature.identifier_value

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

        return description if description else feature.identifier_value

    @classmethod
    def validate_overlap(
        cls, db: DBSession, toponym: AnnotatorToponymCreate, document_id: uuid.UUID
    ) -> bool:
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
        old_toponyms: list[t.Union[AnnotatorToponym, AnnotatorToponymCreate]],
        new_toponyms: list[t.Union[AnnotatorToponym, AnnotatorToponymCreate]],
    ) -> list[AnnotatorToponymCreate]:
        toponyms = []
        for new_toponym in new_toponyms:
            # only add the new toponym if there is no existing one
            if not cls._get_toponym(old_toponyms, new_toponym.start, new_toponym.end):
                toponyms.append(new_toponym)
        return sorted(toponyms, key=lambda x: x.start)

    @classmethod
    def _get_wgs84_coordinates(
        cls, feature: "Feature", gazetteer_name: str
    ) -> tuple[float, float]:
        """
        Extract WGS84 (lat, lon) coordinates from a feature's geometry.

        Handles coordinate transformation if needed (e.g., Swiss coordinates to WGS84).

        Args:
            feature: Feature object with geometry
            gazetteer_name: Name of the gazetteer to determine source CRS

        Returns:
            Tuple of (latitude, longitude) in WGS84, or (None, None) if unavailable
        """
        if not feature.geometry:
            return None, None

        try:
            # Get the centroid for point representation
            centroid = feature.geometry.centroid

            # Get source CRS for this gazetteer
            source_crs = cls.GAZETTEER_CRS.get(gazetteer_name, "EPSG:4326")

            # If already in WGS84, return as-is
            if source_crs == "EPSG:4326":
                return centroid.y, centroid.x  # lat, lon

            # Otherwise, transform to WGS84
            transformer = Transformer.from_crs(source_crs, "EPSG:4326", always_xy=True)
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
            lat, lon = cls._get_wgs84_coordinates(candidate, gazetteer_name)

            candidate_descriptions.append(
                {
                    "loc_id": candidate.identifier_value,
                    "description": description,
                    "attributes": candidate.data,  # Include all attributes for filtering
                    "latitude": lat,
                    "longitude": lon,
                }
            )

        # Handle existing annotation if it's not in the candidate list
        existing_loc_id = toponym.loc_id
        candidate_ids = [c.identifier_value for c in candidates]
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
                lat, lon = cls._get_wgs84_coordinates(existing_feature, gazetteer_name)

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
    def create(
        cls,
        db: DBSession,
        item: AnnotatorToponymCreate,
        exclude: t.Optional[list[str]] = [],
        additional: t.Optional[dict[str, t.Any]] = {},
    ) -> AnnotatorToponym:
        assert (
            "document_id" in additional
        ), "toponym cannot be created without link to document"
        cls.validate_overlap(db, item, additional["document_id"])
        return super().create(db, item, exclude=exclude, additional=additional)

    @classmethod
    def read(cls, db: DBSession, id: uuid.UUID) -> AnnotatorToponym:
        return super().read(db, id)

    @classmethod
    def _get_toponym(
        cls,
        toponyms: list[t.Union[AnnotatorToponym, AnnotatorToponymCreate]],
        start: int,
        end: int,
    ) -> t.Optional[t.Union[AnnotatorToponym, AnnotatorToponymCreate]]:
        return next(
            (t for t in toponyms if t.start == start and t.end == end),
            None,
        )

    @classmethod
    def get_toponym(
        cls, document: "AnnotatorDocument", start: int, end: int
    ) -> t.Optional[AnnotatorToponym]:
        return cls._get_toponym(document.toponyms, start, end)

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
        toponym = cls.get_toponym(doc, candidates_request.start, candidates_request.end)
        if not toponym:
            raise ToponymNotFoundException
        candidate_descriptions, existing_candidate_is_appended = (
            cls.get_candidate_descriptions(
                gazetteer_name,
                toponym,
                candidates_request.text,
                candidates_request.query_text,
            )
        )
        return {
            "candidates": candidate_descriptions,
            "filter_attributes": [],  # Not needed for now, can be empty
            "existing_loc_id": toponym.loc_id,
            "existing_candidate": (
                candidate_descriptions[-1] if existing_candidate_is_appended else None
            ),
        }

    @classmethod
    def update(
        cls,
        db: DBSession,
        item: AnnotatorToponymUpdate,
        document_id: t.Optional[str] = None,
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
