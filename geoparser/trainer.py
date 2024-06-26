import numpy as np
from datasets import Dataset
from haversine import haversine
from sentence_transformers import SentenceTransformerTrainer, losses
from sentence_transformers.training_args import SentenceTransformerTrainingArguments
from spacy.matcher import PhraseMatcher
from tqdm.auto import tqdm

from geoparser.constants import MAX_ERROR
from geoparser.geodoc import GeoDoc
from geoparser.geoparser import Geoparser
from geoparser.geospan import GeoSpan

GeoSpan.set_extension("gold_loc_id", default=None)


class GeoparserTrainer(Geoparser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def annotate(
        self,
        corpus: list[tuple[str, list[tuple[int, int, int]]]],
        include_unmatched: bool = False,
    ):
        docs = []

        matcher = PhraseMatcher(self.nlp.vocab)

        for text, annotations in tqdm(corpus):
            doc = self.nlp(text)
            processed_annotations = []

            for toponym, start_char, end_char, loc_id in annotations:

                if toponym == text[start_char:end_char]:

                    span = doc.char_span(start_char, end_char)

                else:

                    matcher.add("TOPONYM", [self.nlp(toponym)])

                    matches = matcher(doc)

                    if matches:

                        best_match = None
                        best_match_dist = float("inf")

                        for match_id, start_idx, end_idx in matches:
                            match_span = doc[start_idx:end_idx]
                            match_dist = abs(match_span.start_char - start_char) + abs(
                                match_span.end_char - end_char
                            )

                            if match_dist < best_match_dist:
                                best_match = match_span
                                best_match_dist = match_dist

                        span = best_match

                    else:

                        span = None

                    matcher.remove("TOPONYM")

                if span:

                    start_token, end_token = span.start, span.end

                    annotation = GeoSpan(doc, start_token, end_token, label="ANNOT")
                    annotation._.gold_loc_id = loc_id

                    if include_unmatched or annotation in doc.toponyms:
                        processed_annotations.append(annotation)

            sorted_annotations = sorted(processed_annotations, key=lambda x: x.start)

            filtered_annotations = [
                annotation
                for i, annotation in enumerate(sorted_annotations)
                if i == len(sorted_annotations) - 1
                or annotation.end <= sorted_annotations[i + 1].start
            ]

            doc.set_ents(filtered_annotations)

            docs.append(doc)

        return docs

    def evaluate(self, eval_docs: list[GeoDoc]):
        distances = []

        matches = 0

        for doc in tqdm(eval_docs):
            for toponym in doc.toponyms:
                gold_id = toponym._.gold_loc_id
                predicted_id = toponym._.loc_id

                if gold_id is None:
                    continue

                elif predicted_id is None:
                    distances.append(MAX_ERROR)

                elif gold_id == predicted_id:
                    distances.append(0)
                    matches += 1

                else:
                    gold_location = self.gazetteer.query_location_info([gold_id])[0]
                    predicted_location = self.gazetteer.query_location_info(
                        [predicted_id]
                    )[0]

                    if gold_location is None:
                        continue

                    distance = haversine(
                        (gold_location["latitude"], gold_location["longitude"]),
                        (
                            predicted_location["latitude"],
                            predicted_location["longitude"],
                        ),
                    )

                    distances.append(distance)

        accuracy = matches / len(distances)
        accuracy_at_161 = np.mean(np.array(distances) <= 161)
        mean_error_distance = np.mean(distances)

        # Calculate AUC
        adjusted_distances = (
            np.array(distances) + 1
        )  # Avoid zero distance for log scale
        ln_distances = np.log(adjusted_distances)
        auc = np.trapz(sorted(ln_distances)) / (
            np.log(MAX_ERROR) * (len(ln_distances) - 1)
        )

        return {
            "Accuracy": accuracy,
            "Accuracy@161km": accuracy_at_161,
            "MeanErrorDistance": mean_error_distance,
            "AreaUnderTheCurve": auc,
        }

    def prepare_training_data(self, docs: list[GeoDoc]):
        toponym_texts = []
        candidate_texts = []
        labels = []

        for doc in tqdm(docs):
            for toponym in doc.toponyms:
                context = toponym.context.text

                correct_id = toponym._.gold_loc_id
                correct_location = self.gazetteer.query_location_info(correct_id)[0]

                candidate_ids = toponym.candidates
                candidate_locations = self.gazetteer.query_location_info(candidate_ids)

                for candidate_location in candidate_locations:
                    description = self.gazetteer.get_location_description(
                        candidate_location
                    )
                    label = 1 if candidate_location == correct_location else 0
                    toponym_texts.append(context)
                    candidate_texts.append(description)
                    labels.append(label)

        return Dataset.from_dict(
            {
                "toponym_texts": toponym_texts,
                "candidate_texts": candidate_texts,
                "label": labels,
            }
        )

    def train(
        self,
        train_docs: list[GeoDoc],
        output_path: str,
        epochs: int = 1,
        batch_size: int = 8,
    ):
        train_dataset = self.prepare_training_data(train_docs)

        train_loss = losses.ContrastiveLoss(self.transformer)

        training_args = SentenceTransformerTrainingArguments(
            output_dir=output_path,
            num_train_epochs=epochs,
            per_device_train_batch_size=batch_size,
            warmup_ratio=0.1,
            save_strategy="no",
        )

        trainer = SentenceTransformerTrainer(
            model=self.transformer,
            args=training_args,
            train_dataset=train_dataset,
            loss=train_loss,
        )

        trainer.train()

        self.transformer.save(output_path)
