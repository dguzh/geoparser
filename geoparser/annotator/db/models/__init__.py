from .document import Document, DocumentBase, DocumentCreate, DocumentUpdate
from .session import Session, SessionBase, SessionCreate, SessionUpdate
from .settings import (
    SessionSettings,
    SessionSettingsBase,
    SessionSettingsCreate,
    SessionSettingsUpdate,
)
from .toponym import Toponym, ToponymBase, ToponymCreate, ToponymUpdate

for rebuild in [
    Session,
    SessionCreate,
    Document,
    DocumentCreate,
]:
    rebuild.model_rebuild()
