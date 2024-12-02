import typer

from geoparser import Geoparser


def run_gazetteer(gazetteer: str):
    print("----------\nrun_gazetteer\n----------")
    geo = Geoparser(
        spacy_model="en_core_web_sm",
        transformer_model="dguzh/geo-all-MiniLM-L6-v2",
        gazetteer=gazetteer,
    )
    texts = [
        "Zurich is a city rich in history.",
        "Geneva is known for its role in international diplomacy.",
    ]
    docs = geo.parse(texts)
    for doc in docs:
        name = "name" if gazetteer == "geonames" else "NAME"
        identifier1 = "admin1_name" if gazetteer == "geonames" else "BEZIRK_NAME"
        identifier2 = "country_name" if gazetteer == "geonames" else "KANTON_NAME"
        identifiers = [(l[name], l[identifier1], l[identifier2]) for l in doc.locations]
        for toponym, identifier in zip(doc.toponyms, identifiers):
            print(toponym, "->", identifier)


def main(gazetteer: str):
    run_gazetteer(gazetteer)


if __name__ == "__main__":
    typer.run(main)
