import json
import os
import threading
import typing as t
import uuid
import webbrowser
from datetime import datetime
from io import StringIO

import uvicorn
from fastapi import Depends, FastAPI, Form, Request, UploadFile, status
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from spacy.util import get_installed_models

from geoparser.annotator.annotator import GeoparserAnnotator
from geoparser.annotator.exceptions import (
    DocumentNotFoundException,
    SessionNotFoundException,
    ToponymNotFoundException,
    document_exception_handler,
    session_exception_handler,
    toponym_exception_handler,
)
from geoparser.annotator.models.api import (
    Annotation,
    AnnotationEdit,
    CandidatesGet,
    SessionSettings,
)
from geoparser.annotator.sessions_cache import SessionsCache
from geoparser.constants import DEFAULT_SESSION_SETTINGS, GAZETTEERS

tags_metadata = [
    {
        "name": "pages",
        "description": "Navigation for different pages. Returns HTML templates",
    },
    {
        "name": "session",
        "description": "Management of user sessions.",
    },
    {
        "name": "document",
        "description": "Management of documents (as in parts of a session or an uploaded files).",
    },
    {
        "name": "candidates",
        "description": "Candidates for a specific toponym.",
    },
    {
        "name": "annotation",
        "description": "Toponym annotations.",
    },
    {
        "name": "settings",
        "description": "Settings on a session level.",
    },
]

app = FastAPI(
    title="Irchel Geoparser",
    summary="API docs for the Irchel Geoparser annotator.",
    openapi_tags=tags_metadata,
)
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")),
    name="static",
)
app.add_exception_handler(DocumentNotFoundException, document_exception_handler)
app.add_exception_handler(SessionNotFoundException, session_exception_handler)
app.add_exception_handler(ToponymNotFoundException, toponym_exception_handler)
templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "templates")
)

annotator = GeoparserAnnotator()
sessions_cache = SessionsCache()
spacy_models = list(get_installed_models())


def _get_session(session_id: str):
    return sessions_cache.load(session_id)


def get_session(session: t.Annotated[dict, Depends(_get_session)]):
    if not session:
        raise SessionNotFoundException
    return session


def _get_document(session: t.Annotated[dict, Depends(_get_session)], doc_index: int):
    if session is not None and doc_index < len(session["documents"]):
        return session["documents"][doc_index]


def get_document(session: t.Annotated[dict, Depends(get_session)], doc_index: int):
    if not session:
        raise SessionNotFoundException
    elif doc_index >= len(session["documents"]):
        raise DocumentNotFoundException
    return session["documents"][doc_index]


def create_new_session(gazetteer: str):
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


@app.get("/", tags=["pages"])
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="html/index.html")


@app.get("/start_new_session", tags=["pages"])
def start_new_session(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="html/start_new_session.html",
        context={"gazetteers": GAZETTEERS, "spacy_models": spacy_models},
    )


@app.get("/continue_session", tags=["pages"])
def continue_session(request: Request):
    cached_sessions = sessions_cache.get_cached_sessions()
    return templates.TemplateResponse(
        request=request,
        name="html/continue_session.html",
        context={"cached_sessions": cached_sessions},
    )


@app.get("/session/{session_id}/document/{doc_index}/annotate", tags=["pages"])
def annotate(
    request: Request,
    session: t.Annotated[dict, Depends(_get_session)],
    doc: t.Annotated[dict, Depends(_get_document)],
    doc_index: int = 0,
):
    if not session:
        return RedirectResponse(
            url=app.url_path_for("index"),
            status_code=status.HTTP_302_FOUND,
        )
    if not doc:
        # If the document index is out of range, redirect to the first document
        return RedirectResponse(
            url=app.url_path_for(
                "annotate", session_id=session["session_id"], doc_index=0
            ),
            status_code=status.HTTP_302_FOUND,
        )
    # Prepare pre-annotated text
    pre_annotated_text = annotator.get_pre_annotated_text(doc["text"], doc["toponyms"])
    # Prepare documents list with progress
    documents = list(annotator.prepare_documents(session["documents"]))
    total_toponyms = len(doc["toponyms"])
    annotated_toponyms = sum(1 for t in doc["toponyms"] if t["loc_id"] != "")
    return templates.TemplateResponse(
        request=request,
        name="html/annotate.html",
        context={
            "doc": doc,
            "doc_index": doc_index,
            "pre_annotated_text": pre_annotated_text,
            "total_docs": len(session["documents"]),
            "gazetteer": annotator.gazetteer,
            "documents": documents,
            "session_id": session["session_id"],
            "total_toponyms": total_toponyms,
            "annotated_toponyms": annotated_toponyms,
            "spacy_models": spacy_models,  # Include spaCy models for the modal
        },
    )


@app.post("/session", tags=["session"])
def create_session(
    files: list[UploadFile],
    gazetteer: t.Annotated[str, Form()],
    spacy_model: t.Annotated[str, Form()],
):
    # Re-initialize gazetteer with selected option
    annotator.gazetteer = annotator.setup_gazetteer(gazetteer)
    # Process uploaded files and create a new session
    session = create_new_session(gazetteer)
    for document in annotator.parse_files(files, spacy_model, apply_spacy=False):
        session["documents"].append(document)
    # Save session to cache
    sessions_cache.save(session["session_id"], session)
    return RedirectResponse(
        url=app.url_path_for("annotate", session_id=session["session_id"], doc_index=0),
        status_code=status.HTTP_302_FOUND,
    )


@app.post("/session/continue/cached", tags=["session"])
def continue_session_cached(session_id: t.Annotated[str, Form()]):
    # Load selected session directly without creating a new session
    session = _get_session(session_id)
    if not session:
        return RedirectResponse(
            app.url_path_for("continue_session"), status_code=status.HTTP_302_FOUND
        )
    # Re-initialize gazetteer
    annotator.gazetteer = annotator.setup_gazetteer(session["gazetteer"])
    # Redirect to annotate page
    return RedirectResponse(
        app.url_path_for("annotate", session_id=session["session_id"], doc_index=0),
        status_code=status.HTTP_302_FOUND,
    )


@app.post("/session/continue/file", tags=["session"])
def continue_session_file(session_file: t.Optional[UploadFile] = None):
    # Handle uploaded session file
    if session_file and session_file.filename:
        session_data = json.loads(session_file.file.read().decode())
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
        return RedirectResponse(
            app.url_path_for("annotate", session_id=session_id, doc_index=0),
            status_code=status.HTTP_302_FOUND,
        )
    else:
        return RedirectResponse(
            app.url_path_for("continue_session"), status_code=status.HTTP_302_FOUND
        )


@app.delete("/session/{session_id}", tags=["session"])
def delete_session(session: t.Annotated[dict, Depends(get_session)]):
    sessions_cache.delete(session["session_id"])
    return JSONResponse({"status": "success"})


@app.post("/session/{session_id}/documents", tags=["document"])
def add_documents(
    session: t.Annotated[dict, Depends(get_session)],
    spacy_model: t.Annotated[str, Form()],
    files: t.Optional[list[UploadFile]] = None,
):
    if not files:
        return JSONResponse(
            {"message": "No files selected.", "status": "error"},
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    # Process uploaded files
    for document in annotator.parse_files(files, spacy_model, apply_spacy=False):
        session["documents"].append(document)
    # Save updated session
    sessions_cache.save(session["session_id"], session)
    return JSONResponse({"status": "success"})


@app.get("/session/{session_id}/documents", tags=["document"])
def get_documents(session: t.Annotated[dict, Depends(get_session)]):
    docs = session["documents"]
    return JSONResponse(docs)


@app.post("/session/{session_id}/document/{doc_index}/parse", tags=["document"])
def parse_document(
    session: t.Annotated[dict, Depends(get_session)],
    doc: t.Annotated[dict, Depends(get_document)],
    doc_index: int,
):
    if not doc.get("spacy_applied"):
        doc = annotator.parse_doc(doc)
        # reload session in case there have been changes to it in the meantime
        session = sessions_cache.load(session["session_id"])
        # merge toponyms in case the user has added some in the meantime
        old_toponyms = session["documents"][doc_index]["toponyms"]
        spacy_toponyms = doc["toponyms"]
        doc["toponyms"] = annotator.merge_toponyms(old_toponyms, spacy_toponyms)
        # save parsed toponyms into session
        session["documents"][doc_index] = doc
        sessions_cache.save(session["session_id"], session)
        return JSONResponse({"status": "success", "parsed": True})
    return JSONResponse({"status": "success", "parsed": False})


@app.get("/session/{session_id}/document/{doc_index}/progress", tags=["document"])
def get_document_progress(
    doc: t.Annotated[dict, Depends(get_document)],
):
    toponyms = doc["toponyms"]
    total_toponyms = len(toponyms)
    annotated_toponyms = sum(1 for t in toponyms if t["loc_id"] != "")
    progress_percentage = (
        (annotated_toponyms / total_toponyms) * 100 if total_toponyms > 0 else 0
    )
    return JSONResponse(
        {
            "status": "success",
            "annotated_toponyms": annotated_toponyms,
            "total_toponyms": total_toponyms,
            "progress_percentage": progress_percentage,
        }
    )


@app.get("/session/{session_id}/document/{doc_index}/text", tags=["document"])
def get_document_text(
    doc: t.Annotated[dict, Depends(get_document)],
):
    # Prepare pre-annotated text
    pre_annotated_text = annotator.get_pre_annotated_text(doc["text"], doc["toponyms"])
    return JSONResponse({"status": "success", "pre_annotated_text": pre_annotated_text})


@app.delete(
    "/session/{session_id}/document/{doc_index}",
    tags=["document"],
    dependencies=[Depends(get_document)],
)
def delete_document(session: t.Annotated[dict, Depends(get_session)], doc_index: int):
    # Remove the document
    del session["documents"][doc_index]
    # Save updated session
    sessions_cache.save(session["session_id"], session)
    return JSONResponse({"status": "success"})


@app.post(
    "/session/{session_id}/document/{doc_index}/get_candidates", tags=["candidates"]
)
def get_candidates(
    doc: t.Annotated[dict, Depends(get_document)],
    candidates_request: CandidatesGet,
):
    toponym = annotator.get_toponym(
        doc["toponyms"], candidates_request.start, candidates_request.end
    )
    if not toponym:
        raise ToponymNotFoundException

    return JSONResponse(
        annotator.get_candidates(
            toponym, candidates_request.text, candidates_request.query_text
        )
    )


@app.post("/session/{session_id}/document/{doc_index}/annotation", tags=["annotation"])
def create_annotation(
    session: t.Annotated[dict, Depends(get_session)],
    doc: t.Annotated[dict, Depends(get_document)],
    annotation: Annotation,
):
    toponyms = doc["toponyms"]
    # Check if there is already an annotation at this position
    existing_toponym = annotator.get_toponym(toponyms, annotation.start, annotation.end)
    if existing_toponym:
        return JSONResponse(
            {"error": "Toponym already exists"},
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    # Add new toponym
    toponym = {
        "text": annotation.text,
        "start": annotation.start,
        "end": annotation.end,
        "loc_id": "",  # Empty loc_id
    }
    toponyms.append(toponym)

    # Sort toponyms by start position
    toponyms.sort(key=lambda x: x["start"])
    # Update last_updated timestamp
    session["last_updated"] = datetime.now().isoformat()
    # Save session
    sessions_cache.save(session["session_id"], session)
    # Recalculate progress for the current document
    total_toponyms = len(toponyms)
    annotated_toponyms = sum(1 for t in toponyms if t["loc_id"] != "")
    progress_percentage = (
        (annotated_toponyms / total_toponyms) * 100 if total_toponyms > 0 else 0
    )
    return JSONResponse(
        {
            "status": "success",
            "annotated_toponyms": annotated_toponyms,
            "total_toponyms": total_toponyms,
            "progress_percentage": progress_percentage,
        }
    )


@app.get("/session/{session_id}/annotations/download", tags=["annotation"])
def download_annotations(annotations_data: t.Annotated[dict, Depends(get_session)]):
    # Prepare annotations file for download
    file_content = json.dumps(annotations_data, ensure_ascii=False, indent=4)
    # Send the file to the client
    session_id = annotations_data["session_id"]
    return StreamingResponse(
        StringIO(file_content),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="annotations_{session_id}.json"'
        },
    )


@app.put("/session/{session_id}/document/{doc_index}/annotation", tags=["annotation"])
def overwrite_annotation(
    session: t.Annotated[dict, Depends(get_session)],
    doc: t.Annotated[dict, Depends(get_document)],
    annotation: Annotation,
):
    toponyms = doc["toponyms"]
    # Find the toponym to update
    toponym = annotator.get_toponym(toponyms, annotation.start, annotation.end)
    if not toponym:
        raise ToponymNotFoundException
    # Get the "one_sense_per_discourse" setting
    one_sense_per_discourse = session.get("settings", {}).get(
        "one_sense_per_discourse", False
    )
    doc["toponyms"] = annotator.annotate_toponyms(
        doc["toponyms"], annotation.model_dump(), one_sense_per_discourse
    )
    # Update last_updated timestamp
    session["last_updated"] = datetime.now().isoformat()
    # Save session
    sessions_cache.save(session["session_id"], session)
    # Recalculate progress for the current document
    total_toponyms = len(toponyms)
    annotated_toponyms = sum(1 for t in toponyms if t["loc_id"] != "")
    progress_percentage = (
        (annotated_toponyms / total_toponyms) * 100 if total_toponyms > 0 else 0
    )
    return JSONResponse(
        {
            "status": "success",
            "annotated_toponyms": annotated_toponyms,
            "total_toponyms": total_toponyms,
            "progress_percentage": progress_percentage,
        }
    )


@app.patch("/session/{session_id}/document/{doc_index}/annotation", tags=["annotation"])
def update_annotation(
    session: t.Annotated[dict, Depends(get_session)],
    doc: t.Annotated[dict, Depends(get_document)],
    annotation: AnnotationEdit,
):
    toponyms = doc["toponyms"]
    # Find the toponym to edit
    toponym = annotator.get_toponym(toponyms, annotation.old_start, annotation.old_end)
    if not toponym:
        raise ToponymNotFoundException
    # Update the toponym
    toponym["start"] = annotation.new_start
    toponym["end"] = annotation.new_end
    toponym["text"] = annotation.new_text
    # Update last_updated timestamp
    session["last_updated"] = datetime.now().isoformat()
    # Save session
    sessions_cache.save(session["session_id"], session)
    # Recalculate progress for the current document
    total_toponyms = len(toponyms)
    annotated_toponyms = sum(1 for t in toponyms if t["loc_id"] != "")
    progress_percentage = (
        (annotated_toponyms / total_toponyms) * 100 if total_toponyms > 0 else 0
    )
    return JSONResponse(
        {
            "status": "success",
            "annotated_toponyms": annotated_toponyms,
            "total_toponyms": total_toponyms,
            "progress_percentage": progress_percentage,
        }
    )


@app.delete(
    "/session/{session_id}/document/{doc_index}/annotation", tags=["annotation"]
)
def delete_annotation(
    session: t.Annotated[dict, Depends(get_session)],
    doc: t.Annotated[dict, Depends(get_document)],
    start: int,
    end: int,
):
    annotation = Annotation(start=start, end=end)
    toponyms = doc["toponyms"]
    # Find the toponym to delete
    toponym = annotator.get_toponym(toponyms, annotation.start, annotation.end)
    if not toponym:
        raise ToponymNotFoundException
    doc = annotator.remove_toponym(doc, toponym)
    # Update last_updated timestamp
    session["last_updated"] = datetime.now().isoformat()
    # Save session
    sessions_cache.save(session["session_id"], session)
    # Recalculate progress for the current document
    total_toponyms = len(toponyms)
    annotated_toponyms = sum(1 for t in toponyms if t["loc_id"] != "")
    progress_percentage = (
        (annotated_toponyms / total_toponyms) * 100 if total_toponyms > 0 else 0.0
    )
    return JSONResponse(
        {
            "status": "success",
            "annotated_toponyms": annotated_toponyms,
            "total_toponyms": total_toponyms,
            "progress_percentage": progress_percentage,
        }
    )


@app.get("/session/{session_id}/settings", tags=["settings"])
def get_session_settings(session: t.Annotated[dict, Depends(get_session)]):
    settings = session.get("settings", DEFAULT_SESSION_SETTINGS)
    return JSONResponse(settings)


@app.put("/session/{session_id}/settings", tags=["settings"])
def put_session_settings(
    session: t.Annotated[dict, Depends(get_session)], session_settings: SessionSettings
):
    # Update settings
    session["settings"] = session_settings.model_dump()
    # Save session
    sessions_cache.save(session["session_id"], session)
    return JSONResponse({"status": "success"})


def run(use_reloader=False):  # pragma: no cover
    def open_browser():
        webbrowser.open_new("http://127.0.0.1:5000/")

    threading.Timer(1.0, open_browser).start()
    uvicorn.run(app, host="0.0.0.0", port=5000, reload=use_reloader)
