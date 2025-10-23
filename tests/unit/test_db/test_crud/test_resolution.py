"""
Unit tests for geoparser/db/crud/resolution.py

Tests the ResolutionRepository class with custom query methods.
"""

import pytest
from sqlmodel import Session

from geoparser.db.crud import ResolutionRepository
from geoparser.db.models import ResolutionCreate


@pytest.mark.unit
class TestResolutionRepositoryGetByReference:
    """Test the get_by_reference method of ResolutionRepository."""

    def test_returns_resolutions_for_reference(
        self,
        test_session: Session,
        reference_factory,
        resolver_factory,
    ):
        """Test that get_by_reference returns all resolutions for a reference."""
        # Arrange
        reference = reference_factory()
        resolver1 = resolver_factory(id="res1")
        resolver2 = resolver_factory(id="res2")

        ResolutionRepository.create(
            test_session,
            ResolutionCreate(reference_id=reference.id, resolver_id="res1"),
        )
        ResolutionRepository.create(
            test_session,
            ResolutionCreate(reference_id=reference.id, resolver_id="res2"),
        )

        # Act
        resolutions = ResolutionRepository.get_by_reference(test_session, reference.id)

        # Assert
        assert len(resolutions) == 2
        resolver_ids = [r.resolver_id for r in resolutions]
        assert "res1" in resolver_ids
        assert "res2" in resolver_ids

    def test_returns_empty_list_for_reference_without_resolutions(
        self, test_session: Session, reference_factory
    ):
        """Test that get_by_reference returns empty list for reference without resolutions."""
        # Arrange
        reference = reference_factory()

        # Act
        resolutions = ResolutionRepository.get_by_reference(test_session, reference.id)

        # Assert
        assert resolutions == []


@pytest.mark.unit
class TestResolutionRepositoryGetByResolver:
    """Test the get_by_resolver method of ResolutionRepository."""

    def test_returns_resolutions_for_resolver(
        self,
        test_session: Session,
        reference_factory,
        resolver_factory,
    ):
        """Test that get_by_resolver returns all resolutions for a resolver."""
        # Arrange
        resolver = resolver_factory(id="test_res")
        ref1 = reference_factory()
        ref2 = reference_factory()

        ResolutionRepository.create(
            test_session,
            ResolutionCreate(reference_id=ref1.id, resolver_id="test_res"),
        )
        ResolutionRepository.create(
            test_session,
            ResolutionCreate(reference_id=ref2.id, resolver_id="test_res"),
        )

        # Act
        resolutions = ResolutionRepository.get_by_resolver(test_session, "test_res")

        # Assert
        assert len(resolutions) == 2
        reference_ids = [r.reference_id for r in resolutions]
        assert ref1.id in reference_ids
        assert ref2.id in reference_ids

    def test_returns_empty_list_for_resolver_without_resolutions(
        self, test_session: Session, resolver_factory
    ):
        """Test that get_by_resolver returns empty list for resolver without resolutions."""
        # Arrange
        resolver = resolver_factory(id="test_res")

        # Act
        resolutions = ResolutionRepository.get_by_resolver(test_session, "test_res")

        # Assert
        assert resolutions == []


@pytest.mark.unit
class TestResolutionRepositoryGetByReferenceAndResolver:
    """Test the get_by_reference_and_resolver method of ResolutionRepository."""

    def test_returns_resolution_for_matching_pair(
        self,
        test_session: Session,
        reference_factory,
        resolver_factory,
    ):
        """Test that get_by_reference_and_resolver returns resolution for matching pair."""
        # Arrange
        reference = reference_factory()
        resolver = resolver_factory(id="test_res")

        created_resolution = ResolutionRepository.create(
            test_session,
            ResolutionCreate(reference_id=reference.id, resolver_id="test_res"),
        )

        # Act
        resolution = ResolutionRepository.get_by_reference_and_resolver(
            test_session, reference.id, "test_res"
        )

        # Assert
        assert resolution is not None
        assert resolution.id == created_resolution.id
        assert resolution.reference_id == reference.id
        assert resolution.resolver_id == "test_res"

    def test_returns_none_for_non_matching_pair(
        self,
        test_session: Session,
        reference_factory,
        resolver_factory,
    ):
        """Test that get_by_reference_and_resolver returns None for non-matching pair."""
        # Arrange
        reference = reference_factory()
        resolver = resolver_factory(id="test_res")

        # Act
        resolution = ResolutionRepository.get_by_reference_and_resolver(
            test_session, reference.id, "test_res"
        )

        # Assert
        assert resolution is None


@pytest.mark.unit
class TestResolutionRepositoryGetUnprocessedReferences:
    """Test the get_unprocessed_references method of ResolutionRepository."""

    def test_returns_references_not_processed_by_resolver(
        self,
        test_session: Session,
        project_factory,
        document_factory,
        reference_factory,
        resolver_factory,
    ):
        """Test that get_unprocessed_references returns references not yet processed."""
        # Arrange
        project = project_factory()
        resolver = resolver_factory(id="test_res")
        document = document_factory(project_id=project.id)

        # Create three references
        ref1 = reference_factory(document_id=document.id)
        ref2 = reference_factory(document_id=document.id)
        ref3 = reference_factory(document_id=document.id)

        # Mark ref1 as processed
        ResolutionRepository.create(
            test_session,
            ResolutionCreate(reference_id=ref1.id, resolver_id="test_res"),
        )

        # Act
        unprocessed = ResolutionRepository.get_unprocessed_references(
            test_session, project.id, "test_res"
        )

        # Assert
        assert len(unprocessed) == 2
        unprocessed_ids = [r.id for r in unprocessed]
        assert ref1.id not in unprocessed_ids
        assert ref2.id in unprocessed_ids
        assert ref3.id in unprocessed_ids

    def test_returns_all_references_when_none_processed(
        self,
        test_session: Session,
        project_factory,
        document_factory,
        reference_factory,
        resolver_factory,
    ):
        """Test that get_unprocessed_references returns all references when none processed."""
        # Arrange
        project = project_factory()
        resolver = resolver_factory(id="test_res")
        document = document_factory(project_id=project.id)

        ref1 = reference_factory(document_id=document.id)
        ref2 = reference_factory(document_id=document.id)

        # Act
        unprocessed = ResolutionRepository.get_unprocessed_references(
            test_session, project.id, "test_res"
        )

        # Assert
        assert len(unprocessed) == 2

    def test_returns_empty_list_when_all_processed(
        self,
        test_session: Session,
        project_factory,
        document_factory,
        reference_factory,
        resolver_factory,
    ):
        """Test that get_unprocessed_references returns empty list when all processed."""
        # Arrange
        project = project_factory()
        resolver = resolver_factory(id="test_res")
        document = document_factory(project_id=project.id)

        ref1 = reference_factory(document_id=document.id)
        ref2 = reference_factory(document_id=document.id)

        # Mark both as processed
        ResolutionRepository.create(
            test_session,
            ResolutionCreate(reference_id=ref1.id, resolver_id="test_res"),
        )
        ResolutionRepository.create(
            test_session,
            ResolutionCreate(reference_id=ref2.id, resolver_id="test_res"),
        )

        # Act
        unprocessed = ResolutionRepository.get_unprocessed_references(
            test_session, project.id, "test_res"
        )

        # Assert
        assert unprocessed == []

    def test_filters_by_project(
        self,
        test_session: Session,
        project_factory,
        document_factory,
        reference_factory,
        resolver_factory,
    ):
        """Test that get_unprocessed_references only returns references from specified project."""
        # Arrange
        project1 = project_factory()
        project2 = project_factory()
        resolver = resolver_factory(id="test_res")

        # References in project1
        doc1_proj1 = document_factory(project_id=project1.id)
        ref1_proj1 = reference_factory(document_id=doc1_proj1.id)

        # References in project2
        doc1_proj2 = document_factory(project_id=project2.id)
        ref1_proj2 = reference_factory(document_id=doc1_proj2.id)

        # Act - Get unprocessed from project1
        unprocessed = ResolutionRepository.get_unprocessed_references(
            test_session, project1.id, "test_res"
        )

        # Assert - Should only contain ref from project1
        assert len(unprocessed) == 1
        assert unprocessed[0].id == ref1_proj1.id
