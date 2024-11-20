from __future__ import annotations

import json
import re
import typing as t
from pathlib import Path

import numpy as np
from datasets import Dataset
from haversine import haversine
from sentence_transformers import SentenceTransformerTrainer, losses
from sentence_transformers.training_args import SentenceTransformerTrainingArguments
from tqdm.auto import tqdm

from geoparser.constants import MAX_ERROR
from geoparser.geodoc import GeoDoc
from geoparser.geoparser import Geoparser
from geoparser.geospan import GeoSpan

GeoSpan.set_extension("gold_loc_id", default=None)


class GeoparserTrainer(Geoparser):
    """Class for training the Geoparser's toponym disambiguation model."""

    def __init__(self, *args, **kwargs):
        """
        Initialize the GeoparserTrainer with inherited Geoparser parameters.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(*args, **kwargs)

    def _find_toponym(
        self, toponym: str, doc: GeoDoc, start_char: int, end_char: int
    ) -> t.Tuple[int, int]:
        """
        Adjust character indices for imprecise toponym annotations.

        Args:
            toponym (str): The toponym text to find.
            doc (GeoDoc): The document to search within.
            start_char (int): The starting character index.
            end_char (int): The ending character index.

        Returns:
            Tuple[int, int]: A tuple containing the best match start and end character indices.
        """
        matches = [
            (m.start(), m.end())
            for m in re.finditer(re.escape(toponym), doc.text, flags=re.IGNORECASE)
        ]

        best_match_chars = (0, 0)
        best_match_dist = float("inf")

        for match_start_char, match_end_char in matches:

            match_dist = abs(match_start_char - start_char) + abs(
                match_end_char - end_char
            )
            if match_dist < best_match_dist:

                best_match_chars = (match_start_char, match_end_char)
                best_match_dist = match_dist

        return best_match_chars

    def _retokenize_toponym(self, doc: GeoDoc, start_char: int, end_char: int) -> None:
        """
        Retokenize the document to ensure the toponym span aligns with spaCy tokens.

        Args:
            doc (GeoDoc): The document containing the toponym.
            start_char (int): The starting character index of the toponym.
            end_char (int): The ending character index of the toponym.
        """
        with doc.retokenize() as retokenizer:

            expanded_span = doc.char_span(start_char, end_char, alignment_mode="expand")

            if expanded_span:

                for token in expanded_span:

                    split_positions = [
                        max(start_char - token.idx, 0),
                        min(end_char - token.idx, len(token.text)),
                    ]

                    sub_tokens = [
                        token.text[: split_positions[0]],
                        token.text[split_positions[0] : split_positions[1]],
                        token.text[split_positions[1] :],
                    ]

                    sub_tokens = [sub_token for sub_token in sub_tokens if sub_token]

                    heads = [(token, 0) for _ in sub_tokens]

                    retokenizer.split(token, sub_tokens, heads=heads)

    @staticmethod
    def _load_json_file(
        json_file_path: t.Union[str, Path]
    ) -> t.List[t.Dict[str, t.Any]]:
        """
        Load a JSON annotation file and transform it into a list of dictionaries.

        Args:
            json_file_path (Union[str, Path]): Path to the JSON annotation file.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, where each dictionary represents a document with toponym annotations.
        """
        with open(json_file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        corpus = [
            {
                "text": document["text"],
                "toponyms": [
                    {
                        "text": toponym["text"],
                        "start": toponym["start"],
                        "end": toponym["end"],
                        "loc_id": toponym["loc_id"],
                    }
                    for toponym in document.get("toponyms", [])
                ],
            }
            for document in data.get("documents", [])
        ]

        return corpus

    def annotate(
        self,
        corpus: t.Union[t.List[t.Dict[str, t.Any]], str, Path],
        include_unmatched: bool = False,
    ) -> t.List[GeoDoc]:
        """
        Load annotations with toponym spans and gold location IDs.

        Args:
            corpus (Union[List[Dict[str, Any]], str, Path]): Either a list of dictionaries containing text and toponym annotations or a path to a JSON annotation file.
            include_unmatched (bool, optional): Whether to include spaCy-unmatched annotations. Defaults to False.

        Returns:
            List[GeoDoc]: A list of annotated GeoDoc objects.
        """
        if isinstance(corpus, (str, Path)) and Path(corpus).suffix == ".json":
            corpus = self._load_json_file(corpus)

        docs = []

        for document in tqdm(corpus):
            text = document["text"]
            annotations = document.get("toponyms", [])

            doc = self.nlp(text)
            processed_annotations = []

            for toponym in sorted(annotations, key=lambda x: x["start"]):
                start_char, end_char, loc_id = (
                    toponym["start"],
                    toponym["end"],
                    toponym["loc_id"],
                )
                toponym_text = toponym["text"].strip()

                if toponym_text != text[start_char:end_char]:
                    start_char, end_char = self._find_toponym(
                        toponym_text, doc, start_char, end_char
                    )

                span = doc.char_span(start_char, end_char)

                if not span and toponym_text in doc.text:
                    self._retokenize_toponym(doc, start_char, end_char)
                    span = doc.char_span(start_char, end_char)

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

    def _calculate_auc(self, distances: t.List[float]) -> float:
        """
        Calculate the Area Under the Curve (AUC) for error distances.

        Args:
            distances (List[float]): List of error distances between predicted and gold locations.

        Returns:
            float: The calculated AUC value.
        """
        adjusted_distances = (
            np.array(distances) + 1
        )  # Avoid zero distance for log scale
        ln_distances = np.log(adjusted_distances)
        auc = np.trapezoid(sorted(ln_distances)) / (
            np.log(MAX_ERROR) * (len(ln_distances) - 1)
        )
        return auc

    def evaluate(self, eval_docs: t.List[GeoDoc]) -> t.Dict[str, float]:
        """
        Evaluate the model on a list of annotated documents.

        Args:
            eval_docs (List[GeoDoc]): List of annotated GeoDoc objects for evaluation.

        Returns:
            Dict[str, float]: A dictionary containing evaluation metrics.
        """
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
                    gold_location = self.gazetteer.query_locations([gold_id])[0]
                    predicted_location = self.gazetteer.query_locations([predicted_id])[
                        0
                    ]

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
        auc = self._calculate_auc(distances)

        return {
            "Accuracy": accuracy,
            "Accuracy@161km": accuracy_at_161,
            "MeanErrorDistance": mean_error_distance,
            "AreaUnderTheCurve": auc,
        }

    def _prepare_training_data(self, docs: t.List[GeoDoc]) -> Dataset:
        """
        Prepare the training data from annotated documents.

        Args:
            docs (List[GeoDoc]): List of annotated GeoDoc objects for training.

        Returns:
            Dataset: A HuggingFace Dataset containing training examples.
        """
        toponym_texts = []
        candidate_texts = []
        labels = []

        for doc in tqdm(docs):
            for toponym in doc.toponyms:
                context = toponym.context.text

                correct_id = toponym._.gold_loc_id
                correct_location = self.gazetteer.query_locations(correct_id)[0]

                if correct_location:

                    candidate_ids = toponym.get_candidates()
                    candidate_locations = self.gazetteer.query_locations(candidate_ids)

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
        train_docs: t.List[GeoDoc],
        output_path: str,
        epochs: int = 1,
        batch_size: int = 8,
    ) -> None:
        """
        Train the toponym disambiguation model using the prepared training data.

        Args:
            train_docs (List[GeoDoc]): List of annotated GeoDoc objects for training.
            output_path (str): Directory path to save the trained model.
            epochs (int, optional): Number of training epochs. Defaults to 1.
            batch_size (int, optional): Training batch size. Defaults to 8.
        """
        train_dataset = self._prepare_training_data(train_docs)

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
