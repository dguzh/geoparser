import typing as t
import uuid
from typing import List, Tuple

from sqlmodel import Session

from geoparser.db.crud import (
    RecognitionRepository,
    RecognizerRepository,
    ReferenceRepository,
)
from geoparser.db.engine import engine
from geoparser.db.models import RecognitionCreate, RecognizerCreate, ReferenceCreate

if t.TYPE_CHECKING:
    from geoparser.db.models import Document
    from geoparser.modules.recognizers.base import Recognizer


class RecognitionService:
    """
    Service layer that handles all database operations for reference recognition.

    This service acts as a bridge between recognizer modules (which are DB-agnostic)
    and the database layer.
    """

    def __init__(self, recognizer: "Recognizer"):
        """
        Initialize the recognition service.

        Args:
            recognizer: The recognizer module to use for predictions
        """
        self.recognizer = recognizer
        self.recognizer_id = recognizer.id

    def _ensure_recognizer_record(self) -> None:
        """
        Ensure a recognizer record exists in the database.

        Creates a new recognizer record if it doesn't already exist.
        """
        with Session(engine) as db:
            db_recognizer = RecognizerRepository.get(db, id=self.recognizer_id)
            if db_recognizer is None:
                recognizer_create = RecognizerCreate(
                    id=self.recognizer_id,
                    name=self.recognizer.name,
                    config=self.recognizer.config,
                )
                RecognizerRepository.create(db, recognizer_create)

    def run(self, documents: List["Document"]) -> None:
        """
        Run the recognizer on the provided documents and store results in the database.

        Args:
            documents: List of Document objects to process
        """
        if not documents:
            return

        # Ensure recognizer record exists in database
        self._ensure_recognizer_record()

        with Session(engine) as db:
            # Filter out documents that have already been processed by this recognizer
            unprocessed_documents = self._filter_unprocessed_documents(db, documents)

            if not unprocessed_documents:
                return

            # Extract text from documents for prediction
            texts = [doc.text for doc in unprocessed_documents]

            # Only call predict_references if there are texts to process
            if texts:
                # Get predictions from recognizer using raw text
                predicted_references = self.recognizer.predict_references(texts)

                # Process predictions and update database
                self._record_reference_predictions(
                    db, unprocessed_documents, predicted_references, self.recognizer_id
                )

    def _record_reference_predictions(
        self,
        db: Session,
        documents: List["Document"],
        predicted_references: List[List[Tuple[int, int]]],
        recognizer_id: uuid.UUID,
    ) -> None:
        """
        Process reference predictions and update the database.

        Args:
            db: Database session
            documents: List of document objects
            predicted_references: Nested list of predicted references
            recognizer_id: ID of the recognizer that made the predictions
        """
        # Process each document with its predicted references
        for document, references in zip(documents, predicted_references):
            # Create references with recognizer ID
            for start, end in references:
                self._create_reference_record(
                    db, document.id, start, end, recognizer_id
                )

            # Mark document as processed
            self._create_recognition_record(db, document.id, recognizer_id)

    def _create_reference_record(
        self,
        db: Session,
        document_id: uuid.UUID,
        start: int,
        end: int,
        recognizer_id: uuid.UUID,
    ) -> None:
        """
        Create a reference record with the recognizer ID.

        Args:
            db: Database session
            document_id: ID of the document containing the reference
            start: Start position of the reference
            end: End position of the reference
            recognizer_id: ID of the recognizer
        """
        # Create the reference with recognizer ID directly
        reference_create = ReferenceCreate(
            start=start, end=end, document_id=document_id, recognizer_id=recognizer_id
        )
        ReferenceRepository.create(db, reference_create)

    def _create_recognition_record(
        self, db: Session, document_id: uuid.UUID, recognizer_id: uuid.UUID
    ) -> None:
        """
        Create a recognition record for a document processed by a specific recognizer.

        Args:
            db: Database session
            document_id: ID of the document that was processed
            recognizer_id: ID of the recognizer that processed it
        """
        recognition_create = RecognitionCreate(
            document_id=document_id, recognizer_id=recognizer_id
        )
        RecognitionRepository.create(db, recognition_create)

    def _filter_unprocessed_documents(
        self, db: Session, documents: List["Document"]
    ) -> List["Document"]:
        """
        Filter out documents that have already been processed by this recognizer.

        Args:
            db: Database session
            documents: List of all documents to check

        Returns:
            List of documents that haven't been processed by this recognizer
        """
        unprocessed_documents = []
        for doc in documents:
            # Check if this document has already been processed by this recognizer
            existing_recognition = RecognitionRepository.get_by_document_and_recognizer(
                db, doc.id, self.recognizer_id
            )
            if not existing_recognition:
                unprocessed_documents.append(doc)
        return unprocessed_documents
