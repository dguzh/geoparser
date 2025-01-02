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
from flask_jsglue import JSGlue
from spacy.util import get_installed_models

from geoparser.annotator.annotator import GeoparserAnnotator
from geoparser.annotator.sessions_cache import SessionsCache
from geoparser.constants import DEFAULT_SESSION_SETTINGS, GAZETTEERS

app = Flask(
    __name__, template_folder=os.path.join(os.path.dirname(__file__), "templates")
)
app.config["SECRET_KEY"] = "dev"
jsglue = JSGlue(app)

annotator = GeoparserAnnotator()
sessions_cache = SessionsCache()
spacy_models = list(get_installed_models())


def get_session(gazetteer: str):
    session_id = uuid.uuid4().hex
    session = {
        "session_id": session_id,
        "created_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "gazetteer": gazetteer,
        "settings": DEFAULT_SESSION_SETTINGS,
        "documents": [],
    }
    return session


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/start_new_session")
def start_new_session():
    gazetteers = GAZETTEERS
    return render_template(
        "start_new_session.html",
        gazetteers=gazetteers,
        spacy_models=spacy_models,
    )


@app.get("/continue_session")
def continue_session():
    cached_sessions = sessions_cache.get_cached_sessions()
    return render_template("continue_session.html", cached_sessions=cached_sessions)


@app.get("/session/<session_id>/annotate")
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


@app.post("/session")
def create_session():
    uploaded_files = request.files.getlist("files[]")

    # Get selected gazetteer and spacy model
    selected_gazetteer = request.form.get("gazetteer")
    selected_spacy_model = request.form.get("spacy_model")

    # Re-initialize gazetteer with selected option
    annotator.gazetteer = annotator.setup_gazetteer(selected_gazetteer)

    # Process uploaded files and create a new session
    session = get_session(selected_gazetteer)
    for document in annotator.parse_files(
        uploaded_files, selected_spacy_model, apply_spacy=False
    ):
        session["documents"].append(document)

    # Save session to cache
    sessions_cache.save(session["session_id"], session)

    return redirect(url_for("annotate", session_id=session["session_id"], doc_index=0))


@app.post("/session/continue/cached")
def continue_session_cached():
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
    return redirect(url_for("annotate", session_id=selected_session_id, doc_index=0))


@app.post("/session/continue/file")
def continue_session_file():
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


@app.delete("/session/<session_id>")
def delete_session(session_id):
    success = sessions_cache.delete(session_id)
    if success:
        return jsonify({"status": "success"})
    else:
        return jsonify({"message": "Session not found.", "status": "error"}), 404


@app.post("/session/<session_id>/documents")
def add_documents(session_id):
    session = sessions_cache.load(session_id)
    if not session:
        return jsonify({"message": "Session not found.", "status": "error"}), 404

    uploaded_files = request.files.getlist("files[]")
    selected_spacy_model = request.form.get("spacy_model")

    if not uploaded_files or not selected_spacy_model:
        return (
            jsonify(
                {"message": "No files or SpaCy model selected.", "status": "error"}
            ),
            422,
        )

    # Process uploaded files
    for document in annotator.parse_files(
        uploaded_files, selected_spacy_model, apply_spacy=False
    ):
        session["documents"].append(document)

    # Save updated session
    sessions_cache.save(session_id, session)

    return jsonify({"status": "success"})


@app.get("/session/<session_id>/documents")
def get_documents(session_id):
    session = sessions_cache.load(session_id)
    if not session:
        return jsonify({"message": "Session not found.", "status": "error"}), 404

    docs = session["documents"]
    return jsonify(docs)


@app.post("/session/<session_id>/document/<doc_index>/parse")
def parse_document(session_id, doc_index):
    doc_index = int(doc_index)

    session = sessions_cache.load(session_id)
    if not session:
        return jsonify({"message": "Session not found", "status": "error"}), 404

    if doc_index >= len(session["documents"]):
        return jsonify({"message": "Invalid document index", "status": "error"}), 422

    doc = session["documents"][doc_index]
    if not doc.get("spacy_applied"):
        doc = annotator.parse_doc(doc)
        # reload toponyms in case the user has added some in the meantime
        old_toponyms = sessions_cache.load(session_id)["documents"][doc_index][
            "toponyms"
        ]
        spacy_toponyms = doc["toponyms"]
        doc["toponyms"] = annotator.merge_toponyms(old_toponyms, spacy_toponyms)
        # save parsed toponyms into session
        session["documents"][doc_index] = doc
        sessions_cache.save(session["session_id"], session)
        return jsonify({"status": "success", "parsed": True})
    return jsonify({"status": "success", "parsed": False})


@app.get("/session/<session_id>/document/<doc_index>/progress")
def get_document_progress(session_id, doc_index):
    doc_index = int(doc_index)

    session = sessions_cache.load(session_id)
    if not session:
        return jsonify({"error": "Session not found", "status": "error"}), 404

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


@app.get("/session/<session_id>/document/<doc_index>/text")
def get_document_text(session_id, doc_index):
    doc_index = int(doc_index)

    session = sessions_cache.load(session_id)
    if not session:
        return jsonify({"error": "Session not found", "status": "error"}), 404

    doc = session["documents"][doc_index]

    # Prepare pre-annotated text
    pre_annotated_text = annotator.get_pre_annotated_text(doc["text"], doc["toponyms"])

    return jsonify({"status": "success", "pre_annotated_text": pre_annotated_text})


@app.delete("/session/<session_id>/document/<doc_index>")
def delete_document(session_id, doc_index):
    doc_index = int(doc_index)

    session = sessions_cache.load(session_id)
    if not session:
        return jsonify({"message": "Session not found.", "status": "error"}), 404

    if 0 <= doc_index < len(session["documents"]):
        # Remove the document
        del session["documents"][doc_index]

        # Save updated session
        sessions_cache.save(session_id, session)

        return jsonify({"status": "success"})
    else:
        return jsonify({"message": "Invalid document index.", "status": "error"}), 422


@app.get("/session/<session_id>/document/<doc_index>/candidates")
def get_candidates(session_id, doc_index):
    doc_index = int(doc_index)
    start = int(request.args.get("start", 0))
    end = int(request.args.get("end", 0))
    toponym_text = request.args.get("text", "")
    query_text = request.args.get("query_text", "").strip()

    session = sessions_cache.load(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    doc = session["documents"][doc_index]
    toponym = annotator.get_toponym(doc["toponyms"], start, end)
    if not toponym:
        return jsonify({"error": "Toponym not found"}), 404

    return jsonify(annotator.get_candidates(toponym, toponym_text, query_text))


@app.post("/session/<session_id>/document/<doc_index>/annotation")
def create_annotation(session_id, doc_index):
    doc_index = int(doc_index)
    data = request.json
    start = data["start"]
    end = data["end"]
    text = data["text"]

    session = sessions_cache.load(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    doc = session["documents"][doc_index]
    toponyms = doc["toponyms"]

    # Check if there is already an annotation at this position
    existing_toponym = annotator.get_toponym(toponyms, start, end)
    if existing_toponym:
        return jsonify({"error": "Toponym already exists"}), 422

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


@app.get("/session/<session_id>/annotations/download")
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


@app.put("/session/<session_id>/document/<doc_index>/annotation")
def overwrite_annotation(session_id, doc_index):
    doc_index = int(doc_index)
    annotation = request.json

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


@app.patch("/session/<session_id>/document/<doc_index>/annotation")
def update_annotation(session_id, doc_index):
    doc_index = int(doc_index)
    data = request.json
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


@app.delete("/session/<session_id>/document/<doc_index>/annotation")
def delete_annotation(session_id, doc_index):
    doc_index = int(doc_index)
    data = request.json
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
        (annotated_toponyms / total_toponyms) * 100 if total_toponyms > 0 else 0.0
    )

    return jsonify(
        {
            "status": "success",
            "annotated_toponyms": annotated_toponyms,
            "total_toponyms": total_toponyms,
            "progress_percentage": progress_percentage,
        }
    )


@app.get("/session/<session_id>/settings")
def get_session_settings(session_id):
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

    return jsonify(settings)


@app.put("/session/<session_id>/settings")
def put_session_settings(session_id):
    settings = request.json

    session = sessions_cache.load(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    # Update settings
    session["settings"] = settings

    # Save session
    sessions_cache.save(session_id, session)

    return jsonify({"status": "success"})


def run(debug=False, use_reloader=False):  # pragma: no cover
    def open_browser():
        webbrowser.open_new("http://127.0.0.1:5000/")

    threading.Timer(1.0, open_browser).start()
    app.run(host="0.0.0.0", port=5000, debug=debug, use_reloader=use_reloader)
