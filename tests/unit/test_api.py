"""
Comprehensive tests for BigMapAPI class.

This module provides comprehensive test coverage for the BigMapAPI class,
testing all public methods, error conditions, and integration points.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import numpy as np
import zarr
import rasterio
from rasterio.transform import from_bounds

from bigmap.api import BigMapAPI, CalculationResult, SpeciesInfo
from bigmap.config import BigMapSettings, CalculationConfig
from bigmap.utils.location_config import LocationConfig


class TestBigMapAPIInitialization:
    """Test BigMapAPI initialization and configuration."""

    def test_init_default_config(self):
        """Test initialization with default configuration."""
        api = BigMapAPI()

        assert isinstance(api.settings, BigMapSettings)
        assert api._rest_client is None  # Lazy loading
        assert api._processor is None  # Lazy loading

    def test_init_with_settings_object(self, test_settings):
        """Test initialization with BigMapSettings object."""
        api = BigMapAPI(config=test_settings)

        assert api.settings is test_settings
        assert api.settings.data_dir == test_settings.data_dir

    def test_init_with_config_path(self, temp_dir):
        """Test initialization with configuration file path."""
        config_path = temp_dir / "test_config.yaml"
        config_content = """
data_dir: "/tmp/data"
output_dir: "/tmp/output"
cache_dir: "/tmp/cache"
calculations:
  - name: "species_richness"
    enabled: true
"""
        config_path.write_text(config_content)

        api = BigMapAPI(config=config_path)

        assert api.settings.data_dir == Path("/tmp/data")
        assert api.settings.output_dir == Path("/tmp/output")
        assert len(api.settings.calculations) == 1
        assert api.settings.calculations[0].name == "species_richness"

    def test_lazy_loading_rest_client(self):
        """Test lazy loading of REST client."""
        api = BigMapAPI()

        # First access creates the client
        client1 = api.rest_client
        assert client1 is not None

        # Second access returns same client
        client2 = api.rest_client
        assert client1 is client2

    def test_lazy_loading_processor(self):
        """Test lazy loading of forest metrics processor."""
        api = BigMapAPI()

        # First access creates the processor
        processor1 = api.processor
        assert processor1 is not None

        # Second access returns same processor
        processor2 = api.processor
        assert processor1 is processor2


class TestBigMapAPIListSpecies:
    """Test list_species() method."""

    @pytest.fixture
    def mock_species_data(self):
        """Mock species data from REST client."""
        return [
            {
                'species_code': '0131',
                'common_name': 'Balsam fir',
                'scientific_name': 'Abies balsamea',
                'function_name': 'FIA_species_131'
            },
            {
                'species_code': '0068',
                'common_name': 'American sweetgum',
                'scientific_name': 'Liquidambar styraciflua',
                'function_name': 'FIA_species_068'
            },
            {
                'species_code': '0202',
                'common_name': 'Douglas-fir',
                'scientific_name': 'Pseudotsuga menziesii',
                'function_name': None  # Test optional field
            }
        ]

    def test_list_species_success(self, mock_species_data):
        """Test successful species listing."""
        api = BigMapAPI()

        with patch.object(api.rest_client, 'list_available_species', return_value=mock_species_data):
            species = api.list_species()

        assert len(species) == 3
        assert all(isinstance(s, SpeciesInfo) for s in species)

        # Test first species
        assert species[0].species_code == '0131'
        assert species[0].common_name == 'Balsam fir'
        assert species[0].scientific_name == 'Abies balsamea'
        assert species[0].function_name == 'FIA_species_131'

        # Test species with None function_name
        assert species[2].function_name is None

    def test_list_species_empty_response(self):
        """Test handling of empty species response."""
        api = BigMapAPI()

        with patch.object(api.rest_client, 'list_available_species', return_value=[]):
            species = api.list_species()

        assert species == []

    def test_list_species_api_error(self):
        """Test handling of REST client errors."""
        api = BigMapAPI()

        with patch.object(api.rest_client, 'list_available_species', side_effect=Exception("API Error")):
            with pytest.raises(Exception, match="API Error"):
                api.list_species()


class TestBigMapAPIDownloadSpecies:
    """Test download_species() method."""

    def test_download_species_with_state(self, temp_dir):
        """Test downloading species data for a state."""
        api = BigMapAPI()
        expected_files = [temp_dir / "montana_0202_douglas_fir.tif"]

        with patch.object(api.rest_client, 'batch_export_location_species', return_value=expected_files):
            with patch('bigmap.api.LocationConfig') as mock_location_config:
                # Mock location config
                mock_config = MagicMock()
                mock_config.location_name = "Montana"
                mock_config.web_mercator_bbox = (-12000000, 5000000, -11000000, 6000000)
                mock_location_config.from_state.return_value = mock_config

                files = api.download_species(
                    output_dir=temp_dir,
                    species_codes=['0202'],
                    state='Montana'
                )

        assert files == expected_files
        assert temp_dir.exists()

    def test_download_species_with_county(self, temp_dir):
        """Test downloading species data for a county."""
        api = BigMapAPI()
        expected_files = [temp_dir / "harris_texas_0131_balsam_fir.tif"]

        with patch.object(api.rest_client, 'batch_export_location_species', return_value=expected_files):
            with patch('bigmap.api.LocationConfig') as mock_location_config:
                # Mock location config
                mock_config = MagicMock()
                mock_config.location_name = "Harris County, Texas"
                mock_config.web_mercator_bbox = (-10000000, 3000000, -9000000, 4000000)
                mock_location_config.from_county.return_value = mock_config

                files = api.download_species(
                    output_dir=temp_dir,
                    species_codes=['0131'],
                    state='Texas',
                    county='Harris'
                )

        assert files == expected_files

    def test_download_species_with_bbox(self, temp_dir):
        """Test downloading species data with custom bounding box."""
        api = BigMapAPI()
        bbox = (-104.0, 44.0, -103.0, 45.0)
        expected_files = [temp_dir / "location_0202_species.tif"]

        with patch.object(api.rest_client, 'batch_export_location_species', return_value=expected_files):
            files = api.download_species(
                output_dir=temp_dir,
                species_codes=['0202'],
                bbox=bbox,
                crs='4326'
            )

        assert files == expected_files

    def test_download_species_with_location_config(self, temp_dir):
        """Test downloading with location configuration file."""
        api = BigMapAPI()
        config_file = temp_dir / "location.yaml"
        expected_files = [temp_dir / "custom_location_species.tif"]

        with patch.object(api.rest_client, 'batch_export_location_species', return_value=expected_files):
            with patch('bigmap.api.LocationConfig') as mock_location_config:
                mock_config = MagicMock()
                mock_config.location_name = "Custom Location"
                mock_config.web_mercator_bbox = (-11000000, 4000000, -10000000, 5000000)
                mock_location_config.return_value = mock_config

                files = api.download_species(
                    output_dir=temp_dir,
                    location_config=config_file,
                    species_codes=['0131']
                )

        assert files == expected_files

    def test_download_species_no_location_error(self, temp_dir):
        """Test error when no location parameters provided."""
        api = BigMapAPI()

        with pytest.raises(ValueError, match="Must specify state, bbox, or location_config"):
            api.download_species(output_dir=temp_dir, species_codes=['0202'])

    def test_download_species_creates_output_directory(self, temp_dir):
        """Test that output directory is created if it doesn't exist."""
        api = BigMapAPI()
        output_dir = temp_dir / "new_downloads"

        with patch.object(api.rest_client, 'batch_export_location_species', return_value=[]):
            with patch('bigmap.api.LocationConfig') as mock_location_config:
                mock_config = MagicMock()
                mock_config.location_name = "Test"
                mock_config.web_mercator_bbox = (-11000000, 4000000, -10000000, 5000000)
                mock_location_config.from_state.return_value = mock_config

                api.download_species(output_dir=output_dir, state="Montana")

        assert output_dir.exists()
        assert output_dir.is_dir()


class TestBigMapAPICreateZarr:
    """Test create_zarr() method."""

    @pytest.fixture
    def sample_geotiff_files(self, temp_dir):
        """Create sample GeoTIFF files for testing."""
        # Create sample data
        height, width = 100, 100
        bounds = (-2000000, -1000000, -1900000, -900000)
        transform = from_bounds(*bounds, width, height)

        tiff_files = []
        species_codes = ['0131', '0068', '0202']
        species_names = ['balsam_fir', 'sweetgum', 'douglas_fir']

        for code, name in zip(species_codes, species_names):
            tiff_path = temp_dir / f"montana_{code}_{name}.tif"

            # Generate unique data for each species
            data = np.random.rand(height, width) * float(code)
            data[data < 50] = 0  # Some areas with no biomass

            with rasterio.open(
                str(tiff_path),  # Convert Path to string for rasterio
                'w',
                driver='GTiff',
                height=height,
                width=width,
                count=1,
                dtype=np.float32,
                crs='EPSG:3857',
                transform=transform,
                nodata=0.0
            ) as dst:
                dst.write(data.astype(np.float32), 1)

            tiff_files.append(tiff_path)

        return tiff_files, species_codes, species_names

    def test_create_zarr_success(self, temp_dir, sample_geotiff_files):
        """Test successful Zarr creation from GeoTIFF files."""
        tiff_files, species_codes, species_names = sample_geotiff_files
        input_dir = temp_dir / "geotiffs"
        input_dir.mkdir()

        # Move files to input directory
        for f in tiff_files:
            f.rename(input_dir / f.name)

        output_path = temp_dir / "test.zarr"

        with patch('bigmap.api.create_zarr_from_geotiffs') as mock_create:
            with patch('bigmap.api.validate_zarr_store') as mock_validate:
                mock_validate.return_value = {
                    'shape': (4, 100, 100),
                    'num_species': 4
                }

                api = BigMapAPI()
                result_path = api.create_zarr(input_dir, output_path)

        assert result_path == output_path
        mock_create.assert_called_once()
        mock_validate.assert_called_once_with(output_path)

    def test_create_zarr_with_species_filter(self, temp_dir, sample_geotiff_files):
        """Test Zarr creation with species code filtering."""
        tiff_files, species_codes, species_names = sample_geotiff_files
        input_dir = temp_dir / "geotiffs"
        input_dir.mkdir()

        # Move files to input directory
        for f in tiff_files:
            f.rename(input_dir / f.name)

        output_path = temp_dir / "filtered.zarr"
        filter_species = ['0131', '0202']  # Only 2 species

        with patch('bigmap.api.create_zarr_from_geotiffs') as mock_create:
            with patch('bigmap.api.validate_zarr_store') as mock_validate:
                mock_validate.return_value = {'shape': (3, 100, 100), 'num_species': 3}

                api = BigMapAPI()
                api.create_zarr(
                    input_dir,
                    output_path,
                    species_codes=filter_species
                )

        # Verify only filtered files were used
        call_args = mock_create.call_args
        geotiff_paths = call_args[1]['geotiff_paths']
        assert len(geotiff_paths) == 2  # Only 2 species

    def test_create_zarr_custom_parameters(self, temp_dir, sample_geotiff_files):
        """Test Zarr creation with custom parameters."""
        tiff_files, species_codes, species_names = sample_geotiff_files
        input_dir = temp_dir / "geotiffs"
        input_dir.mkdir()

        # Move files to input directory
        for f in tiff_files:
            f.rename(input_dir / f.name)

        output_path = temp_dir / "custom.zarr"

        with patch('bigmap.api.create_zarr_from_geotiffs') as mock_create:
            with patch('bigmap.api.validate_zarr_store') as mock_validate:
                mock_validate.return_value = {'shape': (4, 100, 100), 'num_species': 4}

                api = BigMapAPI()
                api.create_zarr(
                    input_dir,
                    output_path,
                    chunk_size=(2, 500, 500),
                    compression='gzip',
                    compression_level=9,
                    include_total=False
                )

        # Verify custom parameters were passed
        call_args = mock_create.call_args[1]
        assert call_args['chunk_size'] == (2, 500, 500)
        assert call_args['compression'] == 'gzip'
        assert call_args['compression_level'] == 9
        assert call_args['include_total'] is False

    def test_create_zarr_input_directory_not_exists(self, temp_dir):
        """Test error when input directory doesn't exist."""
        api = BigMapAPI()
        nonexistent_dir = temp_dir / "nonexistent"
        output_path = temp_dir / "test.zarr"

        with pytest.raises(ValueError, match="Input directory does not exist"):
            api.create_zarr(nonexistent_dir, output_path)

    def test_create_zarr_no_tiff_files(self, temp_dir):
        """Test error when no GeoTIFF files found."""
        api = BigMapAPI()
        input_dir = temp_dir / "empty"
        input_dir.mkdir()
        output_path = temp_dir / "test.zarr"

        with pytest.raises(ValueError, match="No GeoTIFF files found"):
            api.create_zarr(input_dir, output_path)

    def test_create_zarr_no_matching_species(self, temp_dir, sample_geotiff_files):
        """Test error when no files match species filter."""
        tiff_files, species_codes, species_names = sample_geotiff_files
        input_dir = temp_dir / "geotiffs"
        input_dir.mkdir()

        # Move files to input directory
        for f in tiff_files:
            f.rename(input_dir / f.name)

        api = BigMapAPI()
        output_path = temp_dir / "test.zarr"

        with pytest.raises(ValueError, match="No files found for species codes"):
            api.create_zarr(input_dir, output_path, species_codes=['9999'])


class TestBigMapAPICalculateMetrics:
    """Test calculate_metrics() method."""

    @pytest.fixture
    def mock_zarr_path(self, temp_dir):
        """Create a mock Zarr path for testing."""
        zarr_path = temp_dir / "test.zarr"
        zarr_path.mkdir()  # Create as directory to simulate Zarr store
        return zarr_path

    def test_calculate_metrics_default_config(self, mock_zarr_path):
        """Test calculate_metrics with default configuration."""
        api = BigMapAPI()

        mock_output_paths = {
            'species_richness': '/tmp/richness.tif',
            'total_biomass': '/tmp/total.tif'
        }

        with patch('bigmap.api.ForestMetricsProcessor') as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.run_calculations.return_value = mock_output_paths
            mock_processor_class.return_value = mock_processor

            results = api.calculate_metrics(mock_zarr_path)

        assert len(results) == 2
        assert all(isinstance(r, CalculationResult) for r in results)

        # Check first result
        result_names = [r.name for r in results]
        assert 'species_richness' in result_names
        assert 'total_biomass' in result_names

    def test_calculate_metrics_custom_calculations(self, mock_zarr_path):
        """Test calculate_metrics with custom calculations list."""
        api = BigMapAPI()
        custom_calcs = ['shannon_diversity', 'simpson_diversity']

        mock_output_paths = {
            'shannon_diversity': '/tmp/shannon.tif',
            'simpson_diversity': '/tmp/simpson.tif'
        }

        with patch('bigmap.api.registry') as mock_registry:
            mock_registry.list_calculations.return_value = [
                'shannon_diversity', 'simpson_diversity', 'species_richness'
            ]

            with patch('bigmap.api.ForestMetricsProcessor') as mock_processor_class:
                mock_processor = MagicMock()
                mock_processor.run_calculations.return_value = mock_output_paths
                mock_processor_class.return_value = mock_processor

                results = api.calculate_metrics(
                    mock_zarr_path,
                    calculations=custom_calcs
                )

        assert len(results) == 2
        result_names = [r.name for r in results]
        assert 'shannon_diversity' in result_names
        assert 'simpson_diversity' in result_names

    def test_calculate_metrics_custom_output_dir(self, mock_zarr_path, temp_dir):
        """Test calculate_metrics with custom output directory."""
        api = BigMapAPI()
        custom_output = temp_dir / "custom_output"

        with patch('bigmap.api.ForestMetricsProcessor') as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.run_calculations.return_value = {}
            mock_processor_class.return_value = mock_processor

            api.calculate_metrics(mock_zarr_path, output_dir=custom_output)

        # Check that processor was called with updated settings
        processor_call_args = mock_processor_class.call_args[0]
        settings = processor_call_args[0]
        assert settings.output_dir == custom_output

    def test_calculate_metrics_custom_config_file(self, mock_zarr_path, temp_dir):
        """Test calculate_metrics with custom configuration file."""
        config_path = temp_dir / "custom_config.yaml"
        config_content = """
data_dir: "/custom/data"
output_dir: "/custom/output"
calculations:
  - name: "total_biomass"
    enabled: true
"""
        config_path.write_text(config_content)

        api = BigMapAPI()

        with patch('bigmap.api.load_settings') as mock_load_settings:
            mock_settings = MagicMock()
            mock_load_settings.return_value = mock_settings

            with patch('bigmap.api.ForestMetricsProcessor') as mock_processor_class:
                mock_processor = MagicMock()
                mock_processor.run_calculations.return_value = {}
                mock_processor_class.return_value = mock_processor

                api.calculate_metrics(mock_zarr_path, config=config_path)

        mock_load_settings.assert_called_once_with(config_path)

    def test_calculate_metrics_zarr_not_exists(self, temp_dir):
        """Test error when Zarr store doesn't exist."""
        api = BigMapAPI()
        nonexistent_zarr = temp_dir / "nonexistent.zarr"

        with pytest.raises(ValueError, match="Zarr store not found"):
            api.calculate_metrics(nonexistent_zarr)

    def test_calculate_metrics_invalid_calculations(self, mock_zarr_path):
        """Test error with invalid calculation names."""
        api = BigMapAPI()

        with patch('bigmap.api.registry') as mock_registry:
            mock_registry.list_calculations.return_value = ['species_richness', 'total_biomass']

            with pytest.raises(ValueError, match="Unknown calculations"):
                api.calculate_metrics(
                    mock_zarr_path,
                    calculations=['invalid_calculation']
                )


class TestBigMapAPICreateMaps:
    """Test create_maps() method."""

    @pytest.fixture
    def mock_zarr_path(self, temp_dir):
        """Create a mock Zarr path for testing."""
        zarr_path = temp_dir / "test.zarr"
        zarr_path.mkdir()
        return zarr_path

    @pytest.fixture
    def mock_mapper(self):
        """Mock ZarrMapper for testing."""
        with patch('bigmap.api.ZarrMapper') as mock_mapper_class:
            mock_mapper = MagicMock()
            mock_mapper_class.return_value = mock_mapper
            yield mock_mapper

    def test_create_maps_species_type(self, mock_zarr_path, temp_dir, mock_mapper):
        """Test creating species maps."""
        api = BigMapAPI()
        output_dir = temp_dir / "maps"
        species_codes = ['0131', '0202']

        # Mock matplotlib figure
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_mapper.create_species_map.return_value = (mock_fig, mock_ax)

        with patch('bigmap.visualization.plots.save_figure') as mock_save:
            with patch('matplotlib.pyplot.close') as mock_close:
                maps = api.create_maps(
                    mock_zarr_path,
                    map_type="species",
                    species=species_codes,
                    output_dir=output_dir
                )

        assert len(maps) == 2  # One map per species
        assert output_dir.exists()
        assert mock_save.call_count == 2
        assert mock_close.call_count == 2

    def test_create_maps_species_show_all(self, mock_zarr_path, temp_dir, mock_mapper):
        """Test creating maps for all species."""
        api = BigMapAPI()
        output_dir = temp_dir / "maps"

        # Mock species info
        mock_mapper.get_species_info.return_value = [
            {'code': '0131', 'name': 'Balsam Fir', 'index': 1},
            {'code': '0202', 'name': 'Douglas Fir', 'index': 2},
            {'code': '0000', 'name': 'Total', 'index': 0}  # Should be skipped
        ]

        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_mapper.create_species_map.return_value = (mock_fig, mock_ax)

        with patch('bigmap.visualization.plots.save_figure') as mock_save:
            with patch('matplotlib.pyplot.close') as mock_close:
                maps = api.create_maps(
                    mock_zarr_path,
                    map_type="species",
                    show_all=True,
                    output_dir=output_dir
                )

        assert len(maps) == 2  # Total biomass (0000) should be skipped
        assert mock_save.call_count == 2

    def test_create_maps_diversity_type(self, mock_zarr_path, temp_dir, mock_mapper):
        """Test creating diversity maps."""
        api = BigMapAPI()
        output_dir = temp_dir / "maps"

        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_mapper.create_diversity_map.return_value = (mock_fig, mock_ax)

        with patch('bigmap.visualization.plots.save_figure') as mock_save:
            with patch('matplotlib.pyplot.close') as mock_close:
                maps = api.create_maps(
                    mock_zarr_path,
                    map_type="diversity",
                    output_dir=output_dir
                )

        assert len(maps) == 2  # Shannon and Simpson diversity
        assert mock_save.call_count == 2

    def test_create_maps_richness_type(self, mock_zarr_path, temp_dir, mock_mapper):
        """Test creating species richness map."""
        api = BigMapAPI()
        output_dir = temp_dir / "maps"

        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_mapper.create_richness_map.return_value = (mock_fig, mock_ax)

        with patch('bigmap.visualization.plots.save_figure') as mock_save:
            with patch('matplotlib.pyplot.close') as mock_close:
                maps = api.create_maps(
                    mock_zarr_path,
                    map_type="richness",
                    output_dir=output_dir
                )

        assert len(maps) == 1
        assert mock_save.call_count == 1

    def test_create_maps_comparison_type(self, mock_zarr_path, temp_dir, mock_mapper):
        """Test creating species comparison map."""
        api = BigMapAPI()
        output_dir = temp_dir / "maps"
        species_list = ['0131', '0202', '0068']

        mock_fig = MagicMock()
        mock_mapper.create_comparison_map.return_value = mock_fig

        with patch('bigmap.visualization.plots.save_figure') as mock_save:
            with patch('matplotlib.pyplot.close') as mock_close:
                maps = api.create_maps(
                    mock_zarr_path,
                    map_type="comparison",
                    species=species_list,
                    output_dir=output_dir
                )

        assert len(maps) == 1
        assert mock_save.call_count == 1
        mock_mapper.create_comparison_map.assert_called_once_with(
            species_list=species_list,
            cmap='viridis'
        )

    def test_create_maps_custom_parameters(self, mock_zarr_path, temp_dir, mock_mapper):
        """Test creating maps with custom parameters."""
        api = BigMapAPI()

        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_mapper.create_species_map.return_value = (mock_fig, mock_ax)

        with patch('bigmap.visualization.plots.save_figure') as mock_save:
            with patch('matplotlib.pyplot.close'):
                maps = api.create_maps(
                    mock_zarr_path,
                    map_type="species",
                    species=['0131'],
                    output_dir=temp_dir,
                    format="jpg",
                    dpi=150,
                    cmap="plasma",
                    state="MT",
                    basemap="terrain"
                )

        # Check that custom parameters were passed to mapper
        mock_mapper.create_species_map.assert_called_once_with(
            species='0131',
            cmap='plasma',
            state_boundary='MT',
            basemap='terrain'
        )

        # Check save_figure was called with custom parameters
        save_call_args = mock_save.call_args
        assert save_call_args[1]['dpi'] == 150
        assert str(save_call_args[0][1]).endswith('.jpg')

    def test_create_maps_zarr_not_exists(self, temp_dir):
        """Test error when Zarr store doesn't exist."""
        api = BigMapAPI()
        nonexistent_zarr = temp_dir / "nonexistent.zarr"

        with pytest.raises(ValueError, match="Zarr store not found"):
            api.create_maps(nonexistent_zarr)

    def test_create_maps_species_no_codes_or_show_all(self, mock_zarr_path, temp_dir, mock_mapper):
        """Test error when species map requested but no species specified."""
        api = BigMapAPI()

        with pytest.raises(ValueError, match="Please specify species codes or use show_all=True"):
            api.create_maps(mock_zarr_path, map_type="species")

    def test_create_maps_comparison_insufficient_species(self, mock_zarr_path, temp_dir, mock_mapper):
        """Test error when comparison map requested with < 2 species."""
        api = BigMapAPI()

        with pytest.raises(ValueError, match="Comparison maps require at least 2 species"):
            api.create_maps(
                mock_zarr_path,
                map_type="comparison",
                species=['0131']  # Only 1 species
            )

    def test_create_maps_invalid_map_type(self, mock_zarr_path, temp_dir, mock_mapper):
        """Test error with invalid map type."""
        api = BigMapAPI()

        with pytest.raises(ValueError, match="Unknown map type"):
            api.create_maps(mock_zarr_path, map_type="invalid_type")


class TestBigMapAPIGetLocationConfig:
    """Test get_location_config() method."""

    def test_get_location_config_state_only(self):
        """Test getting location config for state."""
        api = BigMapAPI()

        with patch('bigmap.api.LocationConfig') as mock_location_config:
            mock_config = MagicMock()
            mock_location_config.from_state.return_value = mock_config

            config = api.get_location_config(state="Montana")

        assert config is mock_config
        mock_location_config.from_state.assert_called_once_with("Montana", output_path=None)

    def test_get_location_config_state_and_county(self):
        """Test getting location config for county."""
        api = BigMapAPI()

        with patch('bigmap.api.LocationConfig') as mock_location_config:
            mock_config = MagicMock()
            mock_location_config.from_county.return_value = mock_config

            config = api.get_location_config(state="Texas", county="Harris")

        assert config is mock_config
        mock_location_config.from_county.assert_called_once_with(
            "Harris", "Texas", output_path=None
        )

    def test_get_location_config_custom_bbox(self):
        """Test getting location config with custom bounding box."""
        api = BigMapAPI()
        bbox = (-104.0, 44.0, -103.0, 45.0)

        with patch('bigmap.api.LocationConfig') as mock_location_config:
            mock_config = MagicMock()
            mock_location_config.from_bbox.return_value = mock_config

            config = api.get_location_config(bbox=bbox, crs="EPSG:4326")

        assert config is mock_config
        mock_location_config.from_bbox.assert_called_once_with(
            bbox, name="Custom Region", crs="EPSG:4326", output_path=None
        )

    def test_get_location_config_with_output_path(self, temp_dir):
        """Test getting location config with output path."""
        api = BigMapAPI()
        output_path = temp_dir / "config.yaml"

        with patch('bigmap.api.LocationConfig') as mock_location_config:
            mock_config = MagicMock()
            mock_location_config.from_state.return_value = mock_config

            api.get_location_config(state="Montana", output_path=output_path)

        mock_location_config.from_state.assert_called_once_with(
            "Montana", output_path=output_path
        )

    def test_get_location_config_county_without_state(self):
        """Test error when county specified without state."""
        api = BigMapAPI()

        with pytest.raises(ValueError, match="County requires state to be specified"):
            api.get_location_config(county="Harris")

    def test_get_location_config_no_parameters(self):
        """Test error when no location parameters provided."""
        api = BigMapAPI()

        with pytest.raises(ValueError, match="Must specify state, county, or bbox"):
            api.get_location_config()


class TestBigMapAPIUtilityMethods:
    """Test utility methods list_calculations() and validate_zarr()."""

    def test_list_calculations(self):
        """Test listing available calculations."""
        api = BigMapAPI()
        expected_calculations = [
            'species_richness', 'shannon_diversity', 'simpson_diversity', 'total_biomass'
        ]

        with patch('bigmap.api.registry') as mock_registry:
            mock_registry.list_calculations.return_value = expected_calculations

            calculations = api.list_calculations()

        assert calculations == expected_calculations
        mock_registry.list_calculations.assert_called_once()

    def test_validate_zarr(self, temp_dir):
        """Test Zarr store validation."""
        api = BigMapAPI()
        zarr_path = temp_dir / "test.zarr"
        expected_info = {
            'shape': (5, 1000, 1000),
            'num_species': 5,
            'chunks': (1, 500, 500),
            'compression': 'lz4'
        }

        with patch('bigmap.api.validate_zarr_store', return_value=expected_info) as mock_validate:
            info = api.validate_zarr(zarr_path)

        assert info == expected_info
        mock_validate.assert_called_once_with(zarr_path)


class TestBigMapAPIEdgeCasesAndMissingCoverage:
    """Test edge cases and lines missing coverage."""

    def test_download_species_bbox_no_location_bbox(self, temp_dir):
        """Test error when bbox doesn't yield location_bbox."""
        api = BigMapAPI()

        with patch('bigmap.api.LocationConfig') as mock_location_config:
            mock_config = MagicMock()
            mock_config.web_mercator_bbox = None  # No bbox returned
            mock_location_config.from_state.return_value = mock_config

            with pytest.raises(ValueError, match="Could not determine bounding box for location"):
                api.download_species(output_dir=temp_dir, state="InvalidState")

    def test_create_zarr_filename_parsing_edge_cases(self, temp_dir):
        """Test filename parsing with various formats."""
        api = BigMapAPI()
        input_dir = temp_dir / "geotiffs"
        input_dir.mkdir()
        output_path = temp_dir / "test.zarr"

        # Create files with different naming patterns
        test_files = [
            "species_1234_common_name.tif",
            "no_code_file.tif",
            "0999_short.tif",
            "complex_5678_with_multiple_underscores_in_name.tif"
        ]

        for filename in test_files:
            test_file = input_dir / filename
            test_file.touch()

        with patch('bigmap.api.create_zarr_from_geotiffs') as mock_create:
            with patch('bigmap.api.validate_zarr_store', return_value={'shape': (5, 100, 100), 'num_species': 5}):
                api.create_zarr(input_dir, output_path)

        # Verify it was called with parsed species info
        call_args = mock_create.call_args[1]
        species_codes = call_args['species_codes']
        species_names = call_args['species_names']

        assert len(species_codes) == 4
        assert len(species_names) == 4

    def test_calculate_metrics_with_settings_object_config(self, temp_dir):
        """Test calculate_metrics with BigMapSettings object as config."""
        api = BigMapAPI()
        zarr_path = temp_dir / "test.zarr"
        zarr_path.mkdir()

        # Custom settings object
        custom_settings = BigMapSettings(
            data_dir=temp_dir,
            output_dir=temp_dir / "custom_output"
        )

        with patch('bigmap.api.ForestMetricsProcessor') as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.run_calculations.return_value = {'test_calc': '/tmp/test.tif'}
            mock_processor_class.return_value = mock_processor

            results = api.calculate_metrics(zarr_path, config=custom_settings)

        # Verify custom settings were used
        processor_call_args = mock_processor_class.call_args[0]
        used_settings = processor_call_args[0]
        assert used_settings is custom_settings

    def test_create_maps_default_cmap_fallback(self, temp_dir):
        """Test that default colormap is used for unknown map types."""
        api = BigMapAPI()
        zarr_path = temp_dir / "test.zarr"
        zarr_path.mkdir()

        with patch('bigmap.api.ZarrMapper') as mock_mapper_class:
            mock_mapper = MagicMock()
            mock_fig = MagicMock()
            mock_ax = MagicMock()
            mock_mapper.create_species_map.return_value = (mock_fig, mock_ax)
            mock_mapper_class.return_value = mock_mapper

            with patch('bigmap.visualization.plots.save_figure'):
                with patch('matplotlib.pyplot.close'):
                    # This should use default 'viridis' since 'unknown' is not in defaults
                    api.create_maps(zarr_path, map_type="species", species=['0131'])

            # Check that viridis was used (default fallback)
            call_args = mock_mapper.create_species_map.call_args[1]
            assert call_args['cmap'] == 'viridis'

    def test_create_zarr_filename_no_match_fallback(self, temp_dir):
        """Test filename parsing when no species code is found."""
        api = BigMapAPI()
        input_dir = temp_dir / "geotiffs"
        input_dir.mkdir()
        output_path = temp_dir / "test.zarr"

        # Create a file with no numeric species code
        test_file = input_dir / "no_numeric_code.tif"
        test_file.touch()

        with patch('bigmap.api.create_zarr_from_geotiffs') as mock_create:
            with patch('bigmap.api.validate_zarr_store', return_value={'shape': (2, 100, 100), 'num_species': 2}):
                api.create_zarr(input_dir, output_path)

        # Verify it extracted first 4 chars as fallback code
        call_args = mock_create.call_args[1]
        species_codes = call_args['species_codes']
        assert species_codes[0] == 'no_n'  # First 4 characters

    def test_create_zarr_with_tiff_extension(self, temp_dir):
        """Test that both .tif and .tiff files are found."""
        api = BigMapAPI()
        input_dir = temp_dir / "geotiffs"
        input_dir.mkdir()
        output_path = temp_dir / "test.zarr"

        # Create both .tif and .tiff files
        tif_file = input_dir / "species_1234_test.tif"
        tiff_file = input_dir / "species_5678_test.tiff"
        tif_file.touch()
        tiff_file.touch()

        with patch('bigmap.api.create_zarr_from_geotiffs') as mock_create:
            with patch('bigmap.api.validate_zarr_store', return_value={'shape': (3, 100, 100), 'num_species': 3}):
                api.create_zarr(input_dir, output_path)

        # Verify both files were found
        call_args = mock_create.call_args[1]
        geotiff_paths = call_args['geotiff_paths']
        assert len(geotiff_paths) == 2


class TestBigMapAPIIntegration:
    """Integration tests combining multiple API methods."""

    def test_full_workflow_mock(self, temp_dir):
        """Test a complete workflow with mocked components."""
        api = BigMapAPI()

        # Mock components
        mock_species_data = [
            {
                'species_code': '0131',
                'common_name': 'Balsam fir',
                'scientific_name': 'Abies balsamea'
            }
        ]

        download_files = [temp_dir / "montana_0131_balsam_fir.tif"]
        zarr_path = temp_dir / "montana.zarr"

        with patch.object(api.rest_client, 'list_available_species', return_value=mock_species_data):
            with patch.object(api.rest_client, 'batch_export_location_species', return_value=download_files):
                with patch('bigmap.api.LocationConfig') as mock_location_config:
                    with patch('bigmap.api.create_zarr_from_geotiffs'):
                        with patch('bigmap.api.validate_zarr_store', return_value={'shape': (2, 100, 100), 'num_species': 2}):

                            # Mock location config
                            mock_config = MagicMock()
                            mock_config.location_name = "Montana"
                            mock_config.web_mercator_bbox = (-12000000, 5000000, -11000000, 6000000)
                            mock_location_config.from_state.return_value = mock_config

                            # Create fake downloads directory and GeoTIFF file
                            downloads_dir = temp_dir / "downloads"
                            downloads_dir.mkdir(parents=True, exist_ok=True)

                            # Create a real .tif file instead of using touch()
                            fake_tif = downloads_dir / "montana_0131_balsam_fir.tif"
                            fake_tif.write_bytes(b"fake tiff content")  # Minimal fake content

                            # 1. List species
                            species = api.list_species()
                            assert len(species) == 1

                            # 2. Download species data
                            files = api.download_species(
                                output_dir=downloads_dir,
                                species_codes=['0131'],
                                state="Montana"
                            )
                            assert len(files) == 1

                            # 3. Create Zarr
                            zarr_result = api.create_zarr(
                                downloads_dir,
                                zarr_path
                            )
                            assert zarr_result == zarr_path

    def test_error_propagation(self, temp_dir):
        """Test that errors from underlying components are properly propagated."""
        api = BigMapAPI()

        # Test that REST client errors bubble up
        with patch.object(api.rest_client, 'list_available_species', side_effect=ConnectionError("Network error")):
            with pytest.raises(ConnectionError, match="Network error"):
                api.list_species()

        # Test that processor errors bubble up
        zarr_path = temp_dir / "test.zarr"
        zarr_path.mkdir()

        with patch('bigmap.api.ForestMetricsProcessor', side_effect=RuntimeError("Processing error")):
            with pytest.raises(RuntimeError, match="Processing error"):
                api.calculate_metrics(zarr_path)