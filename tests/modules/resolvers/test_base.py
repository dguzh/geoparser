import uuid
from unittest.mock import MagicMock, patch

import pytest

from geoparser.db.crud import (
    FeatureRepository,
    ReferenceRepository,
    ReferentRepository,
    ResolutionRepository,
    ResolverRepository,
)
from geoparser.modules.resolvers.base import Resolver


def test_resolver_initialization():
    """Test basic initialization of Resolver."""

    class TestResolver(Resolver):
        NAME = "test_resolver"

        def predict_referents(self, references):
            return [("gazetteer", "id1") for _ in references]

    with patch.object(TestResolver, "_load", return_value=uuid.uuid4()):
        resolver = TestResolver(param1="value1")
        assert resolver.name == "test_resolver"
        assert resolver.config == {"param1": "value1"}
        assert resolver.id is not None


def test_resolver_abstract():
    """Test that Resolver is abstract and requires implementation."""

    # Create a concrete subclass that doesn't implement required methods
    class InvalidResolver(Resolver):
        NAME = "invalid_resolver"

    # Should raise TypeError when instantiated due to abstract methods
    with pytest.raises(TypeError, match="predict_referents"):
        InvalidResolver()


def test_resolver_load_existing(test_db):
    """Test _load with an existing resolver."""

    class TestResolver(Resolver):
        NAME = "test_resolver"

        def predict_referents(self, references):
            return [("gazetteer", "id1") for _ in references]

    # Create existing resolver in database
    existing_resolver_id = uuid.uuid4()
    with patch("geoparser.modules.resolvers.base.Session") as mock_session:
        mock_session.return_value.__enter__.return_value = test_db
        mock_session.return_value.__exit__.return_value = None

        mock_db_resolver = MagicMock()
        mock_db_resolver.id = existing_resolver_id

        with patch.object(
            ResolverRepository, "get_by_name_and_config", return_value=mock_db_resolver
        ):
            resolver = TestResolver(param="value")
            assert resolver.id == existing_resolver_id


def test_resolver_load_new(test_db):
    """Test _load with a new resolver."""

    class TestResolver(Resolver):
        NAME = "test_resolver"

        def predict_referents(self, references):
            return [("gazetteer", "id1") for _ in references]

    new_resolver_id = uuid.uuid4()
    with patch("geoparser.modules.resolvers.base.Session") as mock_session:
        mock_session.return_value.__enter__.return_value = test_db
        mock_session.return_value.__exit__.return_value = None

        mock_new_resolver = MagicMock()
        mock_new_resolver.id = new_resolver_id

        with patch.object(
            ResolverRepository, "get_by_name_and_config", return_value=None
        ):
            with patch.object(
                ResolverRepository, "create", return_value=mock_new_resolver
            ) as mock_create:
                resolver = TestResolver(param="value")
                assert resolver.id == new_resolver_id
                mock_create.assert_called_once()


def test_resolver_run_no_documents():
    """Test run with empty document list."""

    class TestResolver(Resolver):
        NAME = "test_resolver"

        def predict_referents(self, references):
            return [("gazetteer", "id1") for _ in references]

    with patch.object(TestResolver, "_load", return_value=uuid.uuid4()):
        resolver = TestResolver()
        resolver.run([])  # Should return early without error


def test_resolver_run_no_references(test_db, test_documents):
    """Test run with documents that have no references."""

    class TestResolver(Resolver):
        NAME = "test_resolver"

        def predict_referents(self, references):
            return [("gazetteer", "id1") for _ in references]

    resolver_id = uuid.uuid4()
    with patch.object(TestResolver, "_load", return_value=resolver_id):
        resolver = TestResolver()

        with patch("geoparser.modules.resolvers.base.Session") as mock_session:
            mock_session.return_value.__enter__.return_value = test_db
            mock_session.return_value.__exit__.return_value = None

            with patch.object(ReferenceRepository, "get_by_document", return_value=[]):
                with patch.object(resolver, "predict_referents") as mock_predict:
                    resolver.run(test_documents)
                    mock_predict.assert_not_called()


def test_resolver_run_already_processed(test_db, test_documents, test_references):
    """Test run with references already processed by this resolver."""

    class TestResolver(Resolver):
        NAME = "test_resolver"

        def predict_referents(self, references):
            return [("gazetteer", "id1") for _ in references]

    resolver_id = uuid.uuid4()
    with patch.object(TestResolver, "_load", return_value=resolver_id):
        resolver = TestResolver()

        with patch("geoparser.modules.resolvers.base.Session") as mock_session:
            mock_session.return_value.__enter__.return_value = test_db
            mock_session.return_value.__exit__.return_value = None

            with patch.object(
                ReferenceRepository, "get_by_document", return_value=test_references
            ):
                with patch.object(
                    resolver, "_filter_unprocessed_references", return_value=[]
                ):
                    with patch.object(resolver, "predict_referents") as mock_predict:
                        resolver.run(test_documents)
                        mock_predict.assert_not_called()


def test_resolver_run_success(test_db, test_documents, test_references):
    """Test successful run with unprocessed references."""

    class TestResolver(Resolver):
        NAME = "test_resolver"

        def predict_referents(self, references):
            return [("test_gazetteer", "loc1") for _ in references]

    resolver_id = uuid.uuid4()
    with patch.object(TestResolver, "_load", return_value=resolver_id):
        resolver = TestResolver()

        with patch("geoparser.modules.resolvers.base.Session") as mock_session:
            mock_session.return_value.__enter__.return_value = test_db
            mock_session.return_value.__exit__.return_value = None

            with patch.object(
                ReferenceRepository, "get_by_document", return_value=test_references
            ):
                with patch.object(
                    resolver,
                    "_filter_unprocessed_references",
                    return_value=test_references,
                ):
                    with patch.object(
                        resolver, "_record_referent_predictions"
                    ) as mock_record:
                        resolver.run(test_documents)
                        mock_record.assert_called_once_with(
                            test_db,
                            test_references,
                            [("test_gazetteer", "loc1") for _ in test_references],
                            resolver_id,
                        )


def test_record_referent_predictions(test_db, test_references):
    """Test _record_referent_predictions processing."""

    class TestResolver(Resolver):
        NAME = "test_resolver"

        def predict_referents(self, references):
            return [("gazetteer", "id1") for _ in references]

    resolver_id = uuid.uuid4()
    with patch.object(TestResolver, "_load", return_value=resolver_id):
        resolver = TestResolver()

        predicted_referents = [("test_gazetteer", "loc1") for _ in test_references]

        with patch.object(resolver, "_create_referent_record") as mock_create_ref:
            with patch.object(resolver, "_create_resolution_record") as mock_create_res:
                resolver._record_referent_predictions(
                    test_db, test_references, predicted_referents, resolver_id
                )

                # Should create referent for each reference
                for ref in test_references:
                    mock_create_ref.assert_any_call(
                        test_db, ref.id, "test_gazetteer", "loc1", resolver_id
                    )
                    mock_create_res.assert_any_call(test_db, ref.id, resolver_id)


def test_create_referent_record(test_db, test_reference):
    """Test _create_referent_record creates referent with resolver ID."""

    class TestResolver(Resolver):
        NAME = "test_resolver"

        def predict_referents(self, references):
            return [("gazetteer", "id1") for _ in references]

    resolver_id = uuid.uuid4()
    with patch.object(TestResolver, "_load", return_value=resolver_id):
        resolver = TestResolver()

        # Mock feature lookup
        mock_feature = MagicMock()
        mock_feature.id = 12345

        with patch.object(
            FeatureRepository,
            "get_by_gazetteer_and_identifier",
            return_value=mock_feature,
        ):
            with patch.object(ReferentRepository, "create") as mock_create:
                resolver._create_referent_record(
                    test_db, test_reference.id, "test_gazetteer", "loc1", resolver_id
                )

                mock_create.assert_called_once()
                created_args = mock_create.call_args[0][1]  # Get ReferentCreate object
                assert created_args.reference_id == test_reference.id
                assert created_args.feature_id == 12345
                assert created_args.resolver_id == resolver_id


def test_create_resolution_record(test_db, test_reference):
    """Test _create_resolution_record creates resolution record."""

    class TestResolver(Resolver):
        NAME = "test_resolver"

        def predict_referents(self, references):
            return [("gazetteer", "id1") for _ in references]

    resolver_id = uuid.uuid4()
    with patch.object(TestResolver, "_load", return_value=resolver_id):
        resolver = TestResolver()

        with patch.object(ResolutionRepository, "create") as mock_create:
            resolver._create_resolution_record(test_db, test_reference.id, resolver_id)

            mock_create.assert_called_once()
            created_args = mock_create.call_args[0][1]  # Get ResolutionCreate object
            assert created_args.reference_id == test_reference.id
            assert created_args.resolver_id == resolver_id


def test_filter_unprocessed_references(test_db, test_references):
    """Test _filter_unprocessed_references filters correctly."""

    class TestResolver(Resolver):
        NAME = "test_resolver"

        def predict_referents(self, references):
            return [("gazetteer", "id1") for _ in references]

    resolver_id = uuid.uuid4()
    with patch.object(TestResolver, "_load", return_value=resolver_id):
        resolver = TestResolver()

        # Mock that first reference is already processed
        def mock_get_by_reference_and_resolver(db, ref_id, res_id):
            if ref_id == test_references[0].id:
                return MagicMock()  # Existing resolution
            return None  # No resolution

        with patch.object(
            ResolutionRepository,
            "get_by_reference_and_resolver",
            side_effect=mock_get_by_reference_and_resolver,
        ):
            result = resolver._filter_unprocessed_references(test_db, test_references)
            assert len(result) == len(test_references) - 1
            assert test_references[0] not in result


def test_predict_referents_implementation():
    """Test a valid implementation of predict_referents."""

    class ValidResolver(Resolver):
        NAME = "valid_resolver"

        def predict_referents(self, references):
            return [("test_gazetteer", "loc1") for _ in references]

    with patch.object(ValidResolver, "_load", return_value=uuid.uuid4()):
        resolver = ValidResolver()

        # Create mock Reference objects with Document relationships
        ref1 = MagicMock()
        ref1.start = 0
        ref1.end = 5
        ref1.text = "Test"
        ref1.document.text = "Test document 1"

        ref2 = MagicMock()
        ref2.start = 10
        ref2.end = 15
        ref2.text = "docum"
        ref2.document.text = "Test document 2"

        references = [ref1, ref2]

        result = resolver.predict_referents(references)
        assert len(result) == 2
        assert result[0] == ("test_gazetteer", "loc1")
        assert result[1] == ("test_gazetteer", "loc1")
