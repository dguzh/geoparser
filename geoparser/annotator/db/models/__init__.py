from .document import (
    AnnotatorDocument,
    AnnotatorDocumentBase,
    AnnotatorDocumentCreate,
    AnnotatorDocumentUpdate,
)
from .session import (
    AnnotatorSession,
    AnnotatorSessionBase,
    AnnotatorSessionCreate,
    AnnotatorSessionDownload,
    AnnotatorSessionForTemplate,
    AnnotatorSessionUpdate,
)
from .settings import (
    AnnotatorSessionSettings,
    AnnotatorSessionSettingsBase,
    AnnotatorSessionSettingsCreate,
    AnnotatorSessionSettingsUpdate,
)
from .toponym import (
    AnnotatorToponym,
    AnnotatorToponymBase,
    AnnotatorToponymCreate,
    AnnotatorToponymUpdate,
)

for rebuild in [
    AnnotatorSession,
    AnnotatorSessionCreate,
    AnnotatorSessionDownload,
    AnnotatorDocument,
    AnnotatorDocumentCreate,
]:
    rebuild.model_rebuild()
