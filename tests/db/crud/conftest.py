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
    Gazetteer,
    GazetteerCreate,
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
    Source,
    SourceCreate,
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
def test_document(test_db: Session, test_project: Project):
    """Create a test document."""
    document_create = DocumentCreate(
        text="This is a test document with Berlin.", project_id=test_project.id
    )
    document = Document(text=document_create.text, project_id=test_project.id)
    test_db.add(document)
    test_db.commit()
    test_db.refresh(document)
    return document


@pytest.fixture
def test_recognizer(test_db: Session):
    """Create a test recognizer."""
    config = {
        "model": "test-model",
        "threshold": 0.75,
    }
    recognizer_create = RecognizerCreate(
        id="test-recognizer-id", name="test-recognizer", config=config
    )
    recognizer = Recognizer(
        id=recognizer_create.id,
        name=recognizer_create.name,
        config=recognizer_create.config,
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
    resolver_create = ResolverCreate(
        id="test-resolver-id", name="test-resolver", config=config
    )
    resolver = Resolver(
        id=resolver_create.id, name=resolver_create.name, config=resolver_create.config
    )
    test_db.add(resolver)
    test_db.commit()
    test_db.refresh(resolver)
    return resolver


@pytest.fixture
def test_gazetteer(test_db: Session):
    """Create a test gazetteer."""
    gazetteer_create = GazetteerCreate(name="test-gazetteer")
    gazetteer = Gazetteer(name=gazetteer_create.name)
    test_db.add(gazetteer)
    test_db.commit()
    test_db.refresh(gazetteer)
    return gazetteer


@pytest.fixture
def test_source(test_db: Session, test_gazetteer: Gazetteer):
    """Create a test source."""
    source_create = SourceCreate(
        name="test_table",
        location_id_name="test_id",
        gazetteer_id=test_gazetteer.id,
    )
    source = Source(
        name=source_create.name,
        location_id_name=source_create.location_id_name,
        gazetteer_id=test_gazetteer.id,
    )
    test_db.add(source)
    test_db.commit()
    test_db.refresh(source)
    return source


@pytest.fixture
def test_feature(test_db: Session, test_source: Source):
    """Create a test feature."""
    feature_create = FeatureCreate(
        source_id=test_source.id,
        location_id_value="123456",
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
