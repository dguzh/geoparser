from .document import (
    Document,
    DocumentBase,
    DocumentCreate,
    DocumentGet,
    DocumentUpdate,
)
from .session import Session, SessionBase, SessionCreate, SessionGet, SessionUpdate
from .settings import (
    SessionSettings,
    SessionSettingsBase,
    SessionSettingsCreate,
    SessionSettingsGet,
    SessionSettingsUpdate,
)
from .toponym import Toponym, ToponymBase, ToponymCreate, ToponymGet, ToponymUpdate

for rebuild in [Session, SessionCreate, Document, DocumentCreate]:
    rebuild.model_rebuild()
