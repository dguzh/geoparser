import typing as t
import uuid
from abc import abstractmethod
from typing import List, Tuple

from sqlmodel import Session

from geoparser.db.crud import (
    DocumentRepository,
    RecognitionRepository,
    RecognizerRepository,
    ReferenceRepository,
)
from geoparser.db.db import engine
from geoparser.db.models import RecognitionCreate, RecognizerCreate, ReferenceCreate
from geoparser.modules.module import Module

if t.TYPE_CHECKING:
    from geoparser.db.models import Document
    from geoparser.project import Project


class Recognizer(Module):
    """
    Abstract class for modules that perform reference recognition.

    These modules identify potential references (place names) in text and handle
    all database operations related to recognition processing.
    """

    # This base class should have NAME set to None since it should not be instantiated directly
    NAME = None

    def __init__(self, **kwargs):
        """
        Initialize a recognition module.

        Args:
            **kwargs: Configuration parameters for this module
        """
        super().__init__(**kwargs)

        # Load recognizer ID immediately upon initialization
        self.id = self._load()

    def _load(self) -> uuid.UUID:
        """
        Load a recognizer from the database.

        Retrieves an existing recognizer record or creates a new one if it doesn't exist.

        Returns:
            Database ID of the recognizer
        """
        with Session(engine) as db:
            db_recognizer = RecognizerRepository.get_by_name_and_config(
                db, self.name, self.config
            )
            if db_recognizer is None:
                recognizer_create = RecognizerCreate(name=self.name, config=self.config)
                db_recognizer = RecognizerRepository.create(db, recognizer_create)

            return db_recognizer.id

    def run(self, project: "Project") -> None:
        """
        Run the configured recognizer on all documents in the project.

        Args:
            project: Project object containing documents to process
        """
        with Session(engine) as db:
            # Get all documents in the project
            documents = DocumentRepository.get_by_project(db, project.id)

            if not documents:
                return

            # Filter out documents that have already been processed by this recognizer
            unprocessed_documents = self._get_unprocessed_documents(db, documents)

            if not unprocessed_documents:
                return

            # Get predictions from recognizer using Document objects
            predicted_references = self.predict_references(unprocessed_documents)

            # Extract document IDs for database operations
            document_ids = [doc.id for doc in unprocessed_documents]

            # Process predictions and update database
            self._process_reference_predictions(
                db, document_ids, predicted_references, self.id
            )

    def _process_reference_predictions(
        self,
        db: Session,
        document_ids: List[uuid.UUID],
        predicted_references: List[List[Tuple[int, int]]],
        recognizer_id: uuid.UUID,
    ) -> None:
        """
        Process reference predictions and update the database.

        Args:
            db: Database session
            document_ids: List of document IDs
            predicted_references: Nested list of predicted references
            recognizer_id: ID of the recognizer that made the predictions
        """
        # Process each document with its predicted references
        for doc_id, references in zip(document_ids, predicted_references):
            # Create references with recognizer ID
            for start, end in references:
                self._create_reference_record(db, doc_id, start, end, recognizer_id)

            # Mark document as processed
            self._create_recognition_record(db, doc_id, recognizer_id)

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

    def _get_unprocessed_documents(
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
                db, doc.id, self.id
            )
            if not existing_recognition:
                unprocessed_documents.append(doc)
        return unprocessed_documents

    @abstractmethod
    def predict_references(
        self, documents: t.List["Document"]
    ) -> t.List[t.List[t.Tuple[int, int]]]:
        """
        Predict references in multiple documents.

        This abstract method must be implemented by child classes.

        Args:
            documents: List of Document ORM objects to process

        Returns:
            List of lists of tuples containing (start, end) positions of references.
            Each inner list corresponds to references found in one document at the same index in the input list.
        """
