import datetime
import uuid


def get_session(gazetteer: str):
    session_id = uuid.uuid4().hex
    session = {
        "session_id": session_id,
        "created_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "gazetteer": gazetteer,
        "settings": {
            "one_sense_per_discourse": False,
            "auto_close_annotation_modal": False,
        },
        "documents": [],
    }
    return session
