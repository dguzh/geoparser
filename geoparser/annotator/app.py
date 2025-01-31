import json
import os
import threading
import typing as t
import webbrowser
from datetime import datetime
from io import StringIO

import uvicorn
from fastapi import Depends, FastAPI, Form, Request, Response, UploadFile, status
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from spacy.util import get_installed_models
from sqlmodel import Session as DBSession

from geoparser import Geoparser
from geoparser.annotator.db.crud import (
    DocumentRepository,
    SessionRepository,
    SessionSettingsRepository,
    ToponymRepository,
)
from geoparser.annotator.db.db import create_db_and_tables, get_db
from geoparser.annotator.db.models import (
    SessionCreate,
    SessionForTemplate,
    SessionSettingsBase,
    SessionSettingsUpdate,
    SessionUpdate,
    ToponymBase,
    ToponymCreate,
    ToponymUpdate,
)
from geoparser.annotator.dependencies import get_document, get_session
from geoparser.annotator.exceptions import (
    DocumentNotFoundException,
    SessionNotFoundException,
    SessionSettingsNotFoundException,
    ToponymNotFoundException,
    document_exception_handler,
    session_exception_handler,
    sessionsettings_exception_handler,
    toponym_exception_handler,
)
from geoparser.annotator.metadata import tags_metadata
from geoparser.annotator.models.api import (
    AnnotationEdit,
    BaseResponse,
    CandidatesGet,
    ParsingResponse,
    PreAnnotatedTextResponse,
    ProgressResponse,
)
from geoparser.constants import GAZETTEERS

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
app.add_exception_handler(SessionNotFoundException, session_exception_handler)
app.add_exception_handler(
    SessionSettingsNotFoundException, sessionsettings_exception_handler
)
app.add_exception_handler(DocumentNotFoundException, document_exception_handler)
app.add_exception_handler(ToponymNotFoundException, toponym_exception_handler)
templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "templates")
)

geoparser = Geoparser()
spacy_models = list(get_installed_models())


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
def continue_session(db: t.Annotated[DBSession, Depends(get_db)], request: Request):
    cached_sessions = [
        SessionForTemplate(**session.model_dump(), num_documents=len(session.documents))
        for session in SessionRepository.read_all(db)
    ]
    return templates.TemplateResponse(
        request=request,
        name="html/continue_session.html",
        context={"cached_sessions": cached_sessions},
    )


@app.get("/session/{session_id}/document/{doc_index}/annotate", tags=["pages"])
def annotate(
    request: Request,
    db: t.Annotated[DBSession, Depends(get_db)],
    session_id: str,
    doc_index: int = 0,
):
    try:
        session = get_session(db, session_id)
    except SessionNotFoundException:
        return RedirectResponse(
            url=app.url_path_for("index"),
            status_code=status.HTTP_302_FOUND,
        )
    try:
        doc = get_document(session, doc_index)
    except DocumentNotFoundException:
        # If the document index is out of range, redirect to the first document
        return RedirectResponse(
            url=app.url_path_for("annotate", session_id=session.id, doc_index=0),
            status_code=status.HTTP_302_FOUND,
        )
    # Prepare pre-annotated text
    pre_annotated_text = DocumentRepository.get_pre_annotated_text(db, doc.id)
    # Prepare documents list with progress
    documents = DocumentRepository.get_progress(db, session_id=session.id)
    total_toponyms = len(doc.toponyms)
    annotated_toponyms = sum(t.loc_id != "" for t in doc.toponyms)
    return templates.TemplateResponse(
        request=request,
        name="html/annotate.html",
        context={
            "doc": doc,
            "doc_index": doc_index,
            "pre_annotated_text": pre_annotated_text,
            "total_docs": len(session.documents),
            "gazetteer": geoparser.gazetteer,
            "documents": documents,
            "session_id": session.id,
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
    db: t.Annotated[DBSession, Depends(get_db)],
):
    # Re-initialize gazetteer with selected option
    geoparser.gazetteer = geoparser.setup_gazetteer(gazetteer)
    session = SessionRepository.create(db, SessionCreate(gazetteer=gazetteer))
    DocumentRepository.create_from_text_files(
        db, geoparser, files, session.id, spacy_model, apply_spacy=False
    )
    return RedirectResponse(
        url=app.url_path_for("annotate", session_id=session.id, doc_index=0),
        status_code=status.HTTP_302_FOUND,
    )


@app.post("/session/continue/cached", tags=["session"])
def continue_session_cached(
    db: t.Annotated[DBSession, Depends(get_db)], session_id: t.Annotated[str, Form()]
):
    # Load selected session directly without creating a new session
    try:
        session = get_session(db, session_id)
    except SessionNotFoundException:
        return RedirectResponse(
            app.url_path_for("continue_session"), status_code=status.HTTP_302_FOUND
        )
    # Re-initialize gazetteer
    geoparser.gazetteer = geoparser.setup_gazetteer(session.gazetteer)
    # Redirect to annotate page
    return RedirectResponse(
        app.url_path_for("annotate", session_id=session.id, doc_index=0),
        status_code=status.HTTP_302_FOUND,
    )


@app.post("/session/continue/file", tags=["session"])
def continue_session_file(
    db: t.Annotated[DBSession, Depends(get_db)],
    session_file: t.Optional[UploadFile] = None,
):
    # Handle uploaded session file
    if session_file and session_file.filename:
        # Save session to cache
        session = SessionRepository.create_from_json(
            db, session_file.file.read().decode()
        )
        # Re-initialize gazetteer
        geoparser.gazetteer = geoparser.setup_gazetteer(session.gazetteer)
        # Redirect to annotate page
        return RedirectResponse(
            app.url_path_for("annotate", session_id=session.id, doc_index=0),
            status_code=status.HTTP_302_FOUND,
        )
    else:
        return RedirectResponse(
            app.url_path_for("continue_session"), status_code=status.HTTP_302_FOUND
        )


@app.delete("/session/{session_id}", tags=["session"])
def delete_session(
    db: t.Annotated[DBSession, Depends(get_db)],
    session: t.Annotated[dict, Depends(get_session)],
):
    SessionRepository.delete(db, session.id)
    return BaseResponse()


@app.post("/session/{session_id}/documents", tags=["document"])
def add_documents(
    response: Response,
    db: t.Annotated[DBSession, Depends(get_db)],
    session: t.Annotated[dict, Depends(get_session)],
    spacy_model: t.Annotated[str, Form()],
    files: t.Optional[list[UploadFile]] = None,
):
    if not files:
        response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        return BaseResponse(message="No files selected.", status="error")
    DocumentRepository.create_from_text_files(
        db, geoparser, files, session.id, spacy_model, apply_spacy=False
    )
    return BaseResponse()


@app.get("/session/{session_id}/documents", tags=["document"])
def get_documents(session: t.Annotated[dict, Depends(get_session)]):
    docs = session.documents
    return docs


@app.post("/session/{session_id}/document/{doc_index}/parse", tags=["document"])
def parse_document(
    db: t.Annotated[DBSession, Depends(get_db)],
    doc: t.Annotated[dict, Depends(get_document)],
):
    if not doc.spacy_applied:
        doc = DocumentRepository.parse(db, geoparser, doc.id)
        return ParsingResponse(parsed=True)
    return ParsingResponse(parsed=False)


@app.get("/session/{session_id}/document/{doc_index}/progress", tags=["document"])
def get_document_progress(
    db: t.Annotated[DBSession, Depends(get_db)],
    doc: t.Annotated[dict, Depends(get_document)],
):
    return ProgressResponse(**DocumentRepository.get_document_progress(db, doc.id))


@app.get("/session/{session_id}/document/{doc_index}/text", tags=["document"])
def get_document_text(
    db: t.Annotated[DBSession, Depends(get_db)],
    doc: t.Annotated[dict, Depends(get_document)],
):
    # Prepare pre-annotated text
    pre_annotated_text = DocumentRepository.get_pre_annotated_text(db, doc.id)
    return PreAnnotatedTextResponse(pre_annotated_text=pre_annotated_text)


@app.delete(
    "/session/{session_id}/document/{doc_index}",
    tags=["document"],
    dependencies=[Depends(get_document)],
)
def delete_document(
    db: t.Annotated[DBSession, Depends(get_db)],
    session: t.Annotated[dict, Depends(get_session)],
    doc_index: int,
):
    # Remove the document
    DocumentRepository.delete(db, session.documents[doc_index])
    return BaseResponse()


@app.post(
    "/session/{session_id}/document/{doc_index}/get_candidates", tags=["candidates"]
)
def get_candidates(
    doc: t.Annotated[dict, Depends(get_document)],
    candidates_request: CandidatesGet,
):
    return ToponymRepository.get_candidates(doc, geoparser, candidates_request)


@app.post("/session/{session_id}/document/{doc_index}/annotation", tags=["annotation"])
def create_annotation(
    db: t.Annotated[DBSession, Depends(get_db)],
    session: t.Annotated[dict, Depends(get_session)],
    doc: t.Annotated[dict, Depends(get_document)],
    annotation: ToponymBase,
):
    # Add new toponym
    ToponymRepository.create(
        db,
        ToponymCreate(text=annotation.text, start=annotation.start, end=annotation.end),
        additional={"document_id": doc.id},
    )
    SessionRepository.update(
        db, SessionUpdate(id=session.id, last_updated=datetime.now())
    )
    return ProgressResponse(**DocumentRepository.get_document_progress(db, doc.id))


@app.get("/session/{session_id}/annotations/download", tags=["annotation"])
def download_annotations(
    db: t.Annotated[DBSession, Depends(get_db)],
    session: t.Annotated[dict, Depends(get_session)],
):
    # Prepare annotations file for download
    file_content = json.dumps(
        SessionRepository.read_to_json(db, session.id), ensure_ascii=False, indent=4
    )
    # Send the file to the client
    return StreamingResponse(
        StringIO(file_content),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="annotations_{session.id}.json"'
        },
    )


@app.put("/session/{session_id}/document/{doc_index}/annotation", tags=["annotation"])
def overwrite_annotation(
    db: t.Annotated[DBSession, Depends(get_db)],
    session: t.Annotated[dict, Depends(get_session)],
    doc: t.Annotated[dict, Depends(get_document)],
    annotation: ToponymBase,
):
    ToponymRepository.annotate_many(db, doc, annotation)
    SessionRepository.update(
        db, SessionUpdate(id=session.id, last_updated=datetime.now())
    )
    return ProgressResponse(**DocumentRepository.get_document_progress(db, doc.id))


@app.patch("/session/{session_id}/document/{doc_index}/annotation", tags=["annotation"])
def update_annotation(
    db: t.Annotated[DBSession, Depends(get_db)],
    session: t.Annotated[dict, Depends(get_session)],
    doc: t.Annotated[dict, Depends(get_document)],
    annotation: AnnotationEdit,
):
    # Find the toponym to edit
    toponym = ToponymRepository.get_toponym(
        doc, annotation.old_start, annotation.old_end
    )
    # Update the toponym
    ToponymRepository.update(
        db,
        ToponymUpdate(
            id=toponym.id,
            start=annotation.new_start,
            end=annotation.new_end,
            text=annotation.new_text,
        ),
        document_id=doc.id,
    )
    # Update last_updated timestamp
    SessionRepository.update(
        db, SessionUpdate(id=session.id, last_updated=datetime.now())
    )
    return ProgressResponse(**DocumentRepository.get_document_progress(db, doc.id))


@app.delete(
    "/session/{session_id}/document/{doc_index}/annotation", tags=["annotation"]
)
def delete_annotation(
    db: t.Annotated[DBSession, Depends(get_db)],
    session: t.Annotated[dict, Depends(get_session)],
    doc: t.Annotated[dict, Depends(get_document)],
    start: int,
    end: int,
):
    # Find the toponym to delete
    toponym = ToponymRepository.get_toponym(doc, start, end)
    ToponymRepository.delete(db, toponym.id)
    # Update last_updated timestamp
    SessionRepository.update(
        db, SessionUpdate(id=session.id, last_updated=datetime.now())
    )
    return ProgressResponse(**DocumentRepository.get_document_progress(db, doc.id))


@app.get("/session/{session_id}/settings", tags=["settings"])
def get_session_settings(session: t.Annotated[dict, Depends(get_session)]):
    return session.settings


@app.put("/session/{session_id}/settings", tags=["settings"])
def put_session_settings(
    db: t.Annotated[DBSession, Depends(get_db)],
    session: t.Annotated[dict, Depends(get_session)],
    session_settings: SessionSettingsBase,
):
    # Update settings
    SessionSettingsRepository.update(
        db,
        SessionSettingsUpdate(id=session.settings.id, **session_settings.model_dump()),
    )
    return BaseResponse()


def run(use_reloader=False):  # pragma: no cover
    def open_browser():
        webbrowser.open_new("http://127.0.0.1:5000/")

    create_db_and_tables()
    threading.Timer(1.0, open_browser).start()
    uvicorn.run(app, host="0.0.0.0", port=5000, reload=use_reloader)
