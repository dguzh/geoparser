import typing as t

from markupsafe import Markup
from pyproj import Transformer
from werkzeug.utils import secure_filename

from geoparser.geoparser import Geoparser


class GeoparserAnnotator(Geoparser):
    def __init__(self, *args, **kwargs):
        # Do not initialize spacy model here
        self.gazetteer = None
        self.nlp = None
        self.transformer = None

        self.sessions = {}  # Store sessions with their IDs
        self.current_session_id = None

    def get_toponym(self, toponyms: dict, start: int, end: int) -> t.Optional[dict]:
        return next(
            (t for t in toponyms if t["start"] == start and t["end"] == end),
            None,
        )

    def parse_files(self, files: list[t.IO], spacy_model: str) -> t.Iterator[dict]:
        self.nlp = self.setup_spacy(spacy_model)
        for file in files:
            filename = secure_filename(file.filename)
            text = file.read().decode("utf-8")
            doc = self.nlp(text)
            toponyms = [
                {
                    "text": top.text,
                    "start": top.start_char,
                    "end": top.end_char,
                    "loc_id": "",  # Empty string indicates not annotated yet
                }
                for top in doc.toponyms
            ]
            yield {
                "filename": filename,
                "spacy_model": spacy_model,
                "text": text,
                "toponyms": toponyms,
            }

    def get_pre_annotated_text(self, text, toponyms):
        html_parts = []
        last_idx = 0
        for toponym in sorted(toponyms, key=lambda x: x["start"]):
            start_char = toponym["start"]
            end_char = toponym["end"]
            annotated = toponym["loc_id"] != ""
            # Escape the text before the toponym
            before_toponym = Markup.escape(text[last_idx:start_char])
            html_parts.append(before_toponym)

            # Create the span for the toponym
            toponym_text = Markup.escape(text[start_char:end_char])
            span = Markup(
                '<span class="toponym {annotated_class}" data-start="{start}" data-end="{end}">{text}</span>'
            ).format(
                annotated_class="annotated" if annotated else "",
                start=start_char,
                end=end_char,
                text=toponym_text,
            )
            html_parts.append(span)
            last_idx = end_char
        # Append the remaining text after the last toponym
        after_toponym = Markup.escape(text[last_idx:])
        html_parts.append(after_toponym)
        # Combine all parts into a single Markup object
        html = Markup("").join(html_parts)
        return html

    def prepare_documents(self, documents: list[dict]) -> t.Iterator[dict]:
        for idx, doc_item in enumerate(documents):
            total_toponyms = len(doc_item["toponyms"])
            annotated_toponyms = sum(
                1 for t in doc_item["toponyms"] if t["loc_id"] != ""
            )
            yield {
                "filename": doc_item["filename"],
                "total_toponyms": total_toponyms,
                "annotated_toponyms": annotated_toponyms,
                "doc_index": idx,
            }

    def get_existing_loc_id(self, toponym: dict) -> str:
        return toponym.get("loc_id", "")

    def get_candidate_descriptions(
        self, toponym: dict, toponym_text: str, query_text: str
    ) -> tuple[list[dict], bool]:

        # Get coordinate columns and CRS from gazetteer config
        coord_config = self.gazetteer.config.location_coordinates
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
        candidates = self.gazetteer.query_candidates(search_text)
        candidate_locations = self.gazetteer.query_locations(candidates)

        # Prepare candidate descriptions and attributes
        candidate_descriptions = []
        for location in candidate_locations:
            description = self.gazetteer.get_location_description(location)

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
                except ValueError:
                    lat = None
                    lon = None
            else:
                lat = None
                lon = None

            candidate_descriptions.append(
                {
                    "loc_id": location[self.gazetteer.config.location_identifier],
                    "description": description,
                    "attributes": location,  # Include all attributes for filtering
                    "latitude": lat,
                    "longitude": lon,
                }
            )

        existing_loc_id = self.get_existing_loc_id(toponym)

        append_existing_candidate = (
            existing_loc_id and not existing_loc_id in candidates
        )

        if append_existing_candidate:
            existing_location = self.gazetteer.query_locations([existing_loc_id])[0]
            existing_description = self.gazetteer.get_location_description(
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
                except ValueError:
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

    def get_filter_attributes(self) -> list[str]:
        location_identifier = self.gazetteer.config.location_identifier
        location_columns = self.gazetteer.config.location_columns

        filter_attributes = [
            col.name
            for col in location_columns
            if col.type == "TEXT"
            and col.name != location_identifier
            and not col.name.endswith(location_identifier)
        ]
        return filter_attributes

    def get_candidates(self, toponym: dict, toponym_text: str, query_text: str) -> dict:
        candidate_descriptions, existing_candidate_is_appended = (
            self.get_candidate_descriptions(toponym, toponym_text, query_text)
        )
        return jsonify(
            {
                "candidates": candidate_descriptions,
                "filter_attributes": self.get_filter_attributes(),
                "existing_loc_id": self.get_existing_loc_id(toponym),
                "existing_candidate": (
                    candidate_descriptions[-1]
                    if existing_candidate_is_appended
                    else None
                ),
            }
        )

    def annotate_toponyms(
        self,
        toponyms: list[dict],
        annotation: str,
        one_sense_per_discourse: bool = False,
    ) -> list[dict]:
        toponym = self.get_toponym(toponyms, annotation["start"], annotation["end"])
        # Update the loc_id
        toponym["loc_id"] = (
            annotation["loc_id"] if annotation["loc_id"] is not None else None
        )

        if one_sense_per_discourse and toponym["loc_id"]:
            # Apply the same loc_id to other unannotated toponyms with the same text
            for other_toponym in toponyms:
                if (
                    other_toponym["text"] == toponym["text"]
                    and other_toponym["loc_id"] == ""
                    and other_toponym is not toponym
                ):
                    other_toponym["loc_id"] = toponym["loc_id"]
        return toponyms

    def remove_toponym(doc: dict, toponym: dict) -> dict:
        toponyms = doc["toponyms"]
        toponyms.remove(toponym)
        return doc
