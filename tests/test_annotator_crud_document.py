import uuid
from contextlib import nullcontext

import pytest
from sqlmodel import Session as DBSession

from geoparser.annotator.db.crud import DocumentRepository, SessionRepository
from geoparser.annotator.db.models import (
    Document,
    DocumentCreate,
    DocumentUpdate,
    SessionCreate,
    Toponym,
    ToponymCreate,
)
from geoparser.annotator.exceptions import DocumentNotFoundException


def test_get_highest_index(test_db: DBSession):
    # setup: create a session to link the documents to
    session_create = SessionCreate(gazetteer="geonames")
    session = SessionRepository.create(test_db, session_create)
    assert (
        DocumentRepository.get_highest_index(test_db, session.id) == -1
    )  # No documents yet
    DocumentRepository.create(
        test_db,
        DocumentCreate(filename="doc1.txt", spacy_model="en_core_web_sm", text="Doc 1"),
        additional={"session_id": session.id},
    )
    assert (
        DocumentRepository.get_highest_index(test_db, session.id) == 0
    )  # First document has index 0
    DocumentRepository.create(
        test_db,
        DocumentCreate(filename="doc2.txt", spacy_model="en_core_web_sm", text="Doc 2"),
        additional={"session_id": session.id},
    )
    assert (
        DocumentRepository.get_highest_index(test_db, session.id) == 1
    )  # Second document has index 1


def test_reindex_documents(test_db: DBSession):
    # setup: create a session to link the documents to
    session_create = SessionCreate(gazetteer="geonames")
    session = SessionRepository.create(test_db, session_create)
    # Create three documents
    docs = [
        DocumentRepository.create(
            test_db,
            DocumentCreate(
                filename=f"doc{i}.txt", spacy_model="en_core_web_sm", text=f"Doc {i}"
            ),
            additional={"session_id": session.id},
        )
        for i in range(3)
    ]
    # Ensure doc_index is assigned correctly
    for i, doc in enumerate(docs):
        assert doc.doc_index == i
    # Delete the second document (index 1)
    DocumentRepository.delete(test_db, docs[1].id)
    # Reindex the documents
    DocumentRepository._reindex_documents(test_db, session.id)
    # Fetch updated documents
    updated_docs = DocumentRepository.read_all(test_db, session_id=session.id)
    # Ensure reindexing is correct (should be sequential)
    for i, doc in enumerate(updated_docs):
        assert doc.doc_index == i
        assert (
            doc
            == DocumentRepository.read_all(test_db, session_id=session.id, doc_index=i)[
                0
            ]
        )


@pytest.mark.parametrize("nested", [True, False])
def test_create(test_db: DBSession, nested: bool):
    # setup: create a session to link the document to
    session_create = SessionCreate(gazetteer="geonames")
    session = SessionRepository.create(test_db, session_create)
    # create the document
    document_create = DocumentCreate(
        filename="test.txt",
        spacy_model="en_core_web_sm",
        text="Andorra is nice.",
        toponyms=[ToponymCreate(text="Andorra", start=0, end=6)] if nested else [],
    )
    document = DocumentRepository.create(
        test_db, document_create, additional={"session_id": session.id}
    )
    db_document = DocumentRepository.read(test_db, document.id)
    assert type(document) is Document
    assert type(db_document) is Document
    assert db_document.model_dump(
        exclude=["id", "session_id", "doc_index"]
    ) == document_create.model_dump(exclude=["toponyms"])
    assert len(db_document.toponyms) == len(document_create.toponyms)
    if nested:
        for toponym in db_document.toponyms:
            assert type(toponym) is Toponym


@pytest.mark.parametrize("valid_id", [True, False])
def test_read(test_db: DBSession, valid_id: bool):
    # setup: create a session to link the document to
    session_create = SessionCreate(gazetteer="geonames")
    session = SessionRepository.create(test_db, session_create)
    # create document to read afterwards
    document_id = uuid.uuid4()
    if valid_id:
        document_create = DocumentCreate(
            filename="test.txt",
            spacy_model="en_core_web_sm",
            text="Andorra is nice.",
            toponyms=[ToponymCreate(text="Andorra", start=0, end=6)],
        )
        document = DocumentRepository.create(
            test_db, document_create, additional={"session_id": session.id}
        )
        document_id = document.id
    # read document
    with nullcontext() if valid_id else pytest.raises(DocumentNotFoundException):
        db_document = DocumentRepository.read(test_db, document_id)
        assert type(db_document) is Document
        assert db_document.model_dump(
            exclude=["id", "session_id", "doc_index"]
        ) == document_create.model_dump(exclude=["toponyms"])


def test_read_all(test_db: DBSession):
    # setup: create a session to link the document to
    session_create = SessionCreate(gazetteer="geonames")
    session = SessionRepository.create(test_db, session_create)
    # create first document
    document_create = DocumentCreate(
        filename="test.txt",
        spacy_model="en_core_web_sm",
        text="Andorra is nice.",
    )
    document1 = DocumentRepository.create(
        test_db, document_create, additional={"session_id": session.id}
    )
    after_first = DocumentRepository.read_all(test_db)
    assert len(after_first) == 1
    assert type(after_first[0]) is Document
    assert after_first[0].id == document1.id
    # create second document
    document2 = DocumentRepository.create(
        test_db, document_create, additional={"session_id": session.id}
    )
    after_second = DocumentRepository.read_all(test_db)
    assert len(after_second) == 2
    assert all(isinstance(doc, Document) for doc in after_second)
    assert {doc.id for doc in after_second} == {document1.id, document2.id}
    # filter by id
    filtered = DocumentRepository.read_all(test_db, id=document1.id)
    assert len(filtered) == 1
    assert type(filtered[0]) is Document
    assert filtered[0].id == document1.id


@pytest.mark.parametrize("valid_id", [True, False])
def test_update(test_db: DBSession, valid_id: bool):
    # setup: create a session to link the document to
    session_create = SessionCreate(gazetteer="geonames")
    session = SessionRepository.create(test_db, session_create)
    # create document to update afterwards
    document_id = uuid.uuid4()
    if valid_id:
        document_create = DocumentCreate(
            filename="test.txt",
            spacy_model="en_core_web_sm",
            text="Andorra is nice.",
        )
        document = DocumentRepository.create(
            test_db, document_create, additional={"session_id": session.id}
        )
        document_id = document.id
    with nullcontext() if valid_id else pytest.raises(DocumentNotFoundException):
        # check initial value
        db_document = DocumentRepository.read(test_db, document_id)
        assert db_document.filename == "test.txt"
        # check updated value
        DocumentRepository.update(
            test_db, DocumentUpdate(id=document_id, filename="updated.txt")
        )
        db_document = DocumentRepository.read(test_db, document_id)
        assert db_document.filename == "updated.txt"


@pytest.mark.parametrize("valid_id", [True, False])
def test_delete(test_db: DBSession, valid_id: bool):
    # setup: create a session to link the document to
    session_create = SessionCreate(gazetteer="geonames")
    session = SessionRepository.create(test_db, session_create)
    document_id = uuid.uuid4()
    # create document to delete afterwards
    if valid_id:
        document_create = DocumentCreate(
            filename="test.txt",
            spacy_model="en_core_web_sm",
            text="Andorra is nice.",
        )
        document = DocumentRepository.create(
            test_db, document_create, additional={"session_id": session.id}
        )
        document_id = document.id
    # document exists before deletion
    with nullcontext() if valid_id else pytest.raises(DocumentNotFoundException):
        assert DocumentRepository.read(test_db, document_id)
        DocumentRepository.delete(test_db, document_id)
    # document is gone
    with pytest.raises(DocumentNotFoundException):
        DocumentRepository.read(test_db, document_id)
