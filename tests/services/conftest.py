import pytest
from sqlmodel import Session, SQLModel
from sqlmodel.pool import StaticPool

from geoparser.db.crud import FeatureRepository, ReferenceRepository
from geoparser.db.engine import create_engine
from geoparser.db.models import (
    Document,
    DocumentCreate,
    Feature,
    FeatureCreate,
    Project,
    ProjectCreate,
    Recognition,
    RecognitionCreate,
    Recognizer,
    RecognizerCreate,
    Reference,
    ReferenceCreate,
    Referent,
    ReferentCreate,
    Resolution,
    ResolutionCreate,
    Resolver,
    ResolverCreate,
)


@pytest.fixture(scope="function")
def test_db():
    """Create a test database session."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def test_project(test_db: Session):
    """Create a test project."""
    project_create = ProjectCreate(name="test-project")
    project = Project(name=project_create.name)
    test_db.add(project)
    test_db.commit()
    test_db.refresh(project)
    return project


@pytest.fixture
def test_document(test_db, test_project):
    """Create a test document in the test project."""
    document_create = DocumentCreate(
        text="This is a test document about London and Paris.",
        project_id=test_project.id,
    )
    document = Document.model_validate(document_create)
    test_db.add(document)
    test_db.commit()
    test_db.refresh(document)
    return document


@pytest.fixture
def test_documents(test_db, test_project):
    """Create multiple test documents in the test project."""
    documents = []
    texts = [
        "This is a test document about London and Paris.",
        "Another document mentioning New York and Tokyo.",
    ]

    for text in texts:
        document_create = DocumentCreate(text=text, project_id=test_project.id)
        document = Document.model_validate(document_create)
        test_db.add(document)
        test_db.commit()
        test_db.refresh(document)
        documents.append(document)

    return documents


@pytest.fixture
def test_recognizer(test_db: Session):
    """Create a test recognizer."""
    config = {
        "model": "test-model",
        "threshold": 0.75,
    }
    recognizer_create = RecognizerCreate(name="test-recognizer", config=config)
    recognizer = Recognizer(
        name=recognizer_create.name, config=recognizer_create.config
    )
    test_db.add(recognizer)
    test_db.commit()
    test_db.refresh(recognizer)
    return recognizer


@pytest.fixture
def test_resolver(test_db: Session):
    """Create a test resolver."""
    config = {
        "gazetteer": "test-gazetteer",
        "max_results": 5,
    }
    resolver_create = ResolverCreate(name="test-resolver", config=config)
    resolver = Resolver(name=resolver_create.name, config=resolver_create.config)
    test_db.add(resolver)
    test_db.commit()
    test_db.refresh(resolver)
    return resolver


@pytest.fixture
def test_feature(test_db: Session):
    """Create a test feature."""
    feature_create = FeatureCreate(
        gazetteer_name="test-gazetteer",
        table_name="test_table",
        identifier_name="test_id",
        identifier_value="123456",
    )
    feature = FeatureRepository.create(test_db, feature_create)
    return feature


@pytest.fixture
def test_reference(
    test_db: Session, test_document: Document, test_recognizer: Recognizer
):
    """Create a test reference."""
    reference_create = ReferenceCreate(
        start=29, end=35, document_id=test_document.id, recognizer_id=test_recognizer.id
    )
    reference = ReferenceRepository.create(test_db, reference_create)
    return reference


@pytest.fixture
def test_references(test_db, test_documents, test_recognizer):
    """Create multiple test references across documents."""
    references = []

    # Create 2 references for first document
    for start, end in [(29, 35), (41, 46)]:
        reference_create = ReferenceCreate(
            start=start,
            end=end,
            document_id=test_documents[0].id,
            recognizer_id=test_recognizer.id,
        )
        reference = ReferenceRepository.create(test_db, reference_create)
        references.append(reference)

    # Create 1 reference for second document
    reference_create = ReferenceCreate(
        start=25,
        end=33,
        document_id=test_documents[1].id,
        recognizer_id=test_recognizer.id,
    )
    reference = ReferenceRepository.create(test_db, reference_create)
    references.append(reference)

    return references


@pytest.fixture
def test_referent(
    test_db: Session,
    test_reference: Reference,
    test_feature: Feature,
    test_resolver: Resolver,
):
    """Create a test referent."""
    referent_create = ReferentCreate(
        reference_id=test_reference.id,
        feature_id=test_feature.id,
        resolver_id=test_resolver.id,
    )
    referent = Referent(
        reference_id=test_reference.id,
        feature_id=test_feature.id,
        resolver_id=test_resolver.id,
    )
    test_db.add(referent)
    test_db.commit()
    test_db.refresh(referent)
    return referent


@pytest.fixture
def test_recognition(
    test_db: Session,
    test_document: Document,
    test_recognizer: Recognizer,
):
    """Create a test recognition."""
    recognition_create = RecognitionCreate(
        document_id=test_document.id, recognizer_id=test_recognizer.id
    )
    recognition = Recognition(
        document_id=recognition_create.document_id,
        recognizer_id=recognition_create.recognizer_id,
    )
    test_db.add(recognition)
    test_db.commit()
    test_db.refresh(recognition)
    return recognition


@pytest.fixture
def test_resolution(
    test_db: Session,
    test_reference: Reference,
    test_resolver: Resolver,
):
    """Create a test resolution."""
    resolution_create = ResolutionCreate(
        reference_id=test_reference.id, resolver_id=test_resolver.id
    )
    resolution = Resolution(
        reference_id=resolution_create.reference_id,
        resolver_id=resolution_create.resolver_id,
    )
    test_db.add(resolution)
    test_db.commit()
    test_db.refresh(resolution)
    return resolution
