"""
Pytest configuration and shared fixtures for BigMap tests.
"""

import tempfile
from pathlib import Path
from typing import Generator
import shutil

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_bounds
import zarr

from bigmap.config import BigMapSettings, CalculationConfig


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
        str(raster_path),  # Convert Path to string
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
def sample_zarr_array(temp_dir: Path) -> zarr.Array:
    """Create a sample zarr array with multiple species for testing."""
    zarr_path = temp_dir / "test_biomass.zarr"
    
    # Create test data: 5 species + 1 total, 100x100 pixels
    n_species = 6
    height, width = 100, 100
    
    # Create zarr array
    z = zarr.open_array(
        str(zarr_path),
        mode='w',
        shape=(n_species, height, width),
        chunks=(1, 50, 50),  # Chunk by species and spatial blocks
        dtype='f4'
    )
    
    # Generate test data
    np.random.seed(42)  # Reproducible tests
    
    # Species 0: Total biomass (sum of all others)
    total_biomass = np.zeros((height, width), dtype=np.float32)
    
    # Species 1-5: Individual species with different patterns
    for i in range(1, n_species):
        # Create different spatial patterns for each species
        if i == 1:  # Dominant species - widespread
            data = np.random.rand(height, width) * 50
            data[data < 10] = 0  # Some areas with no presence
        elif i == 2:  # Common species - patchy
            data = np.random.rand(height, width) * 30
            data[data < 15] = 0  # More sparse
        elif i == 3:  # Rare species - very limited
            data = np.zeros((height, width))
            # Only present in small patch
            data[40:60, 40:60] = np.random.rand(20, 20) * 20
        elif i == 4:  # Edge species - along borders
            data = np.zeros((height, width))
            data[:10, :] = np.random.rand(10, width) * 25
            data[-10:, :] = np.random.rand(10, width) * 25
        else:  # Random scattered species
            data = np.random.rand(height, width) * 15
            data[data < 12] = 0
        
        z[i] = data
        total_biomass += data
    
    # Set total biomass layer
    z[0] = total_biomass
    
    # Add metadata attributes
    z.attrs['species_codes'] = ['TOTAL', 'SP001', 'SP002', 'SP003', 'SP004', 'SP005']
    z.attrs['species_names'] = [
        'All Species Combined',
        'Dominant Oak',
        'Common Pine', 
        'Rare Maple',
        'Edge Birch',
        'Scattered Ash'
    ]
    z.attrs['description'] = 'Test biomass data for BigMap'
    z.attrs['units'] = 'Mg/ha'
    z.attrs['crs'] = 'ESRI:102039'
    z.attrs['transform'] = [-2000000, 30, 0, -900000, 0, -30]
    z.attrs['bounds'] = [-2000000, -1000000, -1900000, -900000]
    
    return z


@pytest.fixture
def sample_species_data() -> dict:
    """Sample species data for testing."""
    return {
        'species_codes': ['TOTAL', 'SP001', 'SP002', 'SP003', 'SP004', 'SP005'],
        'species_names': [
            'All Species Combined',
            'Dominant Oak',
            'Common Pine', 
            'Rare Maple',
            'Edge Birch',
            'Scattered Ash'
        ],
        'n_species': 6
    }


@pytest.fixture
def test_settings(temp_dir: Path) -> BigMapSettings:
    """Create test settings with temporary directories."""
    settings = BigMapSettings(
        data_dir=temp_dir / "data",
        output_dir=temp_dir / "output",
        cache_dir=temp_dir / "cache",
        calculations=[
            CalculationConfig(
                name="species_richness",
                enabled=True,
                parameters={"biomass_threshold": 0.0}
            ),
            CalculationConfig(
                name="total_biomass",
                enabled=True
            ),
            CalculationConfig(
                name="shannon_diversity",
                enabled=True
            ),
            CalculationConfig(
                name="dominant_species",
                enabled=False  # Disabled for testing
            )
        ]
    )
    
    # Ensure directories exist
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    
    return settings


@pytest.fixture
def empty_zarr_array(temp_dir: Path) -> zarr.Array:
    """Create an empty zarr array for edge case testing."""
    zarr_path = temp_dir / "empty_biomass.zarr"
    
    # Create empty array
    z = zarr.open_array(
        str(zarr_path),
        mode='w',
        shape=(3, 50, 50),
        chunks=(1, 50, 50),
        dtype='f4',
        fill_value=0.0
    )
    
    # All zeros
    z[:] = 0
    
    # Minimal metadata
    z.attrs['species_codes'] = ['TOTAL', 'SP001', 'SP002']
    z.attrs['species_names'] = ['All Species', 'Species 1', 'Species 2']
    z.attrs['crs'] = 'ESRI:102039'
    
    return z


@pytest.fixture
def single_species_zarr(temp_dir: Path) -> zarr.Array:
    """Create a zarr array with only one species for testing."""
    zarr_path = temp_dir / "single_species.zarr"
    
    # Single species plus total
    z = zarr.open_array(
        str(zarr_path),
        mode='w',
        shape=(2, 100, 100),
        chunks=(1, 100, 100),
        dtype='f4'
    )
    
    # Generate data
    data = np.random.rand(100, 100) * 75
    data[data < 20] = 0
    
    z[0] = data  # Total
    z[1] = data  # Single species
    
    z.attrs['species_codes'] = ['TOTAL', 'SP001']
    z.attrs['species_names'] = ['All Species Combined', 'Single Pine Species']
    z.attrs['crs'] = 'ESRI:102039'
    
    return z