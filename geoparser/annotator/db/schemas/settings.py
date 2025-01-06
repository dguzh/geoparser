from pydantic import BaseModel

from geoparser.constants import DEFAULT_SESSION_SETTINGS


class SessionSettings(BaseModel):
    auto_close_annotation_modal: bool = DEFAULT_SESSION_SETTINGS[
        "auto_close_annotation_modal"
    ]
    one_sense_per_discourse: bool = DEFAULT_SESSION_SETTINGS["one_sense_per_discourse"]
