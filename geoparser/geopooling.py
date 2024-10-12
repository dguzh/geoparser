import json
import os

import torch
import torch.nn as nn


class GeoPooling(nn.Module):
    def __init__(self, word_embedding_dimension):
        super(GeoPooling, self).__init__()
        self.word_embedding_dimension = word_embedding_dimension

    def forward(self, features):
        # Retrieve necessary tensors
        token_embeddings = features["token_embeddings"]
        toponym_token_mask = features["toponym_token_mask"].unsqueeze(-1).float()

        # Apply mask to get toponym embeddings
        masked_embeddings = token_embeddings * toponym_token_mask
        # Sum over tokens
        sum_embeddings = torch.sum(masked_embeddings, dim=1)
        # Count of toponym tokens
        toponym_token_counts = torch.clamp(toponym_token_mask.sum(dim=1), min=1e-9)

        # Compute mean embedding
        sentence_embeddings = sum_embeddings / toponym_token_counts

        features["sentence_embedding"] = sentence_embeddings
        return features

    def get_sentence_embedding_dimension(self):
        return self.word_embedding_dimension

    def save(self, output_path):
        with open(os.path.join(output_path, "config.json"), "w") as fOut:
            json.dump({"word_embedding_dimension": self.word_embedding_dimension}, fOut)

    @staticmethod
    def load(input_path):
        with open(os.path.join(input_path, "config.json"), "r") as fIn:
            config = json.load(fIn)
        return GeoPooling(**config)
