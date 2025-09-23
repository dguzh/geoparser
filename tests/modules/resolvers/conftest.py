import pytest
from sqlmodel import Session, SQLModel
from sqlmodel.pool import StaticPool

from geoparser.db.db import create_engine
from geoparser.db.models import (
    Document,
    DocumentCreate,
    Project,
    ProjectCreate,
)
from geoparser.db.models import Recognizer as RecognizerModel
from geoparser.db.models import (
    RecognizerCreate,
    Reference,
    ReferenceCreate,
    Referent,
    ReferentCreate,
)
from geoparser.db.models import Resolver as ResolverModel
from geoparser.db.models import (
    ResolverCreate,
)
from geoparser.db.models.feature import Feature, FeatureCreate
from geoparser.db.models.gazetteer import Gazetteer as GazetteerModel
from geoparser.db.models.gazetteer import GazetteerCreate


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
def test_recognizer(test_db):
    """Create a test recognizer."""
    recognizer_create = RecognizerCreate(
        name="test-recognizer", config={"model": "test-model"}
    )
    recognizer = RecognizerModel.model_validate(recognizer_create)
    test_db.add(recognizer)
    test_db.commit()
    test_db.refresh(recognizer)
    return recognizer


@pytest.fixture
def test_reference(test_db, test_document, test_recognizer):
    """Create a test reference in the test document."""
    reference_create = ReferenceCreate(
        start=29, end=35, document_id=test_document.id, recognizer_id=test_recognizer.id
    )
    reference = Reference.model_validate(reference_create)
    test_db.add(reference)
    test_db.commit()
    test_db.refresh(reference)
    return reference


@pytest.fixture
def test_references(test_db, test_documents, test_recognizer):
    """Create multiple test references in the test documents."""
    references = []
    reference_data = [
        (29, 35),  # "London" in first document
        (41, 46),  # "Paris" in first document
        (32, 40),  # "New York" in second document
    ]

    for i, (start, end) in enumerate(reference_data):
        doc = test_documents[i % len(test_documents)]
        reference_create = ReferenceCreate(
            start=start, end=end, document_id=doc.id, recognizer_id=test_recognizer.id
        )
        reference = Reference.model_validate(reference_create)
        test_db.add(reference)
        test_db.commit()
        test_db.refresh(reference)
        references.append(reference)

    return references


@pytest.fixture
def test_resolver(test_db):
    """Create a test resolver."""
    resolver_create = ResolverCreate(
        name="test-resolver", config={"model": "test-model"}
    )
    resolver = ResolverModel.model_validate(resolver_create)
    test_db.add(resolver)
    test_db.commit()
    test_db.refresh(resolver)
    return resolver


@pytest.fixture
def test_gazetteer(test_db):
    """Create a test gazetteer."""
    gazetteer_create = GazetteerCreate(name="test-gazetteer")
    gazetteer = GazetteerModel.model_validate(gazetteer_create)
    test_db.add(gazetteer)
    test_db.commit()
    test_db.refresh(gazetteer)
    return gazetteer


@pytest.fixture
def test_feature(test_db, test_gazetteer):
    """Create a test feature."""
    feature_create = FeatureCreate(
        gazetteer_name=test_gazetteer.name,
        table_name="test_table",
        identifier_name="id",
        identifier_value="12345",
    )
    feature = Feature.model_validate(feature_create)
    test_db.add(feature)
    test_db.commit()
    test_db.refresh(feature)
    return feature


@pytest.fixture
def test_referent(test_db, test_reference, test_feature, test_resolver):
    """Create a test referent linking a reference to a feature."""
    referent_create = ReferentCreate(
        reference_id=test_reference.id,
        feature_id=test_feature.id,
        resolver_id=test_resolver.id,
    )
    referent = Referent.model_validate(referent_create)
    test_db.add(referent)
    test_db.commit()
    test_db.refresh(referent)
    return referent


@pytest.fixture
def test_documents_with_referents(
    test_db, test_project, test_recognizer, test_resolver, test_gazetteer
):
    """Create test documents with references and resolved referents for training."""
    documents = []

    # Create documents
    texts = [
        "I visited London last summer.",
        "Paris is beautiful in spring.",
    ]

    for text in texts:
        document_create = DocumentCreate(text=text, project_id=test_project.id)
        document = Document.model_validate(document_create)
        test_db.add(document)
        test_db.commit()
        test_db.refresh(document)
        documents.append(document)

    # Create features
    feature_data = [
        {"identifier_value": "2643743", "name": "London"},
        {"identifier_value": "2988507", "name": "Paris"},
    ]

    features = []
    for data in feature_data:
        feature_create = FeatureCreate(
            gazetteer_name=test_gazetteer.name,
            table_name="test_table",
            identifier_name="id",
            identifier_value=data["identifier_value"],
        )
        feature = Feature.model_validate(feature_create)
        feature.data = data  # Set additional data
        test_db.add(feature)
        test_db.commit()
        test_db.refresh(feature)
        features.append(feature)

    # Create references and referents
    reference_data = [
        (documents[0], 10, 16, features[0]),  # "London" in first document
        (documents[1], 0, 5, features[1]),  # "Paris" in second document
    ]

    for doc, start, end, feature in reference_data:
        # Create reference
        reference_create = ReferenceCreate(
            start=start, end=end, document_id=doc.id, recognizer_id=test_recognizer.id
        )
        reference = Reference.model_validate(reference_create)
        test_db.add(reference)
        test_db.commit()
        test_db.refresh(reference)

        # Create referent
        referent_create = ReferentCreate(
            reference_id=reference.id,
            feature_id=feature.id,
            resolver_id=test_resolver.id,
        )
        referent = Referent.model_validate(referent_create)
        test_db.add(referent)
        test_db.commit()
        test_db.refresh(referent)

    # Refresh documents to get references and referents
    for doc in documents:
        test_db.refresh(doc)

    return documents
