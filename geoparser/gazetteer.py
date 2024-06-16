import os
import re
import sqlite3
from abc import ABC, abstractmethod
from appdirs import user_data_dir


class Gazetteer(ABC):
    def __init__(self, db_name):
        self.data_dir = user_data_dir("geoparser", "")
        self.db_path = os.path.join(self.data_dir, db_name + ".db")

    @abstractmethod
    def setup_database(self):
        pass

    @abstractmethod
    def query_candidates(self):
        pass

    @abstractmethod
    def query_location_info(self):
        pass

    def execute_query(self, query, params=None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            return cursor.fetchall()

    def get_location_description(self, location):
        return self.format_location_description(
            location, self.location_description_template
        )

    @staticmethod
    def format_location_description(location, template):
        if location:

            def evaluate_conditionals(cond_expr):
                match = re.match(r"COND\[(.+?), (any|all)\{(.+?)\}\]", cond_expr)
                if not match:
                    return None, None

                text, condition_type, keys = match.groups()
                keys = [key.strip("<> ") for key in keys.split(",")]

                if condition_type == "any":
                    return text, lambda loc: any(loc.get(key) for key in keys)
                elif condition_type == "all":
                    return text, lambda loc: all(loc.get(key) for key in keys)
                return None, None

            def substitute_conditionals(template):
                conditionals = re.findall(r"COND\[.+?\]", template)
                for cond in conditionals:
                    text, conditional_func = evaluate_conditionals(cond)
                    if conditional_func:
                        replacement_text = text if conditional_func(location) else ""
                        template = template.replace(cond, replacement_text, 1)
                return template

            def substitute_keys(match):
                key = match.group("key")
                value = location.get(key)
                return (
                    f"{match.group('pre')}{value}{match.group('post')}" if value else ""
                )

            template = substitute_conditionals(template)
            formatted_text = re.sub(
                r"(?P<pre>[^\s<>]*?)<(?P<key>\w+)>(?P<post>[^\s<>]*)",
                substitute_keys,
                template,
            )
            formatted_text = re.sub(r"\s*,\s*", ", ", formatted_text)
            formatted_text = re.sub(r",\s*$", "", formatted_text)
            formatted_text = re.sub(r"\s+", " ", formatted_text)

            return formatted_text.strip()
