import typing as t
import uuid

from pyproj import Transformer
from sqlmodel import Session as DBSession
from sqlmodel import select

from geoparser import Geoparser
from geoparser.annotator.db.crud.base import BaseRepository
from geoparser.annotator.db.models.toponym import (
    Toponym,
    ToponymBase,
    ToponymCreate,
    ToponymUpdate,
)
from geoparser.annotator.exceptions import (
    ToponymNotFoundException,
    ToponymOverlapException,
)
from geoparser.annotator.models.api import CandidatesGet

if t.TYPE_CHECKING:
    from geoparser.annotator.db.models.document import Document


class ToponymRepository(BaseRepository):
    model = Toponym
    exception_factory: t.Callable[[str, uuid.UUID], Exception] = (
        lambda x, y: ToponymNotFoundException(f"{x} with ID {y} not found.")
    )

    @classmethod
    def validate_overlap(
        cls, db: DBSession, toponym: ToponymCreate, document_id: uuid.UUID
    ) -> bool:
        filter_args = [
            Toponym.document_id == document_id,
            (Toponym.start < toponym.end) & (Toponym.end > toponym.start),
        ]
        if hasattr(toponym, "id"):
            filter_args.append(Toponym.id != toponym.id)
        overlapping = db.exec(select(Toponym).where(*filter_args)).all()
        if overlapping:
            raise ToponymOverlapException(
                f"Toponyms overlap: {overlapping} and {toponym}",
            )
        return True

    @classmethod
    def _remove_duplicates(
        cls,
        old_toponyms: list[t.Union[Toponym, ToponymCreate]],
        new_toponyms: list[t.Union[Toponym, ToponymCreate]],
    ) -> list[ToponymCreate]:
        toponyms = []
        for new_toponym in new_toponyms:
            # only add the new toponym if there is no existing one
            if not cls._get_toponym(old_toponyms, new_toponym.start, new_toponym.end):
                toponyms.append(new_toponym)
        return sorted(toponyms, key=lambda x: x.start)

    @classmethod
    def get_candidate_descriptions(
        cls, geoparser: Geoparser, toponym: Toponym, toponym_text: str, query_text: str
    ) -> tuple[list[dict], bool]:
        # Get coordinate columns and CRS from gazetteer config
        coord_config = geoparser.gazetteer.config.location_coordinates
        x_col = coord_config.x_column
        y_col = coord_config.y_column
        crs = coord_config.crs
        # Prepare coordinate transformer if needed
        if crs != "EPSG:4326":
            # Define transformer to WGS84
            coord_transformer = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
        else:
            coord_transformer = None
        # Use query_text if provided, else use toponym_text
        search_text = query_text if query_text else toponym_text
        # Get candidate IDs and locations based on the search_text
        candidates = geoparser.gazetteer.query_candidates(search_text)
        candidate_locations = geoparser.gazetteer.query_locations(candidates)
        # Prepare candidate descriptions and attributes
        candidate_descriptions = []
        for location in candidate_locations:
            description = geoparser.gazetteer.get_location_description(location)
            # Get coordinates
            x = location.get(x_col)
            y = location.get(y_col)
            if x is not None and y is not None:
                try:
                    x = float(x)
                    y = float(y)
                    if coord_transformer:
                        lon, lat = coord_transformer.transform(x, y)
                    else:
                        lon, lat = x, y
                except (ValueError, TypeError):
                    lat = None
                    lon = None
            else:
                lat = None
                lon = None
            candidate_descriptions.append(
                {
                    "loc_id": location[geoparser.gazetteer.config.location_identifier],
                    "description": description,
                    "attributes": location,  # Include all attributes for filtering
                    "latitude": lat,
                    "longitude": lon,
                }
            )
        existing_loc_id = toponym.loc_id
        append_existing_candidate = (
            bool(existing_loc_id) and not existing_loc_id in candidates
        )
        if append_existing_candidate:
            existing_location = geoparser.gazetteer.query_locations([existing_loc_id])[
                0
            ]
            existing_description = geoparser.gazetteer.get_location_description(
                existing_location
            )
            # Get coordinates
            x = existing_location.get(x_col)
            y = existing_location.get(y_col)
            if x is not None and y is not None:
                try:
                    x = float(x)
                    y = float(y)
                    if coord_transformer:
                        lon, lat = coord_transformer.transform(x, y)
                    else:
                        lon, lat = x, y
                except (ValueError, TypeError):
                    lat = None
                    lon = None
            else:
                lat = None
                lon = None
            existing_annotation = {
                "loc_id": existing_loc_id,
                "description": existing_description,
                "attributes": existing_location,
                "latitude": lat,
                "longitude": lon,
            }
            candidate_descriptions.append(existing_annotation)
        return candidate_descriptions, append_existing_candidate

    @classmethod
    def create(
        cls,
        db: DBSession,
        item: ToponymCreate,
        exclude: t.Optional[list[str]] = [],
        additional: t.Optional[dict[str, t.Any]] = {},
    ) -> Toponym:
        assert (
            "document_id" in additional
        ), "toponym cannot be created without link to document"
        cls.validate_overlap(db, item, additional["document_id"])
        return super().create(db, item, exclude=exclude, additional=additional)

    @classmethod
    def read(cls, db: DBSession, id: uuid.UUID) -> Toponym:
        return super().read(db, id)

    @classmethod
    def _get_toponym(
        cls, toponyms: list[t.Union[Toponym, ToponymCreate]], start: int, end: int
    ) -> t.Optional[t.Union[Toponym, ToponymCreate]]:
        return next(
            (t for t in toponyms if t.start == start and t.end == end),
            None,
        )

    @classmethod
    def get_toponym(
        cls, document: "Document", start: int, end: int
    ) -> t.Optional[Toponym]:
        return cls._get_toponym(document.toponyms, start, end)

    @classmethod
    def read_all(cls, db: DBSession, **filters) -> list[Toponym]:
        return super().read_all(db, **filters)

    @classmethod
    def get_candidates(
        cls, doc: "Document", geoparser: Geoparser, candidates_request: CandidatesGet
    ) -> dict:
        toponym = cls.get_toponym(doc, candidates_request.start, candidates_request.end)
        if not toponym:
            raise ToponymNotFoundException
        candidate_descriptions, existing_candidate_is_appended = (
            cls.get_candidate_descriptions(
                geoparser,
                toponym,
                candidates_request.text,
                candidates_request.query_text,
            )
        )
        return {
            "candidates": candidate_descriptions,
            "filter_attributes": geoparser.get_filter_attributes(),
            "existing_loc_id": toponym.loc_id,
            "existing_candidate": (
                candidate_descriptions[-1] if existing_candidate_is_appended else None
            ),
        }

    @classmethod
    def update(
        cls, db: DBSession, item: ToponymUpdate, document_id: t.Optional[str] = None
    ) -> Toponym:
        cls.validate_overlap(db, item, document_id or item.document_id)
        return super().update(db, item)

    @classmethod
    def annotate_many(
        cls, db: DBSession, document: "Document", annotation: ToponymBase
    ) -> list[Toponym]:
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
    def delete(cls, db: DBSession, id: uuid.UUID) -> Toponym:
        return super().delete(db, id)
