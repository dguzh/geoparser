import json
import os

import torch
from sentence_transformers.models import Transformer
from transformers import AutoModel, AutoTokenizer


class GeoTransformer(Transformer):
    def __init__(self, model_name_or_path, max_seq_length=None, do_lower_case=True):
        super().__init__(
            model_name_or_path,
            max_seq_length=max_seq_length,
            do_lower_case=do_lower_case,
        )

    def tokenize(self, texts, **kwargs):
        # Expecting texts to be a list of dicts with 'text' and 'toponym_positions'
        sentences = []
        toponym_positions_list = []
        for item in texts:
            sentences.append(item["text"])
            toponym_positions_list.append(item["toponym_positions"])

        # Tokenize the sentences
        output = self.tokenizer(
            sentences,
            padding="longest",
            truncation=True,
            max_length=self.max_seq_length,
            return_tensors="pt",
            return_attention_mask=True,
            return_token_type_ids=True,
            return_offsets_mapping=True,
        )

        # Compute toponym_token_mask
        toponym_token_mask_list = []
        for i, offsets in enumerate(output["offset_mapping"]):
            start_char, end_char = toponym_positions_list[i]
            toponym_token_mask = []
            for offset_start, offset_end in offsets:
                if offset_end == 0:
                    toponym_token_mask.append(0)
                    continue
                if offset_start >= end_char:
                    toponym_token_mask.append(0)
                    continue
                if offset_end <= start_char:
                    toponym_token_mask.append(0)
                    continue
                # Overlaps with toponym
                toponym_token_mask.append(1)
            toponym_token_mask_list.append(toponym_token_mask)

        # Convert to tensor and pad
        toponym_token_mask_tensor = torch.nn.utils.rnn.pad_sequence(
            [torch.tensor(mask) for mask in toponym_token_mask_list], batch_first=True
        )
        output["toponym_token_mask"] = toponym_token_mask_tensor

        # Remove 'offset_mapping' as it's no longer needed
        output.pop("offset_mapping", None)

        return output

    def forward(self, features):
        output_states = self.auto_model(
            input_ids=features["input_ids"],
            attention_mask=features["attention_mask"],
            token_type_ids=features.get("token_type_ids"),
        )
        features["token_embeddings"] = output_states[0]
        features["attention_mask"] = features["attention_mask"]
        # 'toponym_token_mask' is already in features
        return features

    def save(self, output_path):
        # Save the model and tokenizer
        self.auto_model.save_pretrained(output_path)
        self.tokenizer.save_pretrained(output_path)
        # Save configuration
        with open(os.path.join(output_path, "sentence_bert_config.json"), "w") as fOut:
            json.dump(
                {
                    "max_seq_length": self.max_seq_length,
                    "do_lower_case": self.do_lower_case,
                },
                fOut,
            )

    @staticmethod
    def load(input_path):
        # Load model and tokenizer
        tokenizer = AutoTokenizer.from_pretrained(input_path)
        model = AutoModel.from_pretrained(input_path)
        # Load configuration
        with open(os.path.join(input_path, "sentence_bert_config.json"), "r") as fIn:
            config = json.load(fIn)
        return GeoTransformer(model_name_or_path=input_path, **config)
