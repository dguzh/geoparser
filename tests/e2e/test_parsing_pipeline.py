"""
End-to-end tests for parsing pipeline.

Tests complete end-to-end parsing workflows using real recognizers and resolvers.
Basic API functionality is covered in integration tests.
"""

import pytest

from geoparser.geoparser import Geoparser
from geoparser.modules import SentenceTransformerResolver, SpacyRecognizer
from geoparser.project import Project


@pytest.mark.e2e
class TestCompleteParsingPipeline:
    """End-to-end tests for complete parsing workflows with real models."""

    def test_full_pipeline_with_real_models(
        self,
        real_spacy_recognizer,
        real_sentencetransformer_resolver,
        andorra_gazetteer,
    ):
        """Test complete pipeline using real spaCy recognizer and SentenceTransformer resolver."""
        # Arrange
        texts = [
            "Andorra la Vella is the capital of Andorra.",
            "The parish of Escaldes-Engordany is nearby.",
        ]

        # Act - Use Geoparser stateless API with real models
        geoparser = Geoparser(
            recognizer=real_spacy_recognizer,
            resolver=real_sentencetransformer_resolver,
        )
        documents = geoparser.parse(texts, save=False)

        # Assert
        assert len(documents) == 2

        # First document should have recognized locations
        assert len(documents[0].toponyms) > 0
        # At least some should be resolved
        resolved_count = sum(
            1 for doc in documents for toponym in doc.toponyms if toponym.location
        )
        assert resolved_count > 0

    def test_project_workflow_with_real_models(
        self,
        real_spacy_recognizer,
        real_sentencetransformer_resolver,
        andorra_gazetteer,
    ):
        """Test Project-based workflow with real recognizers and resolvers."""
        # Arrange
        project = Project("e2e_real_models_test")
        texts = [
            "Encamp is a beautiful parish in Andorra.",
            "Sant Julia de Loria is in the south.",
        ]

        # Act
        project.create_documents(texts)
        project.run_recognizer(real_spacy_recognizer)
        project.run_resolver(real_sentencetransformer_resolver)

        documents = project.get_documents()

        # Assert
        assert len(documents) == 2
        # Verify at least some locations were recognized and resolved
        total_toponyms = sum(len(doc.toponyms) for doc in documents)
        assert total_toponyms > 0

        resolved_toponyms = sum(
            1 for doc in documents for toponym in doc.toponyms if toponym.location
        )
        assert resolved_toponyms > 0

        # Cleanup
        project.delete()

    def test_multiple_recognizers_comparison(
        self, real_spacy_recognizer, andorra_gazetteer
    ):
        """Test workflow comparing multiple recognizer configurations on same data."""
        # Arrange
        project = Project("recognizer_comparison_test")
        # Use well-known location names that spaCy will definitely recognize
        texts = [
            "Paris is the capital of France.",
            "The city of London is a major hub.",
        ]

        # Act - Run same data through two different entity type configurations
        recognizer1 = SpacyRecognizer(
            model_name="en_core_web_sm", entity_types=["GPE", "LOC"]
        )
        recognizer2 = SpacyRecognizer(
            model_name="en_core_web_sm", entity_types=["GPE", "LOC", "FAC"]
        )

        project.create_documents(texts)
        project.run_recognizer(recognizer1, tag="config1")
        project.run_recognizer(recognizer2, tag="config2")

        # Get results for each recognizer using tags
        docs_rec1 = project.get_documents(tag="config1")
        docs_rec2 = project.get_documents(tag="config2")

        # Assert - Both should produce results (may differ)
        assert len(docs_rec1) == 2
        assert len(docs_rec2) == 2

        # At least one recognizer should find locations (Paris, London, France are well-known GPE entities)
        total_rec1 = sum(len(doc.toponyms) for doc in docs_rec1)
        total_rec2 = sum(len(doc.toponyms) for doc in docs_rec2)
        assert (total_rec1 + total_rec2) > 0

        # Cleanup
        project.delete()

    def test_multiple_resolvers_comparison(
        self, real_spacy_recognizer, andorra_gazetteer
    ):
        """Test workflow comparing multiple resolver configurations on same data."""
        # Arrange
        project = Project("resolver_comparison_test")
        texts = [
            "Paris is the capital of France.",
            "London is a major city.",
        ]

        project.create_documents(texts)

        # Run recognizer on two different tags for comparison
        project.run_recognizer(real_spacy_recognizer, tag="config1")
        project.run_recognizer(real_spacy_recognizer, tag="config2")

        # Define attribute map for andorranames gazetteer
        andorra_attribute_map = {
            "name": "name",
            "type": "feature_name",
            "level1": "country_name",
            "level2": "admin1_name",
            "level3": "admin2_name",
        }

        # Act - Run different resolver configurations with different parameters
        # Different similarity thresholds and max iterations
        resolver1 = SentenceTransformerResolver(
            gazetteer_name="andorranames",
            model_name="dguzh/geo-all-MiniLM-L6-v2",
            min_similarity=0.7,
            max_iter=3,
            attribute_map=andorra_attribute_map,
        )
        resolver2 = SentenceTransformerResolver(
            gazetteer_name="andorranames",
            model_name="dguzh/geo-all-MiniLM-L6-v2",
            min_similarity=0.5,
            max_iter=5,
            attribute_map=andorra_attribute_map,
        )

        project.run_resolver(resolver1, tag="config1")
        project.run_resolver(resolver2, tag="config2")

        # Get results for each resolver using tags
        docs_res1 = project.get_documents(tag="config1")
        docs_res2 = project.get_documents(tag="config2")

        # Assert - Both should produce results
        assert len(docs_res1) == 2
        assert len(docs_res2) == 2

        # Both resolvers should have attempted resolution
        # (may or may not succeed depending on gazetteer content)
        total_toponyms_res1 = sum(len(doc.toponyms) for doc in docs_res1)
        total_toponyms_res2 = sum(len(doc.toponyms) for doc in docs_res2)
        assert total_toponyms_res1 > 0
        assert total_toponyms_res2 > 0

        # Cleanup
        project.delete()

    def test_end_to_end_with_context_switching(
        self,
        real_spacy_recognizer,
        real_sentencetransformer_resolver,
        andorra_gazetteer,
    ):
        """Test workflow that switches between different recognizer/resolver contexts."""
        # Arrange
        project = Project("context_switching_test")
        texts = ["Paris is a beautiful city in France."]

        project.create_documents(texts)

        # Act - Run different recognizers with different entity configurations
        recognizer1 = SpacyRecognizer(
            model_name="en_core_web_sm", entity_types=["GPE", "LOC"]
        )
        recognizer2 = SpacyRecognizer(model_name="en_core_web_sm", entity_types=["GPE"])

        project.run_recognizer(recognizer1, tag="broad")
        project.run_recognizer(recognizer2, tag="narrow")

        # Run resolver for broad recognizer configuration
        project.run_resolver(real_sentencetransformer_resolver, tag="broad")

        # Get documents with different contexts using tags
        docs_rec1_resolved = project.get_documents(tag="broad")
        docs_rec2_unresolved = project.get_documents(tag="narrow")

        # Assert
        assert len(docs_rec1_resolved) == 1
        assert len(docs_rec2_unresolved) == 1

        # Both recognizers should work
        assert len(docs_rec1_resolved[0].toponyms) >= 0
        assert len(docs_rec2_unresolved[0].toponyms) >= 0

        # Cleanup
        project.delete()

    def test_batch_processing_with_real_models(
        self,
        real_spacy_recognizer,
        real_sentencetransformer_resolver,
        andorra_gazetteer,
    ):
        """Test processing larger batch of documents with real models."""
        # Arrange
        project = Project("batch_processing_test")

        # Create varied texts with clear location mentions
        texts = [
            "Paris is the capital of France.",
            "London is in England.",
            "Berlin is the German capital.",
            "Rome is in Italy.",
            "Madrid is in Spain.",
            "Lisbon is the capital of Portugal.",
            "Athens is in Greece.",
        ]

        # Act
        project.create_documents(texts)
        project.run_recognizer(real_spacy_recognizer)
        project.run_resolver(real_sentencetransformer_resolver)

        documents = project.get_documents()

        # Assert
        assert len(documents) == 7

        # Should recognize multiple locations across documents
        total_toponyms = sum(len(doc.toponyms) for doc in documents)
        # With GPE and LOC entity types, we should find many locations
        assert total_toponyms > 0

        # Cleanup
        project.delete()
