from __future__ import annotations

import typing as t

from spacy.tokens import Span


class GeoSpan(Span):
    """Custom spaCy Span class extended for geoparsing."""

    def __eq__(self, other: GeoSpan) -> bool:
        """
        Check equality of GeoSpan with another GeoSpan.

        Args:
            other (GeoSpan): Another GeoSpan object to compare with.

        Returns:
            bool: True if both GeoSpans are equal, False otherwise.
        """
        return (
            self.doc.text == other.doc.text
            and self.start == other.start
            and self.end == other.end
        )

    @property
    def location(self) -> t.Dict[str, t.Any]:
        """
        Get the location information associated with this toponym.

        Returns:
            Dict[str, Any]: Dictionary containing location information.
        """
        return self.doc.geoparser.gazetteer.query_locations(self._.loc_id)[0]

    @property
    def score(self) -> float:
        """
        Get the similarity score for the resolved location.

        Returns:
            float: Similarity score between toponym and resolved location.
        """
        return self._.loc_score

    @property
    def context(self) -> Span:
        """
        Get the contextual Span around the toponym, truncated to model input size.

        Returns:
            Span: The context Span for the toponym.
        """
        tokenizer = self.doc.geoparser.transformer.tokenizer
        token_limit = self.doc.geoparser.transformer.get_max_seq_length()

        sentences = list(self.doc.sents)
        total_tokens = self.doc.transformer_token_count

        if total_tokens <= token_limit:
            return self.doc[:]

        target_sentence = self.sent
        target_index = sentences.index(target_sentence)
        context_sentences = [target_sentence]
        tokens_count = len(tokenizer.tokenize(target_sentence.text))

        i, j = target_index, target_index

        while True:
            expanded = False
            if i > 0:
                prev_sentence = sentences[i - 1]
                prev_tokens = tokenizer.tokenize(prev_sentence.text)
                # leaves room for the CLS special token
                if tokens_count + len(prev_tokens) < token_limit:
                    context_sentences.insert(0, prev_sentence)
                    tokens_count += len(prev_tokens)
                    i -= 1
                    expanded = True

            if j < len(sentences) - 1:
                next_sentence = sentences[j + 1]
                next_tokens = tokenizer.tokenize(next_sentence.text)
                # leaves room for the CLS special token
                if tokens_count + len(next_tokens) < token_limit:
                    context_sentences.append(next_sentence)
                    tokens_count += len(next_tokens)
                    j += 1
                    expanded = True

            if not expanded:
                break

        start = context_sentences[0].start
        end = context_sentences[-1].end

        return Span(self.doc, start, end)

    def get_candidates(
        self, filter: t.Optional[t.Dict[str, t.List[str]]] = None
    ) -> t.List[str]:
        """
        Get the list of candidate location IDs for this toponym, with optional filtering.

        Args:
            filter (Optional[Dict[str, List[str]]], optional): Filter to restrict candidate selection.

        Returns:
            List[str]: List of candidate location IDs.
        """
        filter_key = tuple(sorted((k, tuple(v)) for k, v in (filter or {}).items()))
        if filter_key not in self._.candidate_cache:
            candidates = self.doc.geoparser.gazetteer.query_candidates(
                self.text, filter=filter
            )
            self._.candidate_cache[filter_key] = candidates
        return self._.candidate_cache[filter_key]
