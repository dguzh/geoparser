import json
import os
import tempfile
import threading
import uuid
import webbrowser
from datetime import datetime
from pathlib import Path

import spacy
from appdirs import user_data_dir
from flask import (
    Flask,
    after_this_request,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from markupsafe import Markup
from pyproj import Transformer
from spacy.util import get_installed_models
from werkzeug.utils import secure_filename

from geoparser.constants import GAZETTEERS
from geoparser.geoparser import Geoparser


class GeoparserAnnotator(Geoparser):
    def __init__(self, *args, **kwargs):
        # Do not initialize spacy model here
        self.gazetteer = None
        self.nlp = None
        self.transformer = None

        template_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "templates")
        )
        self.app = Flask(__name__, template_folder=template_dir)
        self.app.config["SECRET_KEY"] = "dev"
        self.sessions = {}  # Store sessions with their IDs
        self.current_session_id = None
        # Define the cache directory
        self.cache_dir = os.path.join(user_data_dir("geoparser", ""), "annotator")
        os.makedirs(self.cache_dir, exist_ok=True)  # Ensure the directory exists
        self.setup_routes()

    def run(self, debug=False, use_reloader=False):
        def open_browser():
            webbrowser.open_new("http://127.0.0.1:5000/")

        threading.Timer(1.0, open_browser).start()
        self.app.run(host="0.0.0.0", port=5000, debug=debug, use_reloader=use_reloader)

    def setup_routes(self):
        @self.app.route("/")
        def index():
            return render_template("index.html")

        @self.app.route("/start_new_session", methods=["GET", "POST"])
        def start_new_session():
            gazetteers = GAZETTEERS
            spacy_models = list(get_installed_models())

            if request.method == "POST":
                uploaded_files = request.files.getlist("files[]")

                # Get selected gazetteer and spacy model
                selected_gazetteer = request.form.get("gazetteer")
                selected_spacy_model = request.form.get("spacy_model")

                # Re-initialize gazetteer and nlp with selected options
                self.gazetteer = self.setup_gazetteer(selected_gazetteer)
                self.nlp = self.setup_spacy(selected_spacy_model)

                # Process uploaded files and create a new session
                session_id = uuid.uuid4().hex
                session = {
                    "session_id": session_id,
                    "created_at": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat(),
                    "gazetteer": selected_gazetteer,
                    "settings": {
                        "one_sense_per_discourse": False,
                        "auto_close_annotation_modal": False,
                    },
                    "documents": [],
                }

                # Process uploaded files
                for file in uploaded_files:
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
                    session["documents"].append(
                        {
                            "filename": file.filename,
                            "spacy_model": selected_spacy_model,
                            "text": text,
                            "toponyms": toponyms,
                        }
                    )

                # Save session to cache
                session_file_path = os.path.join(self.cache_dir, f"{session_id}.json")
                with open(session_file_path, "w", encoding="utf-8") as f:
                    json.dump(session, f, ensure_ascii=False, indent=4)

                # Update current session
                self.current_session_id = session_id
                self.sessions[session_id] = session

                return redirect(url_for("annotate", session_id=session_id, doc_index=0))

            return render_template(
                "start_new_session.html",
                gazetteers=gazetteers,
                spacy_models=spacy_models,
            )

        @self.app.route("/continue_session", methods=["GET", "POST"])
        def continue_session():
            # Get list of cached sessions
            cached_sessions = self.get_cached_sessions()

            if request.method == "POST":
                action = request.form.get("action")
                if action == "load_cached":
                    selected_session_id = request.form.get("cached_session")
                    if not selected_session_id:
                        return redirect(url_for("continue_session"))

                    # Load selected session directly without creating a new session
                    session = self.load_session_from_cache(selected_session_id)
                    if not session:
                        return redirect(url_for("continue_session"))

                    # Update current session
                    self.current_session_id = selected_session_id
                    self.sessions[selected_session_id] = session

                    # Re-initialize gazetteer
                    self.gazetteer = self.setup_gazetteer(session["gazetteer"])

                    # Redirect to annotate page
                    return redirect(
                        url_for("annotate", session_id=selected_session_id, doc_index=0)
                    )

                elif action == "load_file":
                    # Handle uploaded session file
                    session_file = request.files.get("session_file")
                    if session_file and session_file.filename:
                        session_data = json.load(session_file.stream)
                        session_id = session_data.get("session_id")
                        if not session_id:
                            # Generate a new session_id if not present
                            session_id = uuid.uuid4().hex
                            session_data["session_id"] = session_id

                        # Save session to cache
                        session_file_path = os.path.join(
                            self.cache_dir, f"{session_id}.json"
                        )
                        with open(session_file_path, "w", encoding="utf-8") as f:
                            json.dump(session_data, f, ensure_ascii=False, indent=4)

                        # Update current session
                        self.current_session_id = session_id
                        self.sessions[session_id] = session_data

                        # Re-initialize gazetteer
                        self.gazetteer = self.setup_gazetteer(session_data["gazetteer"])

                        # Redirect to annotate page
                        return redirect(
                            url_for("annotate", session_id=session_id, doc_index=0)
                        )
                    else:
                        return redirect(url_for("continue_session"))
                else:
                    return redirect(url_for("continue_session"))

            return render_template(
                "continue_session.html", cached_sessions=cached_sessions
            )

        @self.app.route("/annotate/<session_id>")
        def annotate(session_id):
            doc_index = int(request.args.get("doc_index", 0))
            session = self.load_session_from_cache(session_id)
            if not session:
                return redirect(url_for("index"))

            self.current_session_id = session_id
            self.sessions[session_id] = session

            if doc_index >= len(session["documents"]):
                # If the document index is out of range, redirect to the first document
                return redirect(url_for("annotate", session_id=session_id, doc_index=0))

            doc = session["documents"][doc_index]

            # Prepare pre-annotated text
            pre_annotated_text = self.get_pre_annotated_text(
                doc["text"], doc["toponyms"]
            )

            # Prepare documents list with progress
            documents = []
            for idx, doc_item in enumerate(session["documents"]):
                total_toponyms = len(doc_item["toponyms"])
                annotated_toponyms = sum(
                    1 for t in doc_item["toponyms"] if t["loc_id"] != ""
                )
                documents.append(
                    {
                        "filename": doc_item["filename"],
                        "total_toponyms": total_toponyms,
                        "annotated_toponyms": annotated_toponyms,
                        "doc_index": idx,
                    }
                )

            # Pass spaCy models to the template
            spacy_models = list(get_installed_models())

            total_toponyms = len(doc["toponyms"])
            annotated_toponyms = sum(1 for t in doc["toponyms"] if t["loc_id"] != "")

            return render_template(
                "annotate.html",
                doc=doc,
                doc_index=doc_index,
                pre_annotated_text=pre_annotated_text,
                total_docs=len(session["documents"]),
                gazetteer=self.gazetteer,
                documents=documents,
                session_id=session_id,
                total_toponyms=total_toponyms,
                annotated_toponyms=annotated_toponyms,
                spacy_models=spacy_models,  # Include spaCy models for the modal
            )

        @self.app.route("/get_candidates", methods=["POST"])
        def get_candidates():
            data = request.json
            session_id = data["session_id"]
            doc_index = data["doc_index"]
            start = data["start"]
            end = data["end"]
            toponym_text = data["text"]
            query_text = data.get("query_text", "").strip()

            # Get coordinate columns and CRS from gazetteer config
            coord_config = self.gazetteer.config.location_coordinates
            x_col = coord_config.x_column
            y_col = coord_config.y_column
            crs = coord_config.crs

            # Prepare coordinate transformer if needed
            if crs != "EPSG:4326":
                # Define transformer to WGS84
                coord_transformer = Transformer.from_crs(
                    crs, "EPSG:4326", always_xy=True
                )
            else:
                coord_transformer = None

            session = self.load_session_from_cache(session_id)
            if not session:
                return jsonify({"error": "Session not found"}), 404

            doc = session["documents"][doc_index]
            toponym = next(
                (t for t in doc["toponyms"] if t["start"] == start and t["end"] == end),
                None,
            )
            if not toponym:
                return jsonify({"error": "Toponym not found"}), 404

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

            existing_loc_id = toponym.get("loc_id", "")

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

            # Get filter attributes from gazetteer configuration
            location_identifier = self.gazetteer.config.location_identifier
            location_columns = self.gazetteer.config.location_columns

            filter_attributes = [
                col.name
                for col in location_columns
                if col.type == "TEXT"
                and col.name != location_identifier
                and not col.name.endswith(location_identifier)
            ]

            return jsonify(
                {
                    "candidates": candidate_descriptions,
                    "filter_attributes": filter_attributes,
                    "existing_loc_id": existing_loc_id,
                    "existing_candidate": (
                        existing_annotation if append_existing_candidate else None
                    ),
                }
            )

        @self.app.route("/save_annotation", methods=["POST"])
        def save_annotation():
            data = request.json
            session_id = data["session_id"]
            doc_index = data["doc_index"]
            annotation = data["annotation"]

            session = self.load_session_from_cache(session_id)
            if not session:
                return jsonify({"error": "Session not found"}), 404

            doc = session["documents"][doc_index]
            toponyms = doc["toponyms"]
            # Find the toponym to update
            toponym = next(
                (
                    t
                    for t in toponyms
                    if t["start"] == annotation["start"]
                    and t["end"] == annotation["end"]
                ),
                None,
            )
            if not toponym:
                return jsonify({"error": "Toponym not found"}), 404

            # Update the loc_id
            toponym["loc_id"] = (
                annotation["loc_id"] if annotation["loc_id"] is not None else None
            )

            # Get the "one_sense_per_discourse" setting
            one_sense_per_discourse = session.get("settings", {}).get(
                "one_sense_per_discourse", False
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

            # Update last_updated timestamp
            session["last_updated"] = datetime.now().isoformat()

            # Save session
            session_file_path = os.path.join(self.cache_dir, f"{session_id}.json")
            with open(session_file_path, "w", encoding="utf-8") as f:
                json.dump(session, f, ensure_ascii=False, indent=4)

            # Recalculate progress for the current document
            total_toponyms = len(toponyms)
            annotated_toponyms = sum(1 for t in toponyms if t["loc_id"] != "")
            progress_percentage = (
                (annotated_toponyms / total_toponyms) * 100 if total_toponyms > 0 else 0
            )

            return jsonify(
                {
                    "status": "success",
                    "annotated_toponyms": annotated_toponyms,
                    "total_toponyms": total_toponyms,
                    "progress_percentage": progress_percentage,
                }
            )

        @self.app.route("/download_annotations/<session_id>")
        def download_annotations(session_id):
            session = self.load_session_from_cache(session_id)
            if not session:
                return "Session not found.", 404

            # Prepare annotations file for download
            annotations_data = session

            # Create a temporary file
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".json", mode="w+", encoding="utf-8"
            ) as temp_file:
                temp_file_name = temp_file.name  # Store the file name to use it later
                json.dump(annotations_data, temp_file, ensure_ascii=False, indent=4)

            # Ensure the file is deleted after some delay
            @after_this_request
            def remove_file(response):
                def delayed_delete(file_path):
                    os.remove(file_path)

                # Delay the deletion to ensure the file is no longer in use
                threading.Timer(1, delayed_delete, args=[temp_file_name]).start()
                return response

            # Send the file to the client
            return send_file(
                temp_file_name,
                as_attachment=True,
                download_name=f"annotations_{session_id}.json",
            )

        @self.app.route("/delete_session/<session_id>", methods=["POST"])
        def delete_session(session_id):
            session_file_path = os.path.join(self.cache_dir, f"{session_id}.json")
            if os.path.exists(session_file_path):
                os.remove(session_file_path)
                # Remove from sessions dictionary
                self.sessions.pop(session_id, None)
                # Issue 4 Fix: Redirect back to continue_session page
                return jsonify({"status": "success"})
            else:
                return jsonify({"status": "error", "message": "Session not found."})

        @self.app.route("/add_documents", methods=["POST"])
        def add_documents():
            session_id = request.form.get("session_id")
            session = self.load_session_from_cache(session_id)
            if not session:
                return jsonify({"status": "error", "message": "Session not found."})

            uploaded_files = request.files.getlist("files[]")
            selected_spacy_model = request.form.get("spacy_model")

            if not uploaded_files or not selected_spacy_model:
                return jsonify(
                    {"status": "error", "message": "No files or SpaCy model selected."}
                )

            # Re-initialize nlp with selected model
            self.nlp = self.setup_spacy(selected_spacy_model)

            # Process uploaded files
            for file in uploaded_files:
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
                session["documents"].append(
                    {
                        "filename": filename,
                        "spacy_model": selected_spacy_model,
                        "text": text,
                        "toponyms": toponyms,
                    }
                )

            # Save updated session
            session_file_path = os.path.join(self.cache_dir, f"{session_id}.json")
            with open(session_file_path, "w", encoding="utf-8") as f:
                json.dump(session, f, ensure_ascii=False, indent=4)

            return jsonify({"status": "success"})

        @self.app.route("/remove_document", methods=["POST"])
        def remove_document():
            data = request.json
            session_id = data.get("session_id")
            doc_index = int(data.get("doc_index"))

            session = self.load_session_from_cache(session_id)
            if not session:
                return jsonify({"status": "error", "message": "Session not found."})

            if 0 <= doc_index < len(session["documents"]):
                # Remove the document
                del session["documents"][doc_index]

                # Save updated session
                session_file_path = os.path.join(self.cache_dir, f"{session_id}.json")
                with open(session_file_path, "w", encoding="utf-8") as f:
                    json.dump(session, f, ensure_ascii=False, indent=4)

                return jsonify({"status": "success"})
            else:
                return jsonify(
                    {"status": "error", "message": "Invalid document index."}
                )

        @self.app.route("/delete_annotation", methods=["POST"])
        def delete_annotation():
            data = request.json
            session_id = data["session_id"]
            doc_index = data["doc_index"]
            start = data["start"]
            end = data["end"]

            session = self.load_session_from_cache(session_id)
            if not session:
                return jsonify({"error": "Session not found"}), 404

            doc = session["documents"][doc_index]
            toponyms = doc["toponyms"]
            # Find the toponym to delete
            toponym = next(
                (t for t in toponyms if t["start"] == start and t["end"] == end),
                None,
            )
            if not toponym:
                return jsonify({"error": "Toponym not found"}), 404

            # Remove the toponym
            toponyms.remove(toponym)

            # Update last_updated timestamp
            session["last_updated"] = datetime.now().isoformat()

            # Save session
            session_file_path = os.path.join(self.cache_dir, f"{session_id}.json")
            with open(session_file_path, "w", encoding="utf-8") as f:
                json.dump(session, f, ensure_ascii=False, indent=4)

            # Recalculate progress for the current document
            total_toponyms = len(toponyms)
            annotated_toponyms = sum(1 for t in toponyms if t["loc_id"] != "")
            progress_percentage = (
                (annotated_toponyms / total_toponyms) * 100 if total_toponyms > 0 else 0
            )

            return jsonify(
                {
                    "status": "success",
                    "annotated_toponyms": annotated_toponyms,
                    "total_toponyms": total_toponyms,
                    "progress_percentage": progress_percentage,
                }
            )

        @self.app.route("/edit_annotation", methods=["POST"])
        def edit_annotation():
            data = request.json
            session_id = data["session_id"]
            doc_index = data["doc_index"]
            old_start = data["old_start"]
            old_end = data["old_end"]
            new_start = data["new_start"]
            new_end = data["new_end"]
            new_text = data["new_text"]

            session = self.load_session_from_cache(session_id)
            if not session:
                return jsonify({"error": "Session not found"}), 404

            doc = session["documents"][doc_index]
            toponyms = doc["toponyms"]

            # Find the toponym to edit
            toponym = next(
                (
                    t
                    for t in toponyms
                    if t["start"] == old_start and t["end"] == old_end
                ),
                None,
            )
            if not toponym:
                return jsonify({"error": "Toponym not found"}), 404

            # Update the toponym
            toponym["start"] = new_start
            toponym["end"] = new_end
            toponym["text"] = new_text

            # Update last_updated timestamp
            session["last_updated"] = datetime.now().isoformat()

            # Save session
            session_file_path = os.path.join(self.cache_dir, f"{session_id}.json")
            with open(session_file_path, "w", encoding="utf-8") as f:
                json.dump(session, f, ensure_ascii=False, indent=4)

            # Recalculate progress for the current document
            total_toponyms = len(toponyms)
            annotated_toponyms = sum(1 for t in toponyms if t["loc_id"] != "")
            progress_percentage = (
                (annotated_toponyms / total_toponyms) * 100 if total_toponyms > 0 else 0
            )

            return jsonify(
                {
                    "status": "success",
                    "annotated_toponyms": annotated_toponyms,
                    "total_toponyms": total_toponyms,
                    "progress_percentage": progress_percentage,
                }
            )

        @self.app.route("/create_annotation", methods=["POST"])
        def create_annotation():
            data = request.json
            session_id = data["session_id"]
            doc_index = data["doc_index"]
            start = data["start"]
            end = data["end"]
            text = data["text"]

            session = self.load_session_from_cache(session_id)
            if not session:
                return jsonify({"error": "Session not found"}), 404

            doc = session["documents"][doc_index]
            toponyms = doc["toponyms"]

            # Check if there is already an annotation at this position
            existing_toponym = next(
                (t for t in toponyms if t["start"] == start and t["end"] == end),
                None,
            )
            if existing_toponym:
                return jsonify({"error": "Toponym already exists"}), 400

            # Add new toponym
            toponym = {
                "text": text,
                "start": start,
                "end": end,
                "loc_id": "",  # Empty loc_id
            }
            toponyms.append(toponym)

            # Sort toponyms by start position
            toponyms.sort(key=lambda x: x["start"])

            # Update last_updated timestamp
            session["last_updated"] = datetime.now().isoformat()

            # Save session
            session_file_path = os.path.join(self.cache_dir, f"{session_id}.json")
            with open(session_file_path, "w", encoding="utf-8") as f:
                json.dump(session, f, ensure_ascii=False, indent=4)

            # Recalculate progress for the current document
            total_toponyms = len(toponyms)
            annotated_toponyms = sum(1 for t in toponyms if t["loc_id"] != "")
            progress_percentage = (
                (annotated_toponyms / total_toponyms) * 100 if total_toponyms > 0 else 0
            )

            return jsonify(
                {
                    "status": "success",
                    "annotated_toponyms": annotated_toponyms,
                    "total_toponyms": total_toponyms,
                    "progress_percentage": progress_percentage,
                }
            )

        @self.app.route("/get_document_text", methods=["POST"])
        def get_document_text():
            data = request.json
            session_id = data["session_id"]
            doc_index = data["doc_index"]

            session = self.load_session_from_cache(session_id)
            if not session:
                return jsonify({"status": "error", "error": "Session not found"}), 404

            doc = session["documents"][doc_index]

            # Prepare pre-annotated text
            pre_annotated_text = self.get_pre_annotated_text(
                doc["text"], doc["toponyms"]
            )

            return jsonify(
                {"status": "success", "pre_annotated_text": pre_annotated_text}
            )

        @self.app.route("/get_document_progress", methods=["POST"])
        def get_document_progress():
            data = request.json
            session_id = data["session_id"]
            doc_index = data["doc_index"]

            session = self.load_session_from_cache(session_id)
            if not session:
                return jsonify({"status": "error", "error": "Session not found"}), 404

            doc = session["documents"][doc_index]
            toponyms = doc["toponyms"]
            total_toponyms = len(toponyms)
            annotated_toponyms = sum(1 for t in toponyms if t["loc_id"] != "")
            progress_percentage = (
                (annotated_toponyms / total_toponyms) * 100 if total_toponyms > 0 else 0
            )

            return jsonify(
                {
                    "status": "success",
                    "annotated_toponyms": annotated_toponyms,
                    "total_toponyms": total_toponyms,
                    "progress_percentage": progress_percentage,
                }
            )

        @self.app.route("/get_session_settings", methods=["POST"])
        def get_session_settings():
            data = request.json
            session_id = data["session_id"]

            session = self.load_session_from_cache(session_id)
            if not session:
                return jsonify({"status": "error", "error": "Session not found"}), 404

            settings = session.get(
                "settings",
                {
                    "one_sense_per_discourse": False,
                    "placeholder_option": False,
                },
            )

            return jsonify({"status": "success", "settings": settings})

        @self.app.route("/update_settings", methods=["POST"])
        def update_settings():
            data = request.json
            session_id = data["session_id"]
            settings = data["settings"]

            session = self.load_session_from_cache(session_id)
            if not session:
                return jsonify({"error": "Session not found"}), 404

            # Update settings
            session["settings"] = settings

            # Save session
            session_file_path = os.path.join(self.cache_dir, f"{session_id}.json")
            with open(session_file_path, "w", encoding="utf-8") as f:
                json.dump(session, f, ensure_ascii=False, indent=4)

            return jsonify({"status": "success"})

    def get_cached_sessions(self):
        sessions = []
        for filename in os.listdir(self.cache_dir):
            if filename.endswith(".json") and not filename.endswith("_download.json"):
                session_file_path = os.path.join(self.cache_dir, filename)
                try:
                    with open(session_file_path, "r", encoding="utf-8") as f:
                        session_data = json.load(f)
                        session_id = session_data.get("session_id", filename[:-5])

                        # Format creation date
                        created_at = session_data.get("created_at", "Unknown")
                        try:
                            created_at_dt = datetime.fromisoformat(created_at)
                            created_at_formatted = created_at_dt.strftime(
                                "%Y-%m-%d %H:%M:%S"
                            )
                        except ValueError:
                            created_at_formatted = created_at

                        # Format last updated date
                        last_updated = session_data.get("last_updated", "Unknown")
                        try:
                            last_updated_dt = datetime.fromisoformat(last_updated)
                            last_updated_formatted = last_updated_dt.strftime(
                                "%Y-%m-%d %H:%M:%S"
                            )
                        except ValueError:
                            last_updated_formatted = last_updated

                        gazetteer = session_data.get("gazetteer", "Unknown")
                        num_documents = len(session_data.get("documents", []))
                        sessions.append(
                            {
                                "session_id": session_id,
                                "created_at": created_at_formatted,
                                "last_updated": last_updated_formatted,
                                "gazetteer": gazetteer,
                                "num_documents": num_documents,
                            }
                        )
                except Exception as e:
                    print(f"Failed to load session {filename}: {e}")
                    continue
        # Sort sessions by last updated date descending
        sessions.sort(key=lambda x: x["last_updated"], reverse=True)
        return sessions

    def load_session_from_cache(self, session_id):
        if session_id in self.sessions:
            return self.sessions[session_id]
        session_file_path = os.path.join(self.cache_dir, f"{session_id}.json")
        if os.path.exists(session_file_path):
            try:
                with open(session_file_path, "r", encoding="utf-8") as f:
                    session_data = json.load(f)
                    self.sessions[session_id] = session_data
                    return session_data
            except Exception as e:
                print(f"Failed to load session {session_id}: {e}")
                return None
        else:
            return None

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
