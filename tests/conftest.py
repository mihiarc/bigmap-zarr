"""
Pytest configuration and shared fixtures for BigMap tests.
"""

import tempfile
from pathlib import Path
from typing import Generator

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_bounds


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_raster(temp_dir: Path) -> Path:
    """Create a sample raster file for testing."""
    raster_path = temp_dir / "sample_raster.tif"
    
    # Create sample data
    height, width = 100, 100
    data = np.random.rand(height, width) * 100  # Random biomass values 0-100
    
    # Set some pixels to 0 (no biomass)
    data[data < 20] = 0
    
    # Define spatial properties
    bounds = (-2000000, -1000000, -1900000, -900000)  # Example NC coordinates
    transform = from_bounds(*bounds, width, height)
    
    # Write raster
    with rasterio.open(
        raster_path,
        'w',
        driver='GTiff',
        height=height,
        width=width,
        count=1,
        dtype=np.float32,
        crs='ESRI:102039',
        transform=transform,
        nodata=None
    ) as dst:
        dst.write(data.astype(np.float32), 1)
    
    return raster_path


@pytest.fixture
def sample_species_data() -> dict:
    """Sample species data for testing."""
    return {
        'species_codes': ['TOTAL', 'SPCD0012', 'SPCD0043'],
        'species_names': ['All Species Combined', 'White Oak', 'Loblolly Pine'],
        'n_species': 3
    }


@pytest.fixture
def mock_zarr_attrs() -> dict:
    """Mock zarr attributes for testing."""
    return {
        'description': 'Test biomass data',
        'crs': 'ESRI:102039',
        'transform': [-2000000, 30, 0, -900000, 0, -30],
        'bounds': [-2000000, -1000000, -1900000, -900000],
        'height': 100,
        'width': 100,
        'species_codes': ['TOTAL'],
        'species_names': ['All Species Combined'],
        'n_species': 1
    } 