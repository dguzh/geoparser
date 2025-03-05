from geoparser.db.models.document import Document, DocumentCreate, DocumentUpdate
from geoparser.db.models.location import Location, LocationCreate, LocationUpdate
from geoparser.db.models.session import (
    Session,
    SessionCreate,
    SessionDownload,
    SessionForTemplate,
    SessionUpdate,
)
from geoparser.db.models.settings import (
    SessionSettings,
    SessionSettingsBase,
    SessionSettingsCreate,
    SessionSettingsUpdate,
)
from geoparser.db.models.toponym import Toponym, ToponymCreate, ToponymUpdate

for rebuild in [
    Session,
    SessionCreate,
    SessionDownload,
    Document,
    DocumentCreate,
]:
    rebuild.model_rebuild()
