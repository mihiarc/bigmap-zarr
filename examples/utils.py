#!/usr/bin/env python3
"""
Shared utilities for BigMap examples.

This module contains common functions used across multiple examples
to avoid code duplication.
"""

from pathlib import Path
import numpy as np
import zarr
import rasterio
from typing import List, Optional, Dict, Any
from rich.console import Console

console = Console()


def create_zarr_from_rasters(
    raster_dir: Path,
    output_path: Path,
    chunk_size: tuple = (1, 1000, 1000)
) -> Path:
    """
    Create a zarr array from species raster files.

    Args:
        raster_dir: Directory containing GeoTIFF files
        output_path: Output path for zarr array
        chunk_size: Chunk dimensions for zarr array

    Returns:
        Path to created zarr array
    """
    raster_files = sorted(Path(raster_dir).glob("*.tif"))
    console.print(f"Found {len(raster_files)} species rasters")

    if not raster_files:
        raise ValueError(f"No .tif files found in {raster_dir}")

    # Read first raster for dimensions and metadata
    with rasterio.open(raster_files[0]) as src:
        height, width = src.shape
        transform = src.transform
        crs = src.crs
        bounds = src.bounds

    # Create zarr array with total + species layers
    n_layers = len(raster_files) + 1  # +1 for total biomass
    z = zarr.open_array(
        str(output_path),
        mode='w',
        shape=(n_layers, height, width),
        chunks=chunk_size,
        dtype='f4'
    )

    # Load species data and calculate total
    total_biomass = np.zeros((height, width), dtype=np.float32)
    species_codes = ['TOTAL']
    species_names = ['All Species Combined']

    for i, raster_file in enumerate(raster_files, 1):
        console.print(f"  Loading {raster_file.name}...")
        with rasterio.open(raster_file) as src:
            data = src.read(1).astype(np.float32)
            z[i] = data
            total_biomass += data

            # Extract species info from filename
            species_codes.append(raster_file.stem)
            species_names.append(raster_file.stem)

    # Store total biomass
    z[0] = total_biomass

    # Add metadata
    add_zarr_metadata(z, species_codes, species_names, crs, transform, bounds)

    console.print(f"✅ Created zarr array: {output_path}")
    console.print(f"   Shape: {z.shape}, Chunks: {chunk_size}")

    return output_path


def add_zarr_metadata(
    zarr_array: zarr.Array,
    species_codes: List[str],
    species_names: List[str],
    crs: Any,
    transform: Any,
    bounds: Any
) -> None:
    """Add standard metadata to a zarr array."""
    zarr_array.attrs.update({
        'species_codes': species_codes,
        'species_names': species_names,
        'crs': str(crs),
        'transform': list(transform) if hasattr(transform, '__iter__') else transform,
        'bounds': list(bounds) if hasattr(bounds, '__iter__') else bounds,
        'units': 'Mg/ha',
        'description': 'Forest biomass by species from USDA FIA BIGMAP'
    })


def create_sample_zarr(output_path: Path, n_species: int = 3) -> Path:
    """
    Create a small sample zarr array for testing.

    Args:
        output_path: Output path for zarr array
        n_species: Number of species to simulate

    Returns:
        Path to created zarr array
    """
    console.print(f"Creating sample zarr with {n_species} species...")

    # Create zarr array
    z = zarr.open_array(
        str(output_path),
        mode='w',
        shape=(n_species + 1, 100, 100),  # +1 for total
        chunks=(1, 100, 100),
        dtype='f4'
    )

    # Generate sample data
    np.random.seed(42)
    total = np.zeros((100, 100), dtype=np.float32)
    species_codes = ['TOTAL']
    species_names = ['All Species Combined']

    for i in range(n_species):
        # Create realistic-looking biomass pattern
        data = np.random.rand(100, 100) * (50 - i * 10)
        data[data < 15] = 0  # Add zeros for non-forest areas
        z[i + 1] = data
        total += data

        species_codes.append(f'SP{i+1:03d}')
        species_names.append(f'Species {i+1}')

    z[0] = total

    # Add metadata
    z.attrs.update({
        'species_codes': species_codes,
        'species_names': species_names,
        'crs': 'EPSG:3857',
        'units': 'Mg/ha',
        'description': 'Sample forest biomass data for testing'
    })

    console.print(f"✅ Created sample zarr: {output_path}")
    return output_path


def setup_visualization(style: str = 'seaborn-v0_8-darkgrid') -> None:
    """Setup matplotlib for consistent visualization style."""
    import matplotlib.pyplot as plt

    try:
        plt.style.use(style)
    except:
        # Fallback if style not available
        plt.rcParams['figure.figsize'] = (12, 8)
        plt.rcParams['font.size'] = 10
        plt.rcParams['axes.labelsize'] = 12
        plt.rcParams['axes.titlesize'] = 14
        plt.rcParams['xtick.labelsize'] = 10
        plt.rcParams['ytick.labelsize'] = 10
        plt.rcParams['legend.fontsize'] = 10


def print_zarr_info(zarr_path: Path) -> Dict[str, Any]:
    """Print information about a zarr array."""
    z = zarr.open_array(str(zarr_path), mode='r')

    info = {
        'shape': z.shape,
        'chunks': z.chunks,
        'dtype': str(z.dtype),
        'size_mb': z.nbytes / 1024 / 1024,
        'species_codes': z.attrs.get('species_codes', []),
        'species_names': z.attrs.get('species_names', []),
        'crs': z.attrs.get('crs', 'Unknown')
    }

    console.print(f"\n[bold]Zarr Array Information:[/bold]")
    console.print(f"  Path: {zarr_path}")
    console.print(f"  Shape: {info['shape']}")
    console.print(f"  Chunks: {info['chunks']}")
    console.print(f"  Data type: {info['dtype']}")
    console.print(f"  Size: {info['size_mb']:.1f} MB")
    console.print(f"  Species: {len(info['species_codes']) - 1}")  # -1 for TOTAL
    console.print(f"  CRS: {info['crs']}")

    return info


def calculate_basic_stats(zarr_path: Path, sample_size: Optional[int] = 1000) -> Dict[str, Any]:
    """Calculate basic statistics from a zarr array."""
    z = zarr.open_array(str(zarr_path), mode='r')

    # Sample data if specified
    if sample_size and z.shape[1] > sample_size:
        data = z[:, :sample_size, :sample_size]
        console.print(f"Sampling {sample_size}x{sample_size} pixels for statistics")
    else:
        data = z[:]

    # Calculate stats
    total_biomass = data[0]
    forest_mask = total_biomass > 0
    forest_pixels = np.sum(forest_mask)

    stats = {
        'total_pixels': total_biomass.size,
        'forest_pixels': int(forest_pixels),
        'forest_coverage_pct': 100 * forest_pixels / total_biomass.size,
        'mean_biomass': float(np.mean(total_biomass[forest_mask])) if forest_pixels > 0 else 0,
        'max_biomass': float(np.max(total_biomass)) if forest_pixels > 0 else 0,
        'total_biomass_mg': float(np.sum(total_biomass))
    }

    # Species richness
    species_present = np.sum(data[1:] > 0, axis=0)  # Skip TOTAL layer
    stats['mean_richness'] = float(np.mean(species_present[forest_mask])) if forest_pixels > 0 else 0
    stats['max_richness'] = int(np.max(species_present)) if forest_pixels > 0 else 0

    return stats