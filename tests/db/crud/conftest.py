import pytest
from sqlmodel import Session, SQLModel
from sqlmodel.pool import StaticPool

from geoparser.db.crud import FeatureRepository, ReferenceRepository
from geoparser.db.db import create_engine
from geoparser.db.models import (
    Document,
    DocumentCreate,
    Feature,
    FeatureCreate,
    Project,
    ProjectCreate,
    RecognitionModule,
    RecognitionModuleCreate,
    RecognitionObject,
    RecognitionObjectCreate,
    RecognitionSubject,
    RecognitionSubjectCreate,
    Reference,
    ReferenceCreate,
    Referent,
    ReferentCreate,
    ResolutionModule,
    ResolutionModuleCreate,
    ResolutionObject,
    ResolutionObjectCreate,
    ResolutionSubject,
    ResolutionSubjectCreate,
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
def test_recognition_module(test_db: Session):
    """Create a test recognition module."""
    config = {
        "model": "test-model",
        "threshold": 0.75,
    }
    module_create = RecognitionModuleCreate(
        name="test-recognition-module", config=config
    )
    module = RecognitionModule(name=module_create.name, config=module_create.config)
    test_db.add(module)
    test_db.commit()
    test_db.refresh(module)
    return module


@pytest.fixture
def test_resolution_module(test_db: Session):
    """Create a test resolution module."""
    config = {
        "gazetteer": "test-gazetteer",
        "max_results": 5,
    }
    module_create = ResolutionModuleCreate(name="test-resolution-module", config=config)
    module = ResolutionModule(name=module_create.name, config=module_create.config)
    test_db.add(module)
    test_db.commit()
    test_db.refresh(module)
    return module


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
def test_reference(test_db: Session, test_document: Document):
    """Create a test reference."""
    reference_create = ReferenceCreate(start=29, end=35, document_id=test_document.id)
    reference = ReferenceRepository.create(test_db, reference_create)
    return reference


@pytest.fixture
def test_recognition_object(
    test_db: Session,
    test_reference: Reference,
    test_recognition_module: RecognitionModule,
):
    """Create a test recognition object."""
    recognition_create = RecognitionObjectCreate(
        reference_id=test_reference.id, module_id=test_recognition_module.id
    )
    recognition = RecognitionObject(
        reference_id=recognition_create.reference_id,
        module_id=recognition_create.module_id,
    )
    test_db.add(recognition)
    test_db.commit()
    test_db.refresh(recognition)
    return recognition


@pytest.fixture
def test_referent(test_db: Session, test_reference: Reference, test_feature: Feature):
    """Create a test referent."""
    referent_create = ReferentCreate(
        reference_id=test_reference.id, feature_id=test_feature.id
    )
    referent = Referent(
        reference_id=test_reference.id,
        feature_id=test_feature.id,
    )
    test_db.add(referent)
    test_db.commit()
    test_db.refresh(referent)
    return referent


@pytest.fixture
def test_resolution_object(
    test_db: Session,
    test_referent: Referent,
    test_resolution_module: ResolutionModule,
):
    """Create a test resolution object."""
    resolution_create = ResolutionObjectCreate(
        referent_id=test_referent.id, module_id=test_resolution_module.id
    )
    resolution = ResolutionObject(
        referent_id=resolution_create.referent_id, module_id=resolution_create.module_id
    )
    test_db.add(resolution)
    test_db.commit()
    test_db.refresh(resolution)
    return resolution


@pytest.fixture
def test_recognition_subject(
    test_db: Session,
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
    test_db: Session,
    test_reference: Reference,
    test_resolution_module: ResolutionModule,
):
    """Create a test resolution subject."""
    resolution_subject_create = ResolutionSubjectCreate(
        reference_id=test_reference.id, module_id=test_resolution_module.id
    )
    resolution_subject = ResolutionSubject(
        reference_id=resolution_subject_create.reference_id,
        module_id=resolution_subject_create.module_id,
    )
    test_db.add(resolution_subject)
    test_db.commit()
    test_db.refresh(resolution_subject)
    return resolution_subject
