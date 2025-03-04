import typing as t
from abc import ABC, abstractmethod
from uuid import UUID

from sqlmodel import Session


class BaseModule(ABC):
    """
    Abstract base class for any pipeline module.
    
    All pipeline modules must implement this interface to be compatible
    with the PipelineOrchestrator.
    """
    
    def __init__(self, name: str, description: str = ""):
        """
        Initialize a pipeline module.
        
        Args:
            name: A unique name for this module
            description: An optional description of the module's functionality
        """
        self.name = name
        self.description = description
    
    @abstractmethod
    def run(self, session_id: UUID) -> None:
        """
        Execute the module's functionality on the specified session.
        
        The module should read and write to the database as needed.
        
        Args:
            session_id: UUID of the session to process
        """
        pass


class ToponymRecognitionModule(BaseModule):
    """
    Abstract class for modules that perform toponym recognition.
    
    These modules identify potential toponyms in text and save them to the database.
    """
    
    @abstractmethod
    def run(self, session_id: UUID) -> None:
        """
        Execute toponym recognition on documents in the specified session.
        
        Args:
            session_id: UUID of the session to process
        """
        pass


class ToponymResolutionModule(BaseModule):
    """
    Abstract class for modules that perform toponym resolution.
    
    These modules link recognized toponyms to specific locations in a gazetteer.
    """
    
    @abstractmethod
    def run(self, session_id: UUID) -> None:
        """
        Execute toponym resolution on toponyms in the specified session.
        
        Args:
            session_id: UUID of the session to process
        """
        pass 