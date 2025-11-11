"""
Unit tests for geoparser/gazetteer/installer/installer.py

Tests the GazetteerInstaller orchestrator class.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from geoparser.gazetteer.installer.installer import GazetteerInstaller


@pytest.mark.unit
class TestGazetteerInstallerInit:
    """Test GazetteerInstaller initialization."""

    def test_creates_instance(self):
        """Test creating an installer instance."""
        # Act
        installer = GazetteerInstaller()

        # Assert
        assert installer is not None
        assert hasattr(installer, "dependency_resolver")


@pytest.mark.unit
class TestGazetteerInstallerCreateDownloadsDirectory:
    """Test _create_downloads_directory method."""

    @patch("geoparser.gazetteer.installer.installer.user_data_dir")
    def test_creates_directory(self, mock_user_data_dir):
        """Test that downloads directory is created."""
        # Arrange
        installer = GazetteerInstaller()

        with tempfile.TemporaryDirectory() as temp_dir:
            mock_user_data_dir.return_value = temp_dir

            # Act
            result_dir = installer._create_downloads_directory("test_gaz")

            # Assert
            assert result_dir.exists()
            assert result_dir.name == "test_gaz"
            assert "downloads" in str(result_dir)

    @patch("geoparser.gazetteer.installer.installer.user_data_dir")
    def test_returns_path_object(self, mock_user_data_dir):
        """Test that method returns a Path object."""
        # Arrange
        installer = GazetteerInstaller()

        with tempfile.TemporaryDirectory() as temp_dir:
            mock_user_data_dir.return_value = temp_dir

            # Act
            result_dir = installer._create_downloads_directory("test_gaz")

            # Assert
            assert isinstance(result_dir, Path)


@pytest.mark.unit
class TestGazetteerInstallerEnsureGazetteerRecord:
    """Test _ensure_gazetteer_record method."""

    @patch("geoparser.gazetteer.installer.installer.GazetteerRepository")
    def test_creates_new_gazetteer_when_doesnt_exist(self, mock_repo):
        """Test creating new gazetteer record when it doesn't exist."""
        # Arrange
        mock_repo.get_by_name.return_value = None  # Doesn't exist

        installer = GazetteerInstaller()

        # Act
        installer._ensure_gazetteer_record("test_gaz")

        # Assert
        mock_repo.create.assert_called_once()
        create_call_args = mock_repo.create.call_args[0]
        assert create_call_args[1].name == "test_gaz"

    @patch("geoparser.gazetteer.installer.installer.GazetteerRepository")
    def test_reuses_existing_gazetteer_when_exists(self, mock_repo):
        """Test reusing existing gazetteer record."""
        # Arrange

        mock_existing = Mock()
        mock_repo.get_by_name.return_value = mock_existing  # Already exists

        installer = GazetteerInstaller()

        # Act
        installer._ensure_gazetteer_record("test_gaz")

        # Assert
        mock_repo.create.assert_not_called()


@pytest.mark.unit
class TestGazetteerInstallerCreatePipeline:
    """Test _create_pipeline method."""

    @patch("geoparser.gazetteer.installer.installer.RegistrationStage")
    @patch("geoparser.gazetteer.installer.installer.IndexingStage")
    @patch("geoparser.gazetteer.installer.installer.TransformationStage")
    @patch("geoparser.gazetteer.installer.installer.IngestionStage")
    @patch("geoparser.gazetteer.installer.installer.SchemaStage")
    @patch("geoparser.gazetteer.installer.installer.AcquisitionStage")
    def test_creates_all_pipeline_stages(
        self,
        mock_acquisition,
        mock_schema,
        mock_ingestion,
        mock_transformation,
        mock_indexing,
        mock_registration,
    ):
        """Test that all pipeline stages are created."""
        # Arrange
        installer = GazetteerInstaller()
        downloads_dir = Path("/tmp/downloads")

        # Act
        pipeline = installer._create_pipeline("test_gaz", downloads_dir, 10000)

        # Assert
        assert len(pipeline) == 6
        mock_acquisition.assert_called_once_with(downloads_dir)
        mock_schema.assert_called_once()
        mock_ingestion.assert_called_once_with(10000)
        mock_transformation.assert_called_once()
        mock_indexing.assert_called_once()
        mock_registration.assert_called_once_with("test_gaz")

    @patch("geoparser.gazetteer.installer.installer.RegistrationStage")
    @patch("geoparser.gazetteer.installer.installer.IndexingStage")
    @patch("geoparser.gazetteer.installer.installer.TransformationStage")
    @patch("geoparser.gazetteer.installer.installer.IngestionStage")
    @patch("geoparser.gazetteer.installer.installer.SchemaStage")
    @patch("geoparser.gazetteer.installer.installer.AcquisitionStage")
    def test_pipeline_stages_in_correct_order(
        self,
        mock_acquisition,
        mock_schema,
        mock_ingestion,
        mock_transformation,
        mock_indexing,
        mock_registration,
    ):
        """Test that pipeline stages are in correct order."""
        # Arrange
        installer = GazetteerInstaller()
        downloads_dir = Path("/tmp/downloads")

        # Act
        pipeline = installer._create_pipeline("test_gaz", downloads_dir, 10000)

        # Assert
        # Pipeline order: Acquisition, Schema, Ingestion, Transformation, Indexing, Registration
        assert pipeline[0] == mock_acquisition.return_value
        assert pipeline[1] == mock_schema.return_value
        assert pipeline[2] == mock_ingestion.return_value
        assert pipeline[3] == mock_transformation.return_value
        assert pipeline[4] == mock_indexing.return_value
        assert pipeline[5] == mock_registration.return_value


@pytest.mark.unit
class TestGazetteerInstallerExecutePipeline:
    """Test _execute_pipeline method."""

    def test_executes_all_stages(self):
        """Test that all pipeline stages are executed."""
        # Arrange
        installer = GazetteerInstaller()

        mock_source = Mock()
        mock_stage1 = Mock()
        mock_stage2 = Mock()
        pipeline = [mock_stage1, mock_stage2]

        # Act
        installer._execute_pipeline(mock_source, pipeline)

        # Assert
        mock_stage1.execute.assert_called_once()
        mock_stage2.execute.assert_called_once()

    def test_passes_source_to_all_stages(self):
        """Test that source config is passed to all stages."""
        # Arrange
        installer = GazetteerInstaller()

        mock_source = Mock()
        mock_stage = Mock()
        pipeline = [mock_stage]

        # Act
        installer._execute_pipeline(mock_source, pipeline)

        # Assert
        call_args = mock_stage.execute.call_args[0]
        assert call_args[0] == mock_source

    def test_shares_context_across_stages(self):
        """Test that context is shared across all stages."""
        # Arrange
        installer = GazetteerInstaller()

        mock_source = Mock()
        mock_stage1 = Mock()
        mock_stage2 = Mock()
        pipeline = [mock_stage1, mock_stage2]

        # Act
        installer._execute_pipeline(mock_source, pipeline)

        # Assert
        # Both stages should receive the same context dict
        context1 = mock_stage1.execute.call_args[0][1]
        context2 = mock_stage2.execute.call_args[0][1]
        assert context1 is context2


@pytest.mark.unit
class TestGazetteerInstallerInstall:
    """Test install method."""

    @patch("geoparser.gazetteer.installer.installer.user_data_dir")
    @patch("geoparser.gazetteer.installer.installer.GazetteerRepository")
    @patch("geoparser.gazetteer.installer.installer.GazetteerConfig")
    def test_loads_config_from_yaml(
        self, mock_config_class, mock_repo, mock_user_data_dir
    ):
        """Test that configuration is loaded from YAML file."""
        # Arrange
        mock_config = Mock()
        mock_config.name = "test_gaz"
        mock_config.sources = []
        mock_config_class.from_yaml.return_value = mock_config

        mock_repo.get_by_name.return_value = Mock()  # Existing gazetteer

        with tempfile.TemporaryDirectory() as temp_dir:
            mock_user_data_dir.return_value = temp_dir

            installer = GazetteerInstaller()
            installer.dependency_resolver = Mock()
            installer.dependency_resolver.resolve.return_value = []

            # Act
            installer.install("config.yaml")

            # Assert
            mock_config_class.from_yaml.assert_called_once_with("config.yaml")

    def test_creates_downloads_directory(self):
        """Test that downloads directory is created (tested in _create_downloads_directory)."""
        # This is already tested in TestGazetteerInstallerCreateDownloadsDirectory
        # Just verify the method is called during install

        installer = GazetteerInstaller()

        with patch.object(installer, "_create_downloads_directory") as mock_create_dir:
            with patch.object(installer, "_ensure_gazetteer_record"):
                mock_stage = Mock()
                with patch.object(
                    installer, "_create_pipeline", return_value=[mock_stage]
                ):
                    with patch.object(installer, "_execute_pipeline"):
                        with patch(
                            "geoparser.gazetteer.installer.installer.GazetteerConfig"
                        ) as mock_config_class:
                            mock_config = Mock()
                            mock_config.name = "test_gaz"
                            mock_config.sources = []
                            mock_config_class.from_yaml.return_value = mock_config

                            installer.dependency_resolver = Mock()
                            installer.dependency_resolver.resolve.return_value = []

                            # Act
                            installer.install("config.yaml")

                            # Assert
                            mock_create_dir.assert_called_once_with("test_gaz")

    def test_resolves_dependencies(self):
        """Test that dependencies are resolved."""
        # Arrange
        mock_source1 = Mock()
        mock_source1.name = "source1"
        mock_source2 = Mock()
        mock_source2.name = "source2"

        installer = GazetteerInstaller()

        with patch.object(
            installer, "_create_downloads_directory", return_value=Path("/tmp")
        ):
            with patch.object(installer, "_ensure_gazetteer_record"):
                mock_stage = Mock()
                with patch.object(
                    installer, "_create_pipeline", return_value=[mock_stage]
                ):
                    with patch.object(installer, "_execute_pipeline"):
                        with patch(
                            "geoparser.gazetteer.installer.installer.GazetteerConfig"
                        ) as mock_config_class:
                            mock_config = Mock()
                            mock_config.name = "test_gaz"
                            mock_config.sources = [mock_source1, mock_source2]
                            mock_config_class.from_yaml.return_value = mock_config

                            installer.dependency_resolver = Mock()
                            installer.dependency_resolver.resolve.return_value = [
                                mock_source2,
                                mock_source1,
                            ]

                            # Act
                            installer.install("config.yaml")

                            # Assert
                            installer.dependency_resolver.resolve.assert_called_once_with(
                                [mock_source1, mock_source2]
                            )

    def test_executes_pipeline_for_each_source(self):
        """Test that pipeline is executed for each source."""
        # Arrange
        mock_source1 = Mock()
        mock_source1.name = "source1"
        mock_source2 = Mock()
        mock_source2.name = "source2"

        installer = GazetteerInstaller()

        with patch.object(
            installer, "_create_downloads_directory", return_value=Path("/tmp")
        ):
            with patch.object(installer, "_ensure_gazetteer_record"):
                with patch.object(installer, "_execute_pipeline") as mock_exec:
                    mock_pipeline = [Mock(), Mock()]
                    with patch.object(
                        installer, "_create_pipeline", return_value=mock_pipeline
                    ):
                        with patch(
                            "geoparser.gazetteer.installer.installer.GazetteerConfig"
                        ) as mock_config_class:
                            mock_config = Mock()
                            mock_config.name = "test_gaz"
                            mock_config.sources = [mock_source1, mock_source2]
                            mock_config_class.from_yaml.return_value = mock_config

                            installer.dependency_resolver = Mock()
                            installer.dependency_resolver.resolve.return_value = [
                                mock_source1,
                                mock_source2,
                            ]

                            # Act
                            installer.install("config.yaml")

                            # Assert
                            # _execute_pipeline should be called twice (once for each source)
                            assert mock_exec.call_count == 2

    @patch("geoparser.gazetteer.installer.installer.user_data_dir")
    @patch("geoparser.gazetteer.installer.installer.GazetteerRepository")
    @patch("geoparser.gazetteer.installer.installer.GazetteerConfig")
    @patch("geoparser.gazetteer.installer.installer.AcquisitionStage")
    def test_keeps_downloads_when_requested(
        self,
        mock_acquisition,
        mock_config_class,
        mock_repo,
        mock_user_data_dir,
    ):
        """Test that downloads are kept when keep_downloads=True."""
        # Arrange
        mock_config = Mock()
        mock_config.name = "test_gaz"
        mock_config.sources = []
        mock_config_class.from_yaml.return_value = mock_config

        mock_repo.get_by_name.return_value = Mock()

        mock_stage = Mock()
        mock_acquisition.return_value = mock_stage

        with tempfile.TemporaryDirectory() as temp_dir:
            mock_user_data_dir.return_value = temp_dir

            installer = GazetteerInstaller()
            installer.dependency_resolver = Mock()
            installer.dependency_resolver.resolve.return_value = []

            # Act
            installer.install("config.yaml", keep_downloads=True)

            # Assert
            mock_stage.cleanup.assert_not_called()

    @patch("geoparser.gazetteer.installer.installer.user_data_dir")
    @patch("geoparser.gazetteer.installer.installer.GazetteerRepository")
    @patch("geoparser.gazetteer.installer.installer.GazetteerConfig")
    @patch("geoparser.gazetteer.installer.installer.AcquisitionStage")
    def test_cleans_up_downloads_by_default(
        self,
        mock_acquisition,
        mock_config_class,
        mock_repo,
        mock_user_data_dir,
    ):
        """Test that downloads are cleaned up by default."""
        # Arrange
        mock_config = Mock()
        mock_config.name = "test_gaz"
        mock_config.sources = []
        mock_config_class.from_yaml.return_value = mock_config

        mock_repo.get_by_name.return_value = Mock()

        mock_stage = Mock()
        mock_acquisition.return_value = mock_stage

        with tempfile.TemporaryDirectory() as temp_dir:
            mock_user_data_dir.return_value = temp_dir

            installer = GazetteerInstaller()
            installer.dependency_resolver = Mock()
            installer.dependency_resolver.resolve.return_value = []

            # Act
            installer.install("config.yaml", keep_downloads=False)

            # Assert
            mock_stage.cleanup.assert_called_once()
