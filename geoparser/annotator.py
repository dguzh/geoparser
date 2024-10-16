import json
import os
import threading
import webbrowser
from pathlib import Path

import spacy
from appdirs import user_data_dir
from flask import Flask, jsonify, redirect, render_template, request, send_file, url_for
from markupsafe import Markup
from spacy.util import get_installed_models

from geoparser.constants import GAZETTEERS
from geoparser.geoparser import Geoparser


class GeoparserAnnotator(Geoparser):
    def __init__(self, *args, **kwargs):
        super().__init__(spacy_model="en_core_web_sm", *args, **kwargs)
        template_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "templates")
        )
        self.app = Flask(__name__, template_folder=template_dir)
        self.app.config["SECRET_KEY"] = "dev"
        self.documents = []
        # Define the cache file path
        self.cache_dir = os.path.join(user_data_dir("geoparser", ""), "annotator")
        os.makedirs(self.cache_dir, exist_ok=True)  # Ensure the directory exists
        self.cache_file_path = os.path.join(self.cache_dir, "annotations.json")
        self.setup_routes()

    def run(self, debug=False):
        def open_browser():
            webbrowser.open_new("http://127.0.0.1:5000/")

        threading.Timer(1.0, open_browser).start()
        self.app.run(debug=debug, use_reloader=False)

    def setup_routes(self):
        @self.app.route("/")
        def index():
            return render_template("index.html")

        @self.app.route("/upload", methods=["GET", "POST"])
        def upload():
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

                # Process uploaded files
                self.process_uploaded_files(uploaded_files)

                # Handle uploaded annotation file
                annotation_file = request.files.get("annotation_file")
                if annotation_file and annotation_file.filename:
                    # Overwrite the cache with the uploaded annotations
                    annotations_data = json.load(annotation_file.stream)
                    with open(self.cache_file_path, "w", encoding="utf-8") as f:
                        json.dump(annotations_data, f, ensure_ascii=False, indent=4)
                    # Load annotations into self.documents
                    self.load_annotations()
                else:
                    # Load annotations from the cache if it exists
                    self.load_annotations()

                return redirect(url_for("annotate", doc_index=0))

            # Check if cache exists
            cache_exists = os.path.exists(self.cache_file_path)
            return render_template(
                "upload.html",
                gazetteers=gazetteers,
                spacy_models=spacy_models,
                cache_exists=cache_exists,
            )

        @self.app.route("/annotate")
        def annotate():
            doc_index = int(request.args.get("doc_index", 0))
            doc = self.documents[doc_index]
            doc_obj = doc.get("doc_obj")
            if not doc_obj:
                doc_obj = self.nlp(doc["text"])
                doc["doc_obj"] = doc_obj

            # Process all documents to calculate progress
            for doc_item in self.documents:
                if "doc_obj" not in doc_item:
                    doc_item["doc_obj"] = self.nlp(doc_item["text"])

                doc_obj_item = doc_item["doc_obj"]
                # Identify toponyms
                toponyms = doc_obj_item.toponyms
                doc_item["total_toponyms"] = len(toponyms)

                # Count annotated toponyms
                annotations = doc_item.get("annotations", [])
                annotated_toponym_set = set(
                    (ann["start"], ann["end"]) for ann in annotations
                )
                annotated_count = sum(
                    1
                    for toponym in toponyms
                    if (toponym.start_char, toponym.end_char) in annotated_toponym_set
                )
                doc_item["annotated_toponyms"] = annotated_count

            pre_annotated_text = self.get_pre_annotated_text(
                doc_obj, doc.get("annotations", [])
            )

            return render_template(
                "annotate.html",
                doc=doc,
                doc_index=doc_index,
                pre_annotated_text=pre_annotated_text,
                total_docs=len(self.documents),
                gazetteer=self.gazetteer,
                documents=self.documents,
            )

        @self.app.route("/get_candidates", methods=["POST"])
        def get_candidates():
            data = request.json
            doc_index = data["doc_index"]
            start = data["start"]
            end = data["end"]
            toponym_text = data["text"]
            query_text = data.get(
                "query_text", ""
            ).strip()  # Get query_text if provided

            doc = self.documents[doc_index]["doc_obj"]
            annotations = self.documents[doc_index]["annotations"]

            # Use query_text if provided, else use toponym_text
            search_text = query_text if query_text else toponym_text

            # Get candidate IDs and locations based on the search_text
            candidates = self.gazetteer.query_candidates(search_text)
            candidate_locations = self.gazetteer.query_location_info(candidates)

            # Prepare candidate descriptions and attributes
            candidate_descriptions = []
            for location in candidate_locations:
                description = self.gazetteer.get_location_description(location)
                candidate_descriptions.append(
                    {
                        "loc_id": location[self.gazetteer.config.location_identifier],
                        "description": description,
                        "attributes": location,  # Include all attributes for filtering
                    }
                )

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

            # Find existing annotation for this toponym
            existing_annotation = next(
                (
                    ann
                    for ann in annotations
                    if ann["start"] == start and ann["end"] == end
                ),
                None,
            )
            existing_loc_id = (
                existing_annotation["loc_id"] if existing_annotation else None
            )

            return jsonify(
                {
                    "candidates": candidate_descriptions,
                    "filter_attributes": filter_attributes,
                    "existing_loc_id": existing_loc_id,
                }
            )

        @self.app.route("/save_annotation", methods=["POST"])
        def save_annotation():
            data = request.json
            doc_index = data["doc_index"]
            annotation = data["annotation"]
            doc = self.documents[doc_index]
            annotations = doc.get("annotations", [])

            # Check if the annotation already exists
            for idx, existing_annotation in enumerate(annotations):
                if (
                    existing_annotation["start"] == annotation["start"]
                    and existing_annotation["end"] == annotation["end"]
                ):
                    # Update the existing annotation
                    annotations[idx] = annotation
                    break
            else:
                # If the annotation does not exist, append it
                annotations.append(annotation)

            doc["annotations"] = annotations
            self.save_annotations()  # Save to cache file

            # Recalculate progress for the current document
            doc_obj = doc["doc_obj"]
            toponyms = doc_obj.toponyms
            total_toponyms = len(toponyms)
            annotated_toponym_set = set(
                (ann["start"], ann["end"]) for ann in annotations
            )
            annotated_count = sum(
                1
                for toponym in toponyms
                if (toponym.start_char, toponym.end_char) in annotated_toponym_set
            )
            doc["total_toponyms"] = total_toponyms
            doc["annotated_toponyms"] = annotated_count

            return jsonify(
                {
                    "status": "success",
                    "annotated_toponyms": annotated_count,
                    "total_toponyms": total_toponyms,
                }
            )

        @self.app.route("/download_annotations")
        def download_annotations():
            if os.path.exists(self.cache_file_path):
                return send_file(self.cache_file_path, as_attachment=True)
            else:
                return "No annotations to download.", 404

        @self.app.route("/get_progress")
        def get_progress():
            progress = []
            for i, doc in enumerate(self.documents):
                doc_obj = doc.get("doc_obj")
                if doc_obj:
                    total_toponyms = len(doc_obj.toponyms)
                else:
                    total_toponyms = 0
                annotated_toponyms = len(doc["annotations"])
                progress.append(
                    {
                        "filename": doc["filename"],
                        "total_toponyms": total_toponyms,
                        "annotated_toponyms": annotated_toponyms,
                        "doc_index": i,
                    }
                )
            return jsonify({"progress": progress})

        @self.app.route("/clear_cache", methods=["POST"])
        def clear_cache():
            try:
                # Remove the cache file if it exists
                if os.path.exists(self.cache_file_path):
                    os.remove(self.cache_file_path)

                # Clear annotations from self.documents
                for doc in self.documents:
                    doc["annotations"] = []

                # Save the empty annotations to the cache
                self.save_annotations()

                return jsonify({"status": "success"})
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)})

    def process_uploaded_files(self, uploaded_files):
        self.documents = []
        for file in uploaded_files:
            text = file.read().decode("utf-8")
            self.documents.append(
                {"filename": file.filename, "text": text, "annotations": []}
            )

    def get_pre_annotated_text(self, doc_obj, doc_annotations):
        text = doc_obj.text
        html_parts = []
        last_idx = 0
        annotated_spans = set((ann["start"], ann["end"]) for ann in doc_annotations)

        for toponym in doc_obj.toponyms:
            # Escape the text before the toponym
            before_toponym = Markup.escape(text[last_idx : toponym.start_char])
            html_parts.append(before_toponym)

            # Check if the toponym has been annotated
            annotated = (toponym.start_char, toponym.end_char) in annotated_spans

            # Create the span for the toponym
            toponym_text = Markup.escape(toponym.text)
            span = Markup(
                '<span class="toponym {annotated_class}" data-start="{start}" data-end="{end}">{text}</span>'
            ).format(
                annotated_class="annotated" if annotated else "",
                start=toponym.start_char,
                end=toponym.end_char,
                text=toponym_text,
            )
            html_parts.append(span)
            last_idx = toponym.end_char
        # Append the remaining text after the last toponym
        after_toponym = Markup.escape(text[last_idx:])
        html_parts.append(after_toponym)
        # Combine all parts into a single Markup object
        html = Markup("").join(html_parts)
        return html

    def save_annotations(self):
        # Create a serializable copy of self.documents without non-serializable or unnecessary objects
        serializable_documents = []
        for doc in self.documents:
            doc_copy = doc.copy()
            # Remove non-serializable items
            if "doc_obj" in doc_copy:
                del doc_copy["doc_obj"]
            # Remove calculated attributes
            if "annotated_toponyms" in doc_copy:
                del doc_copy["annotated_toponyms"]
            if "total_toponyms" in doc_copy:
                del doc_copy["total_toponyms"]
            serializable_documents.append(doc_copy)

        # Save annotations to the cache file
        with open(self.cache_file_path, "w", encoding="utf-8") as f:
            json.dump(serializable_documents, f, ensure_ascii=False, indent=4)

    def load_annotations(self):
        if os.path.exists(self.cache_file_path):
            try:
                with open(self.cache_file_path, "r", encoding="utf-8") as f:
                    annotations_data = json.load(f)

                # Update self.documents with annotations from the cache
                doc_mapping = {doc["filename"]: doc for doc in self.documents}
                for cached_doc in annotations_data:
                    filename = cached_doc["filename"]
                    if filename in doc_mapping:
                        doc = doc_mapping[filename]
                        doc["annotations"] = cached_doc.get("annotations", [])
                        # Re-initialize 'doc_obj' if necessary
                        if "doc_obj" not in doc:
                            doc["doc_obj"] = self.nlp(doc["text"])
                    else:
                        # If the document is not in the current session, skip it
                        continue
            except (json.JSONDecodeError, ValueError):
                # Handle empty or invalid cache file
                print("Cache file is empty or invalid. Initializing annotations.")
                for doc in self.documents:
                    doc["annotations"] = []
                # Save empty annotations to the cache
                self.save_annotations()
        else:
            # Initialize annotations for each document
            for doc in self.documents:
                doc["annotations"] = []
