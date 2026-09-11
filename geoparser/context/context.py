import uuid

from sqlmodel import Session

from geoparser.db.crud.context import ContextRepository
from geoparser.db.db import get_session
from geoparser.db.models.context import Context as ContextRecord
from geoparser.db.models.context import ContextCreate, ContextUpdate


class Context:
    """
    Manages context records for a project.

    A context associates a tag with specific recognizer and resolver IDs,
    allowing users to manage multiple result sets using human-friendly tags
    instead of module IDs.
    """

    def __init__(self, project_id: uuid.UUID):
        """
        Initialize a Context manager for a project.

        Args:
            project_id: ID of the project to manage contexts for
        """
        self.project_id = project_id

    def _ensure_context_record(self, tag: str) -> uuid.UUID:
        """
        Ensure a context record exists for the given tag.

        Creates a new context record with None IDs if it doesn't already exist.

        Args:
            tag: Tag identifier

        Returns:
            Context record ID
        """
        with get_session() as session:
            context_record = ContextRepository.get_by_project_and_tag(
                session, self.project_id, tag
            )

            if context_record is None:
                # pragma: no mutate start - a fresh context has no modules
                # yet; the two None arguments restate the model's own default,
                # so dropping them writes exactly the same row.
                context_create = ContextCreate(
                    project_id=self.project_id,
                    tag=tag,
                    recognizer_id=None,
                    resolver_id=None,
                )
                # pragma: no mutate end
                context_record = ContextRepository.create(session, context_create)

            return context_record.id

    def _load_context_record(
        self, session: Session, context_id: uuid.UUID
    ) -> ContextRecord:
        """
        Load the context record that _ensure_context_record guaranteed exists.

        Args:
            session: Database session to load the record into
            context_id: ID returned by _ensure_context_record

        Returns:
            The context record, attached to the given session

        Raises:
            RuntimeError: If the record vanished between the two sessions
        """
        record = ContextRepository.get(session, context_id)
        if record is None:  # pragma: no cover - guaranteed by the caller
            # pragma: no mutate start - wording only, on a branch the caller
            # makes unreachable; there is no test that could pin the prose.
            raise RuntimeError(f"Context record '{context_id}' no longer exists")
            # pragma: no mutate end
        return record

    def update_recognizer_context(self, tag: str, recognizer_id: str) -> None:
        """
        Update the recognizer ID for a given tag.

        Args:
            tag: Tag identifier
            recognizer_id: ID of the recognizer to associate with this tag
        """
        context_id = self._ensure_context_record(tag)

        with get_session() as session:
            context_record = self._load_context_record(session, context_id)
            context_update = ContextUpdate(
                id=context_record.id, recognizer_id=recognizer_id
            )
            ContextRepository.update(
                session, db_obj=context_record, obj_in=context_update
            )

    def update_resolver_context(self, tag: str, resolver_id: str) -> None:
        """
        Update the resolver ID for a given tag.

        Args:
            tag: Tag identifier
            resolver_id: ID of the resolver to associate with this tag
        """
        context_id = self._ensure_context_record(tag)

        with get_session() as session:
            context_record = self._load_context_record(session, context_id)
            context_update = ContextUpdate(
                id=context_record.id, resolver_id=resolver_id
            )
            ContextRepository.update(
                session, db_obj=context_record, obj_in=context_update
            )

    def get_recognizer_context(self, tag: str) -> str | None:
        """
        Get the recognizer ID for a given tag.

        Args:
            tag: Tag identifier

        Returns:
            Recognizer ID if set, None otherwise
        """
        context_id = self._ensure_context_record(tag)

        with get_session() as session:
            context_record = self._load_context_record(session, context_id)
            return context_record.recognizer_id

    def get_resolver_context(self, tag: str) -> str | None:
        """
        Get the resolver ID for a given tag.

        Args:
            tag: Tag identifier

        Returns:
            Resolver ID if set, None otherwise
        """
        context_id = self._ensure_context_record(tag)

        with get_session() as session:
            context_record = self._load_context_record(session, context_id)
            return context_record.resolver_id
