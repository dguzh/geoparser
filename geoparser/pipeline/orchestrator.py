import json
import logging
import typing as t
from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Session, select

from geoparser.db.crud.run import RunRepository
from geoparser.db.db import get_db
from geoparser.db.models.run import RunCreate
from geoparser.db.models.session import Session as DBSession
from geoparser.pipeline.modules import BaseModule

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Orchestrates the execution of pipeline modules.

    This class coordinates the flow of data between modules and the database,
    providing a central point for running individual modules or entire pipelines.
    """

    def __init__(self):
        """Initialize the pipeline orchestrator."""
        self.modules: t.Dict[str, BaseModule] = {}

    def register_module(self, module: BaseModule) -> None:
        """
        Register a module with the orchestrator.

        Args:
            module: The module to register

        Raises:
            ValueError: If a module with the same name is already registered
        """
        if module.name in self.modules:
            raise ValueError(f"Module with name '{module.name}' already registered")

        self.modules[module.name] = module
        logger.info(f"Registered module: {module.name}")

    def run_module(self, module_name: str, session_id: UUID) -> None:
        """
        Run a single module on the specified session.

        Args:
            module_name: Name of the module to run
            session_id: UUID of the session to process

        Raises:
            ValueError: If no module with the given name is registered or if the session does not exist
        """
        # Validate that the session exists
        if not self._validate_session_exists(session_id):
            raise ValueError(f"No session found with ID: {session_id}")

        if module_name not in self.modules:
            raise ValueError(f"No module registered with name '{module_name}'")

        module = self.modules[module_name]
        logger.info(f"Running module: {module_name} on session: {session_id}")

        # Create a new run record
        run_id = uuid4()
        metadata = json.dumps({"description": f"Running module {module_name}"})

        for db in get_db():
            run_create = RunCreate(
                module_name=module_name,
                created_at=datetime.now(),
                status="started",
                metadata=metadata,
            )
            run = RunRepository.create(
                db=db,
                item=run_create,
                additional={"id": run_id, "session_id": session_id},
            )
            logger.info(f"Created run record with ID: {run.id}")

            try:
                # Run the module
                module.run(session_id)

                # Mark the run as completed
                RunRepository.mark_completed(
                    db=db,
                    id=run_id,
                    metadata=json.dumps(
                        {
                            "description": f"Module {module_name} completed successfully",
                            "completed_at": datetime.now().isoformat(),
                        }
                    ),
                )
                logger.info(f"Completed module: {module_name} on session: {session_id}")
            except Exception as e:
                # Mark the run as failed
                error_message = str(e)
                RunRepository.mark_failed(db=db, id=run_id, error_message=error_message)
                logger.error(f"Module {module_name} failed: {error_message}")
                raise  # Re-raise the exception

            break  # Exit the get_db() context manager after first iteration

    def run_pipeline(self, session_id: UUID) -> None:
        """
        Run all registered modules on the specified session.

        Args:
            session_id: UUID of the session to process

        Raises:
            ValueError: If the session does not exist
        """
        # Validate that the session exists
        if not self._validate_session_exists(session_id):
            raise ValueError(f"No session found with ID: {session_id}")

        module_names = list(self.modules.keys())

        logger.info(f"Starting pipeline on session: {session_id}")
        logger.info(f"Pipeline modules: {', '.join(module_names)}")

        # Run each module in sequence
        for module_name in module_names:
            self.run_module(module_name, session_id)

        logger.info(f"Completed pipeline on session: {session_id}")

    @staticmethod
    def _validate_session_exists(session_id: UUID) -> bool:
        """
        Validate that a session with the given ID exists in the database.

        Args:
            session_id: UUID of the session to validate

        Returns:
            bool: True if the session exists, False otherwise
        """
        for db in get_db():
            statement = select(DBSession).where(DBSession.id == session_id)
            result = db.exec(statement).first()
            return result is not None

        return False
