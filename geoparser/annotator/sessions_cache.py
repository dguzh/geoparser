import json
import os
import typing as t
from datetime import datetime

from appdirs import user_data_dir


class SessionsCache:
    def __init__(self, cache_dir: str = "annotator"):
        self.cache_dir = os.path.join(user_data_dir("geoparser", ""), cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)

    def file_path(self, session_id: str) -> str:
        return os.path.join(self.cache_dir, f"{session_id}.json")

    def save(self, session_id: str, to_json: dict):
        with open(self.file_path(session_id), "w", encoding="utf-8") as f:
            json.dump(to_json, f, ensure_ascii=False, indent=4)

    def load(self, session_id: str) -> t.Optional[dict]:
        session_file_path = self.file_path(session_id)
        if os.path.exists(session_file_path):
            try:
                with open(session_file_path, "r", encoding="utf-8") as f:
                    session_data = json.load(f)
                    return session_data
            except Exception as e:
                print(f"Failed to load session {session_id}: {e}")
                return None
        else:
            return None

    def delete(self, session_id: str) -> bool:
        session_file_path = self.file_path(session_id)
        if os.path.exists(session_file_path):
            os.remove(session_file_path)
            return True
        else:
            return False

    def get_cached_sessions(self) -> list[dict]:
        sessions = []
        for filename in os.listdir(self.cache_dir):
            if filename.endswith(".json") and not filename.endswith("_download.json"):
                session_file_path = os.path.join(self.cache_dir, filename)
                try:
                    with open(session_file_path, "r", encoding="utf-8") as f:
                        session_data = json.load(f)
                        session_id = session_data.get("session_id", filename[:-5])

                        # Format creation date
                        created_at = session_data.get("created_at", "Unknown")
                        try:
                            created_at_dt = datetime.fromisoformat(created_at)
                            created_at_formatted = created_at_dt.strftime(
                                "%Y-%m-%d %H:%M:%S"
                            )
                        except ValueError:
                            created_at_formatted = created_at

                        # Format last updated date
                        last_updated = session_data.get("last_updated", "Unknown")
                        try:
                            last_updated_dt = datetime.fromisoformat(last_updated)
                            last_updated_formatted = last_updated_dt.strftime(
                                "%Y-%m-%d %H:%M:%S"
                            )
                        except ValueError:
                            last_updated_formatted = last_updated

                        gazetteer = session_data.get("gazetteer", "Unknown")
                        num_documents = len(session_data.get("documents", []))
                        sessions.append(
                            {
                                "session_id": session_id,
                                "created_at": created_at_formatted,
                                "last_updated": last_updated_formatted,
                                "gazetteer": gazetteer,
                                "num_documents": num_documents,
                            }
                        )
                except Exception as e:
                    print(f"Failed to load session {filename}: {e}")
                    continue
        # Sort sessions by last updated date descending
        sessions.sort(key=lambda x: x["last_updated"], reverse=True)
        return sessions
