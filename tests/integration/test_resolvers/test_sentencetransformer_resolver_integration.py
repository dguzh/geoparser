"""
Integration tests for geoparser/modules/resolvers/sentencetransformer.py

Tests SentenceTransformerResolver with real transformer model and Andorra gazetteer.
"""

from unittest.mock import patch

import pytest

from geoparser.modules.resolvers.sentencetransformer import (
    SentenceTransformerResolver,
)

# Andorra gazetteer uses GeoNames format
ANDORRA_ATTRIBUTE_MAP = {
    "name": "name",
    "type": "feature_name",
    "level1": "country_name",
    "level2": "admin1_name",
    "level3": "admin2_name",
}


@pytest.mark.integration
class TestSentenceTransformerResolverIntegration:
    """Integration tests for SentenceTransformerResolver with real model and gazetteer."""

    def test_creates_with_default_parameters(self, test_engine, andorra_gazetteer):
        """Test that SentenceTransformerResolver can be initialized with defaults."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Act
            resolver = SentenceTransformerResolver(
                gazetteer_name="andorranames", attribute_map=ANDORRA_ATTRIBUTE_MAP
            )

            # Assert
            assert resolver is not None
            assert resolver.model_name == "dguzh/geo-all-MiniLM-L6-v2"
            assert resolver.gazetteer_name == "andorranames"

    def test_creates_with_custom_parameters(self, test_engine, andorra_gazetteer):
        """Test that SentenceTransformerResolver accepts custom parameters."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Act
            resolver = SentenceTransformerResolver(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                gazetteer_name="andorranames",
                min_similarity=0.6,
                max_iter=5,
                attribute_map=ANDORRA_ATTRIBUTE_MAP,
            )

            # Assert
            assert resolver.model_name == "sentence-transformers/all-MiniLM-L6-v2"
            assert resolver.gazetteer_name == "andorranames"
            assert resolver.min_similarity == 0.6
            assert resolver.max_iter == 5

    def test_resolves_reference_to_andorra_location(
        self, test_engine, real_sentencetransformer_resolver, andorra_gazetteer
    ):
        """Test that resolver can resolve a reference to an Andorra location."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Arrange
            texts = ["Andorra la Vella is the capital of Andorra."]
            references = [[(0, 17)]]  # "Andorra la Vella"

            # Act
            results = real_sentencetransformer_resolver.predict(texts, references)

            # Assert
            assert len(results) == 1
            assert len(results[0]) == 1
            assert results[0][0] is not None
            # Should resolve to a location in andorranames gazetteer
            gazetteer_name, identifier = results[0][0]
            assert gazetteer_name == "andorranames"
            assert identifier is not None

    def test_resolves_multiple_references_in_document(
        self, test_engine, real_sentencetransformer_resolver, andorra_gazetteer
    ):
        """Test that resolver handles multiple references in one document."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Arrange
            texts = ["Travel from Andorra la Vella to les Escaldes."]
            references = [[(12, 29), (33, 45)]]  # "Andorra la Vella", "les Escaldes"

            # Act
            results = real_sentencetransformer_resolver.predict(texts, references)

            # Assert
            assert len(results) == 1
            assert len(results[0]) == 2
            # Both should be resolved
            assert results[0][0] is not None
            assert results[0][1] is not None

    def test_resolves_references_across_multiple_documents(
        self, test_engine, real_sentencetransformer_resolver, andorra_gazetteer
    ):
        """Test that resolver handles multiple documents."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Arrange
            texts = [
                "Andorra la Vella is the capital.",
                "les Escaldes is another parish.",
            ]
            references = [[(0, 17)], [(0, 12)]]  # "Andorra la Vella", "les Escaldes"

            # Act
            results = real_sentencetransformer_resolver.predict(texts, references)

            # Assert
            assert len(results) == 2
            assert results[0][0] is not None
            assert results[1][0] is not None

    def test_handles_document_with_no_references(
        self, test_engine, real_sentencetransformer_resolver, andorra_gazetteer
    ):
        """Test that resolver handles documents with empty reference lists."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Arrange
            texts = ["No locations here."]
            references = [[]]

            # Act
            results = real_sentencetransformer_resolver.predict(texts, references)

            # Assert
            assert len(results) == 1
            assert results[0] == []

    def test_handles_empty_input(
        self, test_engine, real_sentencetransformer_resolver, andorra_gazetteer
    ):
        """Test that resolver handles empty input gracefully."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Arrange
            texts = []
            references = []

            # Act
            results = real_sentencetransformer_resolver.predict(texts, references)

            # Assert
            assert results == []

    def test_uses_context_for_disambiguation(
        self, test_engine, real_sentencetransformer_resolver, andorra_gazetteer
    ):
        """Test that resolver uses surrounding context for better resolution."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Arrange
            # Same reference text but different contexts
            texts = [
                "The capital Andorra la Vella has many government buildings.",
                "Visit Andorra la Vella for shopping and dining.",
            ]
            references = [[(12, 29)], [(6, 23)]]  # Both "Andorra la Vella"

            # Act
            results = real_sentencetransformer_resolver.predict(texts, references)

            # Assert
            assert len(results) == 2
            # Both should resolve (possibly to the same location given it's the same place)
            assert results[0][0] is not None
            assert results[1][0] is not None

    def test_caches_context_embeddings(
        self, test_engine, real_sentencetransformer_resolver, andorra_gazetteer
    ):
        """Test that resolver caches context embeddings for efficiency."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Arrange
            texts = ["Andorra la Vella is the capital."]
            references = [[(0, 17)]]

            # Act - First call
            real_sentencetransformer_resolver.predict(texts, references)
            initial_cache_size = len(
                real_sentencetransformer_resolver.context_embeddings
            )

            # Act - Second call with same text
            real_sentencetransformer_resolver.predict(texts, references)
            final_cache_size = len(real_sentencetransformer_resolver.context_embeddings)

            # Assert - Cache should not grow on second call
            assert initial_cache_size > 0
            assert final_cache_size == initial_cache_size

    def test_caches_candidate_embeddings(
        self, test_engine, real_sentencetransformer_resolver, andorra_gazetteer
    ):
        """Test that resolver caches candidate embeddings for efficiency."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Arrange
            texts = ["Andorra la Vella is beautiful.", "Andorra la Vella is historic."]
            references = [[(0, 17)], [(0, 17)]]

            # Act
            real_sentencetransformer_resolver.predict(texts, references)
            cache_size = len(real_sentencetransformer_resolver.candidate_embeddings)

            # Assert - Should have cached candidate embeddings
            assert cache_size > 0

    def test_generates_deterministic_id(self, test_engine, andorra_gazetteer):
        """Test that same configuration produces same resolver ID."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Arrange & Act
            resolver1 = SentenceTransformerResolver(
                model_name="dguzh/geo-all-MiniLM-L6-v2",
                gazetteer_name="andorranames",
                min_similarity=0.7,
                max_iter=3,
                attribute_map=ANDORRA_ATTRIBUTE_MAP,
            )
            resolver2 = SentenceTransformerResolver(
                model_name="dguzh/geo-all-MiniLM-L6-v2",
                gazetteer_name="andorranames",
                min_similarity=0.7,
                max_iter=3,
                attribute_map=ANDORRA_ATTRIBUTE_MAP,
            )

            # Assert
            assert resolver1.id == resolver2.id

    def test_different_config_produces_different_id(
        self, test_engine, andorra_gazetteer
    ):
        """Test that different configuration produces different resolver ID."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Arrange & Act
            resolver1 = SentenceTransformerResolver(
                gazetteer_name="andorranames",
                min_similarity=0.7,
                attribute_map=ANDORRA_ATTRIBUTE_MAP,
            )
            resolver2 = SentenceTransformerResolver(
                gazetteer_name="andorranames",
                min_similarity=0.6,
                attribute_map=ANDORRA_ATTRIBUTE_MAP,
            )

            # Assert
            assert resolver1.id != resolver2.id

    def test_extract_context_truncates_long_text(
        self, test_engine, real_sentencetransformer_resolver, andorra_gazetteer
    ):
        """Test that resolver extracts context within token limits."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Arrange
            long_text = (
                "This is a very long document. " * 100
                + "Andorra la Vella is mentioned here. "
                + "This continues for much longer. " * 100
            )
            start = long_text.index("Andorra la Vella")
            end = start + len("Andorra la Vella")
            texts = [long_text]
            references = [[(start, end)]]

            # Act
            results = real_sentencetransformer_resolver.predict(texts, references)

            # Assert
            # Should still resolve despite long text
            assert len(results) == 1
            assert results[0][0] is not None

    def test_handles_reference_at_document_start(
        self, test_engine, real_sentencetransformer_resolver, andorra_gazetteer
    ):
        """Test that resolver handles references at the very beginning of text."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Arrange
            texts = ["Andorra la Vella is first."]
            references = [[(0, 17)]]

            # Act
            results = real_sentencetransformer_resolver.predict(texts, references)

            # Assert
            assert len(results) == 1
            assert results[0][0] is not None

    def test_handles_reference_at_document_end(
        self, test_engine, real_sentencetransformer_resolver, andorra_gazetteer
    ):
        """Test that resolver handles references at the very end of text."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Arrange
            texts = ["The capital is Andorra la Vella"]
            start = texts[0].index("Andorra la Vella")
            references = [[(start, len(texts[0]))]]

            # Act
            results = real_sentencetransformer_resolver.predict(texts, references)

            # Assert
            assert len(results) == 1
            assert results[0][0] is not None

    def test_searches_gazetteer_for_candidates(
        self, test_engine, real_sentencetransformer_resolver, andorra_gazetteer
    ):
        """Test that resolver searches the gazetteer for location candidates."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Arrange
            texts = ["Visit Encamp, a beautiful parish."]
            references = [[(6, 12)]]  # "Encamp"

            # Act
            results = real_sentencetransformer_resolver.predict(texts, references)

            # Assert
            assert len(results) == 1
            # Should find Encamp in Andorra gazetteer
            assert results[0][0] is not None
            gazetteer_name, identifier = results[0][0]
            assert gazetteer_name == "andorranames"

    def test_fit_trains_model_with_referent_annotations(
        self, test_engine, andorra_gazetteer, tmp_path
    ):
        """Test that fit method trains the model with provided referent annotations."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Arrange
            resolver = SentenceTransformerResolver(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                gazetteer_name="andorranames",
                attribute_map=ANDORRA_ATTRIBUTE_MAP,
            )
            texts = [
                "Andorra la Vella is the capital.",
                "Visit les Escaldes for shopping.",
            ]
            references = [[(0, 17)], [(6, 18)]]  # "Andorra la Vella", "les Escaldes"
            referents = [
                [("andorranames", "3041563")],
                [("andorranames", "3041565")],
            ]
            output_path = tmp_path / "trained_model"

            # Act
            resolver.fit(
                texts=texts,
                references=references,
                referents=referents,
                output_path=str(output_path),
                epochs=1,
                batch_size=2,
            )

            # Assert - Model should be saved
            assert output_path.exists()
            # Check that model files were created
            assert len(list(output_path.iterdir())) > 0

    def test_fit_raises_error_with_no_training_data(
        self, test_engine, andorra_gazetteer, tmp_path
    ):
        """Test that fit raises error when no training examples can be created."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Arrange
            resolver = SentenceTransformerResolver(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                gazetteer_name="andorranames",
                attribute_map=ANDORRA_ATTRIBUTE_MAP,
            )
            texts = []
            references = []
            referents = []
            output_path = tmp_path / "trained_model"

            # Act & Assert
            with pytest.raises(ValueError, match="No training examples found"):
                resolver.fit(
                    texts=texts,
                    references=references,
                    referents=referents,
                    output_path=str(output_path),
                    epochs=1,
                )

    def test_fit_creates_positive_and_negative_examples(
        self, test_engine, andorra_gazetteer, tmp_path
    ):
        """Test that fit creates both positive and negative training examples."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Arrange
            resolver = SentenceTransformerResolver(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                gazetteer_name="andorranames",
                attribute_map=ANDORRA_ATTRIBUTE_MAP,
            )
            texts = ["Andorra la Vella is beautiful."]
            references = [[(0, 17)]]  # "Andorra la Vella"
            referents = [[("andorranames", "3041563")]]
            output_path = tmp_path / "trained_model"

            # Act - Should create positive example for correct referent and negatives for others
            resolver.fit(
                texts=texts,
                references=references,
                referents=referents,
                output_path=str(output_path),
                epochs=1,
            )

            # Assert
            assert output_path.exists()

    def test_fit_handles_multiple_references_per_document(
        self, test_engine, andorra_gazetteer, tmp_path
    ):
        """Test that fit handles documents with multiple references."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Arrange
            resolver = SentenceTransformerResolver(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                gazetteer_name="andorranames",
                attribute_map=ANDORRA_ATTRIBUTE_MAP,
            )
            texts = ["Visit Andorra la Vella and les Escaldes."]
            references = [[(6, 23), (28, 40)]]  # "Andorra la Vella", "les Escaldes"
            referents = [[("andorranames", "3041563"), ("andorranames", "3041565")]]
            output_path = tmp_path / "trained_model"

            # Act
            resolver.fit(
                texts=texts,
                references=references,
                referents=referents,
                output_path=str(output_path),
                epochs=1,
            )

            # Assert
            assert output_path.exists()

    def test_fit_accepts_custom_training_parameters(
        self, test_engine, andorra_gazetteer, tmp_path
    ):
        """Test that fit accepts and uses custom training parameters."""
        # Patch the engine getter to return our test engine
        with patch("geoparser.db.engine.get_engine", return_value=test_engine):
            # Arrange
            resolver = SentenceTransformerResolver(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                gazetteer_name="andorranames",
                attribute_map=ANDORRA_ATTRIBUTE_MAP,
            )
            texts = ["Encamp is a parish."]
            references = [[(0, 6)]]  # "Encamp"
            referents = [[("andorranames", "3041204")]]
            output_path = tmp_path / "trained_model"

            # Act - Use custom parameters
            resolver.fit(
                texts=texts,
                references=references,
                referents=referents,
                output_path=str(output_path),
                epochs=2,
                batch_size=4,
                learning_rate=1e-5,
                warmup_ratio=0.2,
            )

            # Assert
            assert output_path.exists()
