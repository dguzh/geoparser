import torch
from sentence_transformers.data_collator import SentenceTransformerDataCollator

class GeoDataCollator:
    def __init__(self, tokenize_fn):
        self.tokenize_fn = tokenize_fn
        self.valid_label_columns = ['label']

    def __call__(self, batch):
        labels = torch.tensor([item['label'] for item in batch], dtype=torch.float)
        toponym_inputs = [item['toponym_inputs'] for item in batch]
        candidate_inputs = [item['candidate_inputs'] for item in batch]

        toponym_features = self.tokenize_fn(toponym_inputs)
        candidate_features = self.tokenize_fn(candidate_inputs)

        batch_features = {}

        for key in toponym_features:
            batch_features[f'sentence_0_{key}'] = toponym_features[key]
        for key in candidate_features:
            batch_features[f'sentence_1_{key}'] = candidate_features[key]

        batch_features['label'] = labels

        return batch_features
