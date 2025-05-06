from geoparser.db.models.document import (
    Document,
    DocumentCreate,
    DocumentRead,
    DocumentUpdate,
)
from geoparser.db.models.gazetteer import Gazetteer, GazetteerCreate, GazetteerUpdate
from geoparser.db.models.gazetteer_relationship import (
    GazetteerRelationship,
    GazetteerRelationshipCreate,
    GazetteerRelationshipUpdate,
)
from geoparser.db.models.gazetteer_table import (
    GazetteerTable,
    GazetteerTableCreate,
    GazetteerTableUpdate,
)
from geoparser.db.models.location import (
    Location,
    LocationCreate,
    LocationRead,
    LocationUpdate,
)
from geoparser.db.models.project import Project, ProjectCreate, ProjectUpdate
from geoparser.db.models.recognition_module import (
    RecognitionModule,
    RecognitionModuleCreate,
    RecognitionModuleRead,
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
    ResolutionModuleRead,
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
from geoparser.db.models.toponym import (
    Toponym,
    ToponymCreate,
    ToponymRead,
    ToponymUpdate,
)

for rebuild in [
    Project,
    ProjectCreate,
    Document,
    DocumentCreate,
    DocumentRead,
    Toponym,
    ToponymCreate,
    ToponymRead,
    Location,
    LocationCreate,
    LocationRead,
    RecognitionObject,
    RecognitionObjectCreate,
    ResolutionObject,
    ResolutionObjectCreate,
    RecognitionModule,
    RecognitionModuleCreate,
    RecognitionModuleRead,
    ResolutionModule,
    ResolutionModuleCreate,
    ResolutionModuleRead,
    RecognitionSubject,
    RecognitionSubjectCreate,
    ResolutionSubject,
    ResolutionSubjectCreate,
    Gazetteer,
    GazetteerCreate,
    GazetteerUpdate,
    GazetteerRelationship,
    GazetteerRelationshipCreate,
    GazetteerRelationshipUpdate,
    GazetteerTable,
    GazetteerTableCreate,
    GazetteerTableUpdate,
]:
    rebuild.model_rebuild()
