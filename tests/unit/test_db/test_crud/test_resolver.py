"""
Unit tests for geoparser/db/crud/resolver.py

Tests the ResolverRepository class with custom query methods.
"""

import pytest
from sqlmodel import Session

from geoparser.db.crud import ResolverRepository


@pytest.mark.unit
class TestResolverRepositoryGetByNameAndConfig:
    """Test the get_by_name_and_config method of ResolverRepository."""

    def test_returns_resolver_for_matching_name_and_config(
        self, test_session: Session, resolver_factory
    ):
        """Test that get_by_name_and_config returns resolver when both match."""
        # Arrange
        config = {"model": "all-MiniLM-L6-v2", "top_k": 5}
        resolver = resolver_factory(name="SentenceTransformerResolver", config=config)

        # Act
        found_resolver = ResolverRepository.get_by_name_and_config(
            test_session, "SentenceTransformerResolver", config
        )

        # Assert
        assert found_resolver is not None
        assert found_resolver.id == resolver.id
        assert found_resolver.name == "SentenceTransformerResolver"
        assert found_resolver.config == config

    def test_returns_none_for_non_matching_name(
        self, test_session: Session, resolver_factory
    ):
        """Test that get_by_name_and_config returns None when name doesn't match."""
        # Arrange
        config = {"model": "all-MiniLM-L6-v2"}
        resolver = resolver_factory(name="SentenceTransformerResolver", config=config)

        # Act
        found_resolver = ResolverRepository.get_by_name_and_config(
            test_session, "ManualResolver", config
        )

        # Assert
        assert found_resolver is None

    def test_returns_none_for_non_matching_config(
        self, test_session: Session, resolver_factory
    ):
        """Test that get_by_name_and_config returns None when config doesn't match."""
        # Arrange
        config1 = {"model": "all-MiniLM-L6-v2"}
        config2 = {"model": "all-mpnet-base-v2"}
        resolver = resolver_factory(name="SentenceTransformerResolver", config=config1)

        # Act
        found_resolver = ResolverRepository.get_by_name_and_config(
            test_session, "SentenceTransformerResolver", config2
        )

        # Assert
        assert found_resolver is None

    def test_distinguishes_between_same_name_different_configs(
        self, test_session: Session, resolver_factory
    ):
        """Test that method can distinguish resolvers with same name but different configs."""
        # Arrange
        config1 = {"model": "all-MiniLM-L6-v2"}
        config2 = {"model": "all-mpnet-base-v2"}

        res1 = resolver_factory(name="SentenceTransformerResolver", config=config1)
        res2 = resolver_factory(name="SentenceTransformerResolver", config=config2)

        # Act
        found_res1 = ResolverRepository.get_by_name_and_config(
            test_session, "SentenceTransformerResolver", config1
        )
        found_res2 = ResolverRepository.get_by_name_and_config(
            test_session, "SentenceTransformerResolver", config2
        )

        # Assert
        assert found_res1 is not None
        assert found_res2 is not None
        assert found_res1.id == res1.id
        assert found_res2.id == res2.id
        assert found_res1.id != found_res2.id
