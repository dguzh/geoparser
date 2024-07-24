from spacy.tokens import Span


class GeoSpan(Span):

    def __eq__(self, other):
        return (
            self.doc.text == other.doc.text
            and self.start == other.start
            and self.end == other.end
        )

    @property
    def location(self):
        return self.doc.geoparser.gazetteer.query_location_info(self._.loc_id)[0]

    @property
    def score(self):
        return self._.loc_score

    @property
    def candidates(self):
        return self.doc.geoparser.gazetteer.query_candidates(
            self.text,
            self.doc.geoparser.country_filter,
            self.doc.geoparser.feature_filter,
        )

    @property
    def context(self):
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
                if tokens_count + len(prev_tokens) < token_limit:
                    context_sentences.insert(0, prev_sentence)
                    tokens_count += len(prev_tokens)
                    i -= 1
                    expanded = True

            if j < len(sentences) - 1:
                next_sentence = sentences[j + 1]
                next_tokens = tokenizer.tokenize(next_sentence.text)
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
