from .document import (
    Document,
    DocumentBase,
    DocumentCreate,
    DocumentDownload,
    DocumentUpdate,
)
from .session import Session, SessionBase, SessionCreate, SessionDownload, SessionUpdate
from .settings import (
    SessionSettings,
    SessionSettingsBase,
    SessionSettingsCreate,
    SessionSettingsDownload,
    SessionSettingsUpdate,
)
from .toponym import Toponym, ToponymBase, ToponymCreate, ToponymDownload, ToponymUpdate

for rebuild in [
    Session,
    SessionCreate,
    SessionDownload,
    Document,
    DocumentCreate,
    DocumentDownload,
]:
    rebuild.model_rebuild()
