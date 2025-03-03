import io
import uuid
from contextlib import nullcontext

import pytest
from fastapi import UploadFile
from markupsafe import Markup
from sqlmodel import Session as DBSession

from geoparser import Geoparser
from geoparser.db.crud import DocumentRepository
from geoparser.db.models import (
    Document,
    DocumentCreate,
    DocumentUpdate,
    Session,
    Toponym,
    ToponymCreate,
)
from geoparser.annotator.exceptions import DocumentNotFoundException


def test_get_highest_index(test_db: DBSession, test_session: Session):
    assert (
        DocumentRepository.get_highest_index(test_db, test_session.id) == -1
    )  # No documents yet
    DocumentRepository.create(
        test_db,
        DocumentCreate(filename="doc1.txt", spacy_model="en_core_web_sm", text="Doc 1"),
        additional={"session_id": test_session.id},
    )
    assert (
        DocumentRepository.get_highest_index(test_db, test_session.id) == 0
    )  # First document has index 0
    DocumentRepository.create(
        test_db,
        DocumentCreate(filename="doc2.txt", spacy_model="en_core_web_sm", text="Doc 2"),
        additional={"session_id": test_session.id},
    )
    assert (
        DocumentRepository.get_highest_index(test_db, test_session.id) == 1
    )  # Second document has index 1


def test_reindex_documents(test_db: DBSession, test_session: Session):
    # Create three documents
    docs = [
        DocumentRepository.create(
            test_db,
            DocumentCreate(
                filename=f"doc{i}.txt", spacy_model="en_core_web_sm", text=f"Doc {i}"
            ),
            additional={"session_id": test_session.id},
        )
        for i in range(3)
    ]
    # Ensure doc_index is assigned correctly
    for i, doc in enumerate(docs):
        assert doc.doc_index == i
    # Delete the second document (index 1)
    DocumentRepository.delete(test_db, docs[1].id)
    # Reindex the documents
    DocumentRepository._reindex_documents(test_db, test_session.id)
    # Ensure reindexing is correct (should be sequential)
    for i, doc in enumerate(
        DocumentRepository.read_all(test_db, session_id=test_session.id)
    ):
        assert doc.doc_index == i
        assert (
            doc
            == DocumentRepository.read_all(
                test_db, session_id=test_session.id, doc_index=i
            )[0]
        )


@pytest.mark.parametrize("nested", [True, False])
def test_create(test_db: DBSession, test_session: Session, nested: bool):
    # create the document
    document_create = DocumentCreate(
        filename="test.txt",
        spacy_model="en_core_web_sm",
        text="Andorra is nice.",
        toponyms=[ToponymCreate(text="Andorra", start=0, end=6)] if nested else [],
    )
    document = DocumentRepository.create(
        test_db, document_create, additional={"session_id": test_session.id}
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


@pytest.mark.parametrize("apply_spacy", [True, False])
def test_create_from_text_files(
    test_db: DBSession,
    geoparser_mocked_nlp: Geoparser,
    test_session: Session,
    apply_spacy: bool,
):
    file_content = "Andorra is nice."
    file = UploadFile(filename="test.txt", file=io.BytesIO(file_content.encode()))
    # Call the method
    documents = DocumentRepository.create_from_text_files(
        test_db,
        geoparser_mocked_nlp,
        [file],
        session_id=test_session.id,
        spacy_model="en_core_web_sm",
        apply_spacy=apply_spacy,
    )
    # Ensure a document was created
    assert len(documents) == 1
    db_document = DocumentRepository.read_all(test_db, id=documents[0].id)[0]
    assert db_document.filename == "test.txt"
    assert db_document.text == file_content
    assert db_document.spacy_model == "en_core_web_sm"
    assert db_document.spacy_applied == apply_spacy
    # If apply_spacy is True, ensure toponyms were extracted
    if apply_spacy:
        assert (
            db_document.toponyms[0].model_dump(exclude=["id", "document_id"])
            == ToponymCreate(text="Andorra", start=0, end=6).model_dump()
        )
    else:
        assert len(db_document.toponyms) == 0


@pytest.mark.parametrize("annotated", [True, False])
def test_get_pre_annotated_text(
    test_db: DBSession, test_session: Session, annotated: bool
):
    toponym = ToponymCreate(text="Andorra", start=0, end=7)
    if annotated:
        toponym.loc_id = "geonames:3041565"  # Example location ID
    document_create = DocumentCreate(
        filename="test.txt",
        spacy_model="en_core_web_sm",
        text="Andorra is nice.",
        toponyms=[toponym],
    )
    document = DocumentRepository.create(
        test_db, document_create, additional={"session_id": test_session.id}
    )
    annotated_text = DocumentRepository.get_pre_annotated_text(test_db, document.id)
    expected_html = Markup(
        '<span class="toponym {}" data-start="0" data-end="7">Andorra</span> is nice.'.format(
            "annotated" if annotated else ""
        )
    )
    assert isinstance(annotated_text, Markup)
    assert annotated_text == expected_html


@pytest.mark.parametrize(
    "toponyms, expected_annotated, expected_total, expected_percentage",
    [
        (  # Case: One annotated, one unannotated
            [
                ToponymCreate(text="Andorra", start=0, end=7, loc_id="3041565"),
                ToponymCreate(text="nice", start=11, end=15),
            ],
            1,
            2,
            50.0,
        ),
        (  # Case: All annotated
            [
                ToponymCreate(text="Zurich", start=0, end=6, loc_id="2657896"),
                ToponymCreate(text="great", start=11, end=16, loc_id="1234567"),
            ],
            2,
            2,
            100.0,
        ),
    ],
)
def test_get_progress(
    test_db: DBSession,
    test_session: Session,
    toponyms: list[ToponymCreate],
    expected_annotated: int,
    expected_total: int,
    expected_percentage: float,
):
    DocumentRepository.create(
        test_db,
        DocumentCreate(
            filename="test.txt",
            spacy_model="en_core_web_sm",
            text="Some text.",
            toponyms=toponyms,
        ),
        additional={"session_id": test_session.id},
    )

    progress = list(
        DocumentRepository.get_progress(test_db, session_id=test_session.id)
    )[0]
    assert progress["annotated_toponyms"] == expected_annotated
    assert progress["total_toponyms"] == expected_total
    assert progress["progress_percentage"] == expected_percentage


def test_get_document_progress(test_db: DBSession, test_session: Session):
    # Create a document
    document = DocumentRepository.create(
        test_db,
        DocumentCreate(
            filename="test.txt",
            spacy_model="en_core_web_sm",
            text="Berlin is amazing.",
            toponyms=[
                ToponymCreate(
                    text="Berlin", start=0, end=6, loc_id="geonames:2950159"
                ),  # Annotated
                ToponymCreate(text="amazing", start=11, end=18),  # Unannotated
            ],
        ),
        additional={"session_id": test_session.id},
    )
    # Call get_document_progress
    document_progress = DocumentRepository.get_document_progress(test_db, document.id)
    # Verify result (1 annotated / 2 total → 50%)
    assert document_progress["filename"] == "test.txt"
    assert document_progress["doc_id"] == document.id
    assert document_progress["annotated_toponyms"] == 1
    assert document_progress["total_toponyms"] == 2
    assert document_progress["progress_percentage"] == 50.0


@pytest.mark.parametrize("valid_id", [True, False])
def test_read(test_db: DBSession, test_session: Session, valid_id: bool):
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
            test_db, document_create, additional={"session_id": test_session.id}
        )
        document_id = document.id
    # read document
    with nullcontext() if valid_id else pytest.raises(DocumentNotFoundException):
        db_document = DocumentRepository.read(test_db, document_id)
        assert type(db_document) is Document
        assert db_document.model_dump(
            exclude=["id", "session_id", "doc_index"]
        ) == document_create.model_dump(exclude=["toponyms"])


def test_read_all(test_db: DBSession, test_session: Session):
    # create first document
    document_create = DocumentCreate(
        filename="test.txt",
        spacy_model="en_core_web_sm",
        text="Andorra is nice.",
    )
    document1 = DocumentRepository.create(
        test_db, document_create, additional={"session_id": test_session.id}
    )
    after_first = DocumentRepository.read_all(test_db)
    assert len(after_first) == 1
    assert type(after_first[0]) is Document
    assert after_first[0].id == document1.id
    # create second document
    document2 = DocumentRepository.create(
        test_db, document_create, additional={"session_id": test_session.id}
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
def test_update(test_db: DBSession, test_session: Session, valid_id: bool):
    # create document to update afterwards
    document_id = uuid.uuid4()
    if valid_id:
        document_create = DocumentCreate(
            filename="test.txt",
            spacy_model="en_core_web_sm",
            text="Andorra is nice.",
        )
        document = DocumentRepository.create(
            test_db, document_create, additional={"session_id": test_session.id}
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


def test_parse(
    test_db: DBSession,
    geoparser_mocked_nlp: Geoparser,
    test_session: Session,
):
    # Create a document without toponyms
    document_create = DocumentCreate(
        filename="test.txt",
        spacy_model="en_core_web_sm",
        text="Andorra is beautiful.",
        toponyms=[],
    )
    document = DocumentRepository.create(
        test_db, document_create, additional={"session_id": test_session.id}
    )
    # Call parse method
    parsed_document = DocumentRepository.parse(
        test_db, geoparser_mocked_nlp, document.id
    )
    assert parsed_document.spacy_applied is True
    assert len(parsed_document.toponyms) == 1
    assert parsed_document.toponyms[0].text == "Andorra"
    assert parsed_document.toponyms[0].start == 0
    assert parsed_document.toponyms[0].end == 6


@pytest.mark.parametrize("valid_id", [True, False])
def test_delete(test_db: DBSession, test_session: Session, valid_id: bool):
    document_id = uuid.uuid4()
    # create document to delete afterwards
    if valid_id:
        document_create = DocumentCreate(
            filename="test.txt",
            spacy_model="en_core_web_sm",
            text="Andorra is nice.",
        )
        document = DocumentRepository.create(
            test_db, document_create, additional={"session_id": test_session.id}
        )
        document_id = document.id
    # document exists before deletion
    with nullcontext() if valid_id else pytest.raises(DocumentNotFoundException):
        assert DocumentRepository.read(test_db, document_id)
        DocumentRepository.delete(test_db, document_id)
    # document is gone
    with pytest.raises(DocumentNotFoundException):
        DocumentRepository.read(test_db, document_id)


def test_delete_with_reindexing(test_db: DBSession, test_session: Session):
    # create three documents
    docs = [
        DocumentRepository.create(
            test_db,
            DocumentCreate(
                filename=f"doc{i}.txt",
                spacy_model="en_core_web_sm",
                text=f"Document {i}",
            ),
            additional={"session_id": test_session.id},
        )
        for i in range(3)
    ]

    # delete the middle document
    DocumentRepository.delete(test_db, docs[1].id)

    # verify remaining documents are reindexed properly
    remaining_docs = DocumentRepository.read_all(test_db, session_id=test_session.id)
    assert len(remaining_docs) == 2
    assert remaining_docs[0].doc_index == 0
    assert remaining_docs[1].doc_index == 1
    assert remaining_docs[0].id == docs[0].id
    assert remaining_docs[1].id == docs[2].id
