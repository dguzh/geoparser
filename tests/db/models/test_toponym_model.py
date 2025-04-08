import uuid

from sqlmodel import Session

from geoparser.db.models import Document, Toponym


def test_text_property(test_db: Session):
    """Test the text property of a toponym."""
    # Create a test document
    document = Document(
        text="This is a test document with Berlin.", project_id=uuid.uuid4()
    )
    test_db.add(document)

    # Create test toponyms
    berlin_toponym = Toponym(start=29, end=35, document_id=document.id)
    test_toponym = Toponym(start=10, end=14, document_id=document.id)
    test_db.add(berlin_toponym)
    test_db.add(test_toponym)
    test_db.commit()

    test_db.refresh(berlin_toponym)
    test_db.refresh(test_toponym)

    # Verify the text property returns the correct substring
    assert berlin_toponym.text == "Berlin"
    assert test_toponym.text == "test"

    # Test with a different document
    another_document = Document(text="Paris is beautiful.", project_id=uuid.uuid4())
    test_db.add(another_document)

    paris_toponym = Toponym(start=0, end=5, document_id=another_document.id)
    test_db.add(paris_toponym)
    test_db.commit()
    test_db.refresh(paris_toponym)

    assert paris_toponym.text == "Paris"
