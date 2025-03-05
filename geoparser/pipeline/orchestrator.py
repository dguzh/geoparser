import logging
import typing as t
from uuid import UUID

from geoparser.pipeline.modules import ToponymRecognitionModule, ToponymResolutionModule

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Orchestrates the execution of pipeline modules.

    This class coordinates the flow of data between modules and the database,
    providing a central point for running a geoparsing pipeline.
    """

    def __init__(
        self,
        recognition_module: t.Optional[ToponymRecognitionModule] = None,
        resolution_module: t.Optional[ToponymResolutionModule] = None,
    ):
        """
        Initialize the pipeline orchestrator with optional recognition and resolution modules.

        Args:
            recognition_module: The toponym recognition module to use
            resolution_module: The toponym resolution module to use
        """
        self.recognition_module = recognition_module
        self.resolution_module = resolution_module

        # Log module initialization
        if recognition_module:
            logger.info(
                f"Pipeline initialized with recognition module: {recognition_module.name}"
            )

        if resolution_module:
            logger.info(
                f"Pipeline initialized with resolution module: {resolution_module.name}"
            )

    def _should_run_recognition(self, session_id: UUID) -> bool:
        """
        Simplified placeholder to determine if recognition should run.

        This will be replaced with more sophisticated logic later.

        Args:
            session_id: UUID of the session to check

        Returns:
            bool: True if recognition should run, False otherwise
        """
        # Always return True for now
        return True

    def _should_run_resolution(self, session_id: UUID) -> bool:
        """
        Simplified placeholder to determine if resolution should run.

        This will be replaced with more sophisticated logic later.

        Args:
            session_id: UUID of the session to check

        Returns:
            bool: True if resolution should run, False otherwise
        """
        # Always return True for now
        return True

    def run_recognition(self, session_id: UUID) -> None:
        """
        Run the registered recognition module on the specified session.

        Args:
            session_id: UUID of the session to process
        """
        if self.recognition_module is None:
            logger.warning("No recognition module registered")
            return

        # Check if we need to run this module
        if not self._should_run_recognition(session_id):
            logger.info(
                f"Skipping recognition module: {self.recognition_module.name} on session: {session_id}"
            )
            return

        logger.info(
            f"Running recognition module: {self.recognition_module.name} on session: {session_id}"
        )
        self.recognition_module.run(session_id)
        logger.info(
            f"Completed recognition module: {self.recognition_module.name} on session: {session_id}"
        )

    def run_resolution(self, session_id: UUID) -> None:
        """
        Run the registered resolution module on the specified session.

        Args:
            session_id: UUID of the session to process
        """
        if self.resolution_module is None:
            logger.warning("No resolution module registered")
            return

        if self.recognition_module is None:
            logger.warning(
                "No recognition module registered - needed to identify source toponyms"
            )
            return

        # Check if we need to run this module
        if not self._should_run_resolution(session_id):
            logger.info(
                f"Skipping resolution module: {self.resolution_module.name} on session: {session_id}"
            )
            return

        logger.info(
            f"Running resolution module: {self.resolution_module.name} on session: {session_id}"
        )
        self.resolution_module.run(session_id)
        logger.info(
            f"Completed resolution module: {self.resolution_module.name} on session: {session_id}"
        )

    def run_pipeline(self, session_id: UUID) -> None:
        """
        Run the complete pipeline on the session.

        Args:
            session_id: UUID of the session to process
        """
        logger.info(f"Starting pipeline on session: {session_id}")

        # Run recognition
        self.run_recognition(session_id)

        # Run resolution
        self.run_resolution(session_id)

        logger.info(f"Completed pipeline on session: {session_id}")
