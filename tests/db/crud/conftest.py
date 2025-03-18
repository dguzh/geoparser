import pytest
from sqlmodel import Session as DBSession
from sqlmodel import SQLModel
from sqlmodel.pool import StaticPool

from geoparser.db.db import create_engine
from geoparser.db.models import (
    Document,
    DocumentCreate,
    Location,
    LocationCreate,
    RecognitionModule,
    RecognitionModuleCreate,
    RecognitionObject,
    RecognitionObjectCreate,
    RecognitionSubject,
    RecognitionSubjectCreate,
    ResolutionModule,
    ResolutionModuleCreate,
    ResolutionObject,
    ResolutionObjectCreate,
    ResolutionSubject,
    ResolutionSubjectCreate,
    Session,
    SessionCreate,
    Toponym,
    ToponymCreate,
)


@pytest.fixture(scope="function")
def test_db():
    """Create a test database session."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with DBSession(engine) as session:
        yield session


@pytest.fixture
def test_session(test_db: DBSession):
    """Create a test session."""
    session_create = SessionCreate(name="test-session")
    session = Session(name=session_create.name)
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)
    return session


@pytest.fixture
def test_document(test_db: DBSession, test_session: Session):
    """Create a test document."""
    document_create = DocumentCreate(
        text="This is a test document with Berlin.", session_id=test_session.id
    )
    document = Document(text=document_create.text, session_id=test_session.id)
    test_db.add(document)
    test_db.commit()
    test_db.refresh(document)
    return document


@pytest.fixture
def test_recognition_module(test_db: DBSession):
    """Create a test recognition module."""
    module_create = RecognitionModuleCreate(name="test-recognition-module")
    module = RecognitionModule(name=module_create.name)
    test_db.add(module)
    test_db.commit()
    test_db.refresh(module)
    return module


@pytest.fixture
def test_resolution_module(test_db: DBSession):
    """Create a test resolution module."""
    module_create = ResolutionModuleCreate(name="test-resolution-module")
    module = ResolutionModule(name=module_create.name)
    test_db.add(module)
    test_db.commit()
    test_db.refresh(module)
    return module


@pytest.fixture
def test_toponym(test_db: DBSession, test_document: Document):
    """Create a test toponym."""
    toponym_create = ToponymCreate(start=27, end=33, document_id=test_document.id)
    toponym = Toponym(
        start=toponym_create.start, end=toponym_create.end, document_id=test_document.id
    )
    test_db.add(toponym)
    test_db.commit()
    test_db.refresh(toponym)
    return toponym


@pytest.fixture
def test_recognition_object(
    test_db: DBSession,
    test_toponym: Toponym,
    test_recognition_module: RecognitionModule,
):
    """Create a test recognition object."""
    recognition_create = RecognitionObjectCreate(
        toponym_id=test_toponym.id, module_id=test_recognition_module.id
    )
    recognition = RecognitionObject(
        toponym_id=recognition_create.toponym_id, module_id=recognition_create.module_id
    )
    test_db.add(recognition)
    test_db.commit()
    test_db.refresh(recognition)
    return recognition


@pytest.fixture
def test_location(test_db: DBSession, test_toponym: Toponym):
    """Create a test location."""
    location_create = LocationCreate(
        location_id="123456", confidence=0.9, toponym_id=test_toponym.id
    )
    location = Location(
        location_id=location_create.location_id,
        confidence=location_create.confidence,
        toponym_id=test_toponym.id,
    )
    test_db.add(location)
    test_db.commit()
    test_db.refresh(location)
    return location


@pytest.fixture
def test_resolution_object(
    test_db: DBSession,
    test_location: Location,
    test_resolution_module: ResolutionModule,
):
    """Create a test resolution object."""
    resolution_create = ResolutionObjectCreate(
        location_id=test_location.id, module_id=test_resolution_module.id
    )
    resolution = ResolutionObject(
        location_id=resolution_create.location_id, module_id=resolution_create.module_id
    )
    test_db.add(resolution)
    test_db.commit()
    test_db.refresh(resolution)
    return resolution


@pytest.fixture
def test_recognition_subject(
    test_db: DBSession,
    test_document: Document,
    test_recognition_module: RecognitionModule,
):
    """Create a test recognition subject."""
    recognition_subject_create = RecognitionSubjectCreate(
        document_id=test_document.id, module_id=test_recognition_module.id
    )
    recognition_subject = RecognitionSubject(
        document_id=recognition_subject_create.document_id,
        module_id=recognition_subject_create.module_id,
    )
    test_db.add(recognition_subject)
    test_db.commit()
    test_db.refresh(recognition_subject)
    return recognition_subject


@pytest.fixture
def test_resolution_subject(
    test_db: DBSession,
    test_toponym: Toponym,
    test_resolution_module: ResolutionModule,
):
    """Create a test resolution subject."""
    resolution_subject_create = ResolutionSubjectCreate(
        toponym_id=test_toponym.id, module_id=test_resolution_module.id
    )
    resolution_subject = ResolutionSubject(
        toponym_id=resolution_subject_create.toponym_id,
        module_id=resolution_subject_create.module_id,
    )
    test_db.add(resolution_subject)
    test_db.commit()
    test_db.refresh(resolution_subject)
    return resolution_subject
