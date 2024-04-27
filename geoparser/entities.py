from typing import List

class Location:
    def __init__(self, geonameid: int, name: str, admin2_geonameid: int, admin2_name: str, 
                 admin1_geonameid: int, admin1_name: str, country_geonameid: int, 
                 country_name: str, feature_name: str, latitude: float, longitude: float, 
                 elevation: int, population: int):
        self.geonameid = geonameid
        self.name = name
        self.admin2_geonameid = admin2_geonameid
        self.admin2_name = admin2_name
        self.admin1_geonameid = admin1_geonameid
        self.admin1_name = admin1_name
        self.country_geonameid = country_geonameid
        self.country_name = country_name
        self.feature_name = feature_name
        self.latitude = latitude
        self.longitude = longitude
        self.elevation = elevation
        self.population = population

    def __str__(self):
        return f"{self.name} (https://www.geonames.org/{self.geonameid})"

class Toponym:
    def __init__(self, name: str, start_char: int, end_char: int, context: str):
        self.name = name
        self.start_char = start_char
        self.end_char = end_char
        self.context = context
        self.location = None

    def __str__(self):
        return f"{self.name} ({self.start_char}:{self.end_char})"

class Document:
    def __init__(self, text: str):
        self.text = text
        self.toponyms: List[Toponym] = []

    def __str__(self):
        return self.text
        