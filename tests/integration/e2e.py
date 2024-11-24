#########################################################
# GeoNames
#########################################################


from geoparser import Geoparser

geo = Geoparser(
    spacy_model="en_core_web_sm",
    transformer_model="dguzh/geo-all-MiniLM-L6-v2",
    gazetteer="geonames",
)

texts = [
    "Zurich is a city rich in history.",
    "Geneva is known for its role in international diplomacy.",
    "Munich is famous for its annual Oktoberfest celebration.",
]

docs = geo.parse(texts)

for doc in docs:
    identifiers = [(l["name"], l["admin1_name"], l["country_name"]) for l in doc.locations]
    for toponym, identifier in zip(doc.toponyms, identifiers):
        print(toponym, "->", identifier)

#########################################################
# Trainer
#########################################################

from geoparser import GeoparserTrainer

train_corpus = [
    {
        "text": "Zurich is a city in Switzerland.",
        "toponyms": [
            {"text": "Zurich", "start": 0, "end": 6, "loc_id": "2657896"},
            {"text": "Switzerland", "start": 20, "end": 31, "loc_id": "2658434"}
        ]
    },
    {
        "text": "Geneva is known for international diplomacy.",
        "toponyms": [
            {"text": "Geneva", "start": 0, "end": 6, "loc_id": "2660646"}
        ]
    },
    {
        "text": "Munich hosts the annual Oktoberfest.",
        "toponyms": [
            {"text": "Munich", "start": 0, "end": 6, "loc_id": "2867714"}
        ]
    }
]

trainer = GeoparserTrainer(
    spacy_model="en_core_web_sm", transformer_model="bert-base-uncased"
)

train_docs = trainer.annotate(train_corpus)

output_path = "path_to_custom_model"

trainer.train(train_docs, output_path=output_path)

test_docs = trainer.annotate(train_corpus)

trainer.resolve(test_docs)

evaluation_results = trainer.evaluate(test_docs)

print(evaluation_results)

#########################################################
# Use model
#########################################################

from geoparser import Geoparser

geo = Geoparser(spacy_model="en_core_web_sm", transformer_model="path_to_custom_model")

docs = geo.parse(["New text to parse"])
