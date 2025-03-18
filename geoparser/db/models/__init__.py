from geoparser.db.models.document import Document, DocumentCreate, DocumentUpdate
from geoparser.db.models.location import Location, LocationCreate, LocationUpdate
from geoparser.db.models.recognition_module import (
    RecognitionModule,
    RecognitionModuleCreate,
    RecognitionModuleUpdate,
)
from geoparser.db.models.recognition_object import (
    RecognitionObject,
    RecognitionObjectCreate,
    RecognitionObjectUpdate,
)
from geoparser.db.models.recognition_subject import (
    RecognitionSubject,
    RecognitionSubjectCreate,
    RecognitionSubjectUpdate,
)
from geoparser.db.models.resolution_module import (
    ResolutionModule,
    ResolutionModuleCreate,
    ResolutionModuleUpdate,
)
from geoparser.db.models.resolution_object import (
    ResolutionObject,
    ResolutionObjectCreate,
    ResolutionObjectUpdate,
)
from geoparser.db.models.resolution_subject import (
    ResolutionSubject,
    ResolutionSubjectCreate,
    ResolutionSubjectUpdate,
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
    RecognitionObject,
    RecognitionObjectCreate,
    ResolutionObject,
    ResolutionObjectCreate,
    RecognitionModule,
    RecognitionModuleCreate,
    ResolutionModule,
    ResolutionModuleCreate,
    RecognitionSubject,
    RecognitionSubjectCreate,
    ResolutionSubject,
    ResolutionSubjectCreate,
]:
    rebuild.model_rebuild()
