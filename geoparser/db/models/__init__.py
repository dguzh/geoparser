from geoparser.db.models.document import Document, DocumentCreate, DocumentUpdate
from geoparser.db.models.feature import Feature, FeatureCreate, FeatureUpdate
from geoparser.db.models.gazetteer import Gazetteer, GazetteerCreate, GazetteerUpdate
from geoparser.db.models.project import Project, ProjectCreate, ProjectUpdate
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
from geoparser.db.models.reference import Reference, ReferenceCreate, ReferenceUpdate
from geoparser.db.models.referent import Referent, ReferentCreate, ReferentUpdate
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
from geoparser.db.models.toponym import (
    Toponym,
    ToponymCreate,
    ToponymFTS,
    ToponymUpdate,
)

for rebuild in [
    Project,
    ProjectCreate,
    Document,
    DocumentCreate,
    Reference,
    ReferenceCreate,
    Referent,
    ReferentCreate,
    Feature,
    FeatureCreate,
    Toponym,
    ToponymCreate,
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
    Gazetteer,
    GazetteerCreate,
    GazetteerUpdate,
]:
    rebuild.model_rebuild()
