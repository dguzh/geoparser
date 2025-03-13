from geoparser.db.models.document import Document, DocumentCreate, DocumentUpdate
from geoparser.db.models.location import Location, LocationCreate, LocationUpdate
from geoparser.db.models.recognition import (
    Recognition,
    RecognitionCreate,
    RecognitionUpdate,
)
from geoparser.db.models.recognition_module import (
    RecognitionModule,
    RecognitionModuleCreate,
    RecognitionModuleUpdate,
)
from geoparser.db.models.resolution import (
    Resolution,
    ResolutionCreate,
    ResolutionUpdate,
)
from geoparser.db.models.resolution_module import (
    ResolutionModule,
    ResolutionModuleCreate,
    ResolutionModuleUpdate,
)
from geoparser.db.models.session import Session, SessionCreate, SessionUpdate
from geoparser.db.models.settings import (  # SessionSettings,  # Commented out to disable the SessionSettings model
    SessionSettingsBase,
    SessionSettingsCreate,
    SessionSettingsUpdate,
)
from geoparser.db.models.toponym import Toponym, ToponymCreate, ToponymUpdate

for rebuild in [
    Session,
    SessionCreate,
    Document,
    DocumentCreate,
    Toponym,
    ToponymCreate,
    Location,
    LocationCreate,
    Recognition,
    RecognitionCreate,
    Resolution,
    ResolutionCreate,
    RecognitionModule,
    RecognitionModuleCreate,
    ResolutionModule,
    ResolutionModuleCreate,
]:
    rebuild.model_rebuild()
