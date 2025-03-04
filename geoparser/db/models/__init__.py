from .document import Document, DocumentBase, DocumentCreate, DocumentUpdate
from .run import Run, RunBase, RunCreate, RunUpdate
from .session import (
    Session,
    SessionBase,
    SessionCreate,
    SessionDownload,
    SessionForTemplate,
    SessionUpdate,
)
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
    SessionDownload,
    Document,
    DocumentCreate,
    Run,
    RunCreate,
]:
    rebuild.model_rebuild()
