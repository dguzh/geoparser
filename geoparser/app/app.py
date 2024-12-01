import json
import os
import tempfile
import threading
import uuid
import webbrowser
from datetime import datetime

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
from spacy.util import get_installed_models
from werkzeug.utils import secure_filename

from geoparser.annotator import GeoparserAnnotator
from geoparser.app.sessions_cache import SessionsCache
from geoparser.app.util import get_session
from geoparser.constants import GAZETTEERS

app = Flask(
    __name__, template_folder=os.path.join(os.path.dirname(__file__), "templates")
)
app.config["SECRET_KEY"] = "dev"

annotator = GeoparserAnnotator()
sessions_cache = SessionsCache()
spacy_models = list(get_installed_models())


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/start_new_session")
def start_new_session_get():
    gazetteers = GAZETTEERS
    return render_template(
        "start_new_session.html",
        gazetteers=gazetteers,
        spacy_models=spacy_models,
    )


@app.post("/start_new_session")
def start_new_session_post():
    uploaded_files = request.files.getlist("files[]")

    # Get selected gazetteer and spacy model
    selected_gazetteer = request.form.get("gazetteer")
    selected_spacy_model = request.form.get("spacy_model")

    # Re-initialize gazetteer with selected option
    annotator.gazetteer = annotator.setup_gazetteer(selected_gazetteer)

    # Process uploaded files and create a new session
    session = get_session(selected_gazetteer)
    for document in annotator.parse_files(uploaded_files, selected_spacy_model):
        session["documents"].append(document)

    # Save session to cache
    sessions_cache.save(session, session["session_id"])

    return redirect(url_for("annotate", session_id=session["session_id"], doc_index=0))


@app.get("/continue_session")
def continue_session_get():
    cached_sessions = sessions_cache.get_cached_sessions()
    return render_template("continue_session.html", cached_sessions=cached_sessions)


@app.post("/continue_session")
def continue_session_post():
    action = request.form.get("action")
    if action == "load_cached":
        selected_session_id = request.form.get("cached_session")
        if not selected_session_id:
            return redirect(url_for("continue_session"))

        # Load selected session directly without creating a new session
        session = sessions_cache.load(selected_session_id)
        if not session:
            return redirect(url_for("continue_session"))

        # Re-initialize gazetteer
        annotator.gazetteer = annotator.setup_gazetteer(session["gazetteer"])

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
            sessions_cache.save(session_id, session_data)

            # Re-initialize gazetteer
            annotator.gazetteer = annotator.setup_gazetteer(session_data["gazetteer"])

            # Redirect to annotate page
            return redirect(url_for("annotate", session_id=session_id, doc_index=0))
        else:
            return redirect(url_for("continue_session"))
    else:
        return redirect(url_for("continue_session"))


@app.get("/annotate/<session_id>")
def annotate(session_id):
    doc_index = int(request.args.get("doc_index", 0))
    session = sessions_cache.load(session_id)
    if not session:
        return redirect(url_for("index"))

    if doc_index >= len(session["documents"]):
        # If the document index is out of range, redirect to the first document
        return redirect(url_for("annotate", session_id=session_id, doc_index=0))

    doc = session["documents"][doc_index]

    # Prepare pre-annotated text
    pre_annotated_text = annotator.get_pre_annotated_text(doc["text"], doc["toponyms"])

    # Prepare documents list with progress
    documents = list(annotator.prepare_documents(session["documents"]))

    total_toponyms = len(doc["toponyms"])
    annotated_toponyms = sum(1 for t in doc["toponyms"] if t["loc_id"] != "")

    return render_template(
        "annotate.html",
        doc=doc,
        doc_index=doc_index,
        pre_annotated_text=pre_annotated_text,
        total_docs=len(session["documents"]),
        gazetteer=annotator.gazetteer,
        documents=documents,
        session_id=session_id,
        total_toponyms=total_toponyms,
        annotated_toponyms=annotated_toponyms,
        spacy_models=spacy_models,  # Include spaCy models for the modal
    )


@app.post("/get_candidates")
def get_candidates():
    data = request.json
    session_id = data["session_id"]
    doc_index = data["doc_index"]
    start = data["start"]
    end = data["end"]
    toponym_text = data["text"]
    query_text = data.get("query_text", "").strip()

    session = sessions_cache.load(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    doc = session["documents"][doc_index]
    toponym = annotator.get_toponym(doc["toponyms"], start, end)
    if not toponym:
        return jsonify({"error": "Toponym not found"}), 404

    return jsonify(annotator.get_candidates(toponym, toponym_text, query_text))


@app.post("/save_annotation")
def save_annotation():
    data = request.json
    session_id = data["session_id"]
    doc_index = data["doc_index"]
    annotation = data["annotation"]

    session = sessions_cache.load(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    doc = session["documents"][doc_index]
    toponyms = doc["toponyms"]
    # Find the toponym to update
    toponym = annotator.get_toponym(toponyms, annotation["start"], annotation["end"])
    if not toponym:
        return jsonify({"error": "Toponym not found"}), 404

    # Get the "one_sense_per_discourse" setting
    one_sense_per_discourse = session.get("settings", {}).get(
        "one_sense_per_discourse", False
    )
    doc["toponyms"] = annotator.annotate_toponyms(
        doc["toponyms"], annotation, one_sense_per_discourse
    )

    # Update last_updated timestamp
    session["last_updated"] = datetime.now().isoformat()

    # Save session
    sessions_cache.save(session_id, session)

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


@app.get("/download_annotations/<session_id>")
def download_annotations(session_id):
    session = sessions_cache.load(session_id)
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


@app.post("/delete_session/<session_id>")
def delete_session(session_id):
    success = sessions_cache.delete(session_id)
    if success:
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": "Session not found."})


@app.post("/add_documents")
def add_documents():
    session_id = request.form.get("session_id")
    session = sessions_cache.load(session_id)
    if not session:
        return jsonify({"status": "error", "message": "Session not found."})

    uploaded_files = request.files.getlist("files[]")
    selected_spacy_model = request.form.get("spacy_model")

    if not uploaded_files or not selected_spacy_model:
        return jsonify(
            {"status": "error", "message": "No files or SpaCy model selected."}
        )

    # Process uploaded files
    for document in annotator.parse_files(uploaded_files, selected_spacy_model):
        session["documents"].append(document)

    # Save updated session
    sessions_cache.save(session_id, session)

    return jsonify({"status": "success"})


@app.post("/remove_document")
def remove_document():
    data = request.json
    session_id = data.get("session_id")
    doc_index = int(data.get("doc_index"))

    session = sessions_cache.load(session_id)
    if not session:
        return jsonify({"status": "error", "message": "Session not found."})

    if 0 <= doc_index < len(session["documents"]):
        # Remove the document
        del session["documents"][doc_index]

        # Save updated session
        sessions_cache.save(session_id, session)

        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": "Invalid document index."})


@app.post("/delete_annotation")
def delete_annotation():
    data = request.json
    session_id = data["session_id"]
    doc_index = data["doc_index"]
    start = data["start"]
    end = data["end"]

    session = sessions_cache.load(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    doc = session["documents"][doc_index]
    toponyms = doc["toponyms"]
    # Find the toponym to delete
    toponym = annotator.get_toponym(toponyms, start, end)
    if not toponym:
        return jsonify({"error": "Toponym not found"}), 404

    doc = annotator.remove_toponym(doc, toponym)

    # Update last_updated timestamp
    session["last_updated"] = datetime.now().isoformat()

    # Save session
    sessions_cache.save(session_id, session)

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


@app.post("/edit_annotation")
def edit_annotation():
    data = request.json
    session_id = data["session_id"]
    doc_index = data["doc_index"]
    old_start = data["old_start"]
    old_end = data["old_end"]
    new_start = data["new_start"]
    new_end = data["new_end"]
    new_text = data["new_text"]

    session = sessions_cache.load(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    doc = session["documents"][doc_index]
    toponyms = doc["toponyms"]

    # Find the toponym to edit
    toponym = annotator.get_toponym(toponyms, old_start, old_end)
    if not toponym:
        return jsonify({"error": "Toponym not found"}), 404

    # Update the toponym
    toponym["start"] = new_start
    toponym["end"] = new_end
    toponym["text"] = new_text

    # Update last_updated timestamp
    session["last_updated"] = datetime.now().isoformat()

    # Save session
    sessions_cache.save(session_id, session)

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


@app.post("/create_annotation")
def create_annotation():
    data = request.json
    session_id = data["session_id"]
    doc_index = data["doc_index"]
    start = data["start"]
    end = data["end"]
    text = data["text"]

    session = sessions_cache(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    doc = session["documents"][doc_index]
    toponyms = doc["toponyms"]

    # Check if there is already an annotation at this position
    existing_toponym = annotator.get_toponym(toponyms, start, end)
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
    sessions_cache.save(session_id, session)

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


@app.post("/get_document_text")
def get_document_text():
    data = request.json
    session_id = data["session_id"]
    doc_index = data["doc_index"]

    session = sessions_cache.load(session_id)
    if not session:
        return jsonify({"status": "error", "error": "Session not found"}), 404

    doc = session["documents"][doc_index]

    # Prepare pre-annotated text
    pre_annotated_text = annotator.get_pre_annotated_text(doc["text"], doc["toponyms"])

    return jsonify({"status": "success", "pre_annotated_text": pre_annotated_text})


@app.post("/get_document_progress")
def get_document_progress():
    data = request.json
    session_id = data["session_id"]
    doc_index = data["doc_index"]

    session = sessions_cache.load(session_id)
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


@app.post("/get_session_settings")
def get_session_settings():
    data = request.json
    session_id = data["session_id"]

    session = sessions_cache.load(session_id)
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


@app.post("/update_settings")
def update_settings():
    data = request.json
    session_id = data["session_id"]
    settings = data["settings"]

    session = sessions_cache.load(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    # Update settings
    session["settings"] = settings

    # Save session
    sessions_cache.save(session_id, session)

    return jsonify({"status": "success"})


def run(debug=False, use_reloader=False):
    def open_browser():
        webbrowser.open_new("http://127.0.0.1:5000/")

    threading.Timer(1.0, open_browser).start()
    app.run(host="0.0.0.0", port=5000, debug=debug, use_reloader=use_reloader)
