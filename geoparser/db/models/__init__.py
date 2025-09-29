from geoparser.db.models.document import Document, DocumentCreate, DocumentUpdate
from geoparser.db.models.feature import Feature, FeatureCreate, FeatureUpdate
from geoparser.db.models.gazetteer import Gazetteer, GazetteerCreate, GazetteerUpdate
from geoparser.db.models.project import Project, ProjectCreate, ProjectUpdate
from geoparser.db.models.recognition import (
    Recognition,
    RecognitionCreate,
    RecognitionUpdate,
)
from geoparser.db.models.recognizer import (
    Recognizer,
    RecognizerCreate,
    RecognizerUpdate,
)
from geoparser.db.models.reference import Reference, ReferenceCreate, ReferenceUpdate
from geoparser.db.models.referent import Referent, ReferentCreate, ReferentUpdate
from geoparser.db.models.resolution import (
    Resolution,
    ResolutionCreate,
    ResolutionUpdate,
)
from geoparser.db.models.resolver import Resolver, ResolverCreate, ResolverUpdate
from geoparser.db.models.toponym import (
    Name,
    NameCreate,
    NameFTSTrigrams,
    NameFTSWords,
    NameUpdate,
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
    Name,
    NameCreate,
    Recognition,
    RecognitionCreate,
    Resolution,
    ResolutionCreate,
    Recognizer,
    RecognizerCreate,
    Resolver,
    ResolverCreate,
    Gazetteer,
    GazetteerCreate,
    GazetteerUpdate,
]:
    rebuild.model_rebuild()
