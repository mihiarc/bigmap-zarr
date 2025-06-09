#!/usr/bin/env python3
"""
Script to create an expandable Zarr file from NC-clipped BIGMAP rasters for efficient processing.

This script:
1. Creates a 3D Zarr array (species, height, width) with the total biomass as the first layer
2. Sets up the array structure to allow sequential appending of individual species
3. Saves as Zarr with proper chunking and metadata for expandability
"""

import os
import json
import numpy as np
import rasterio
import zarr
import xarray as xr
from pathlib import Path
from tqdm import tqdm
import pandas as pd
from numcodecs import Blosc

def get_raster_info(raster_path):
    """Get detailed information about a raster file."""
    with rasterio.open(raster_path) as src:
        return {
            'crs': src.crs,
            'transform': src.transform,
            'bounds': src.bounds,
            'shape': src.shape,
            'dtype': src.dtypes[0],
            'nodata': src.nodata,
            'count': src.count
        }

def create_expandable_zarr_from_base_raster(raster_path, output_path="nc_biomass_expandable.zarr", chunk_size=(1, 1000, 1000)):
    """Create an expandable 3D Zarr file starting with the base total biomass raster."""
    print(f"Creating expandable Zarr from base raster: {raster_path}")
    print(f"Output: {output_path}")
    
    # Check if input file exists
    if not os.path.exists(raster_path):
        raise FileNotFoundError(f"Input raster not found: {raster_path}")
    
    # Get raster information
    raster_info = get_raster_info(raster_path)
    height, width = raster_info['shape']
    
    print(f"Raster dimensions: {height} × {width} pixels")
    print(f"Chunk size: {chunk_size}")
    print(f"Data type: {raster_info['dtype']}")
    print(f"CRS: {raster_info['crs']}")
    
    # Remove existing Zarr file if it exists
    if os.path.exists(output_path):
        print(f"Removing existing Zarr file: {output_path}")
        import shutil
        shutil.rmtree(output_path)
    
    # Read the base raster data (total biomass)
    print("Reading base raster data...")
    with rasterio.open(raster_path) as src:
        data = src.read(1)  # Read first (and only) band
        
        # Convert to float32 and handle nodata
        data = data.astype(np.float32)
        
        # Replace nodata values with 0.0
        if src.nodata is not None:
            data[data == src.nodata] = 0.0
        
        # Count valid (non-zero) pixels
        valid_pixels = np.count_nonzero(data)
        
        print(f"Valid pixels: {valid_pixels:,} ({valid_pixels / (height * width) * 100:.1f}% coverage)")
        print(f"Biomass range: {data[data > 0].min():.1f} - {data.max():.1f} Mg/ha")
        print(f"Mean biomass (valid pixels): {data[data > 0].mean():.1f} Mg/ha")
    
    # Create expandable 3D zarr array starting with 1 species (total)
    print("Creating expandable 3D Zarr array...")
    zarr_array = zarr.create_array(
        store=output_path, 
        shape=(1, height, width),  # Start with 1 species layer
        chunks=chunk_size,
        dtype=np.float32,
        compressors=zarr.codecs.BloscCodec(cname='lz4', clevel=5),
        fill_value=0.0
    )
    
    # Store the total biomass data in the first layer
    print("Writing total biomass data to first layer...")
    zarr_array[0, :, :] = data
    
    # Store metadata as attributes
    zarr_array.attrs['description'] = 'North Carolina Above Ground Biomass by Species - Expandable Stack'
    zarr_array.attrs['source'] = 'BIGMAP 2018 - Clipped to North Carolina'
    zarr_array.attrs['source_file'] = str(raster_path)
    zarr_array.attrs['units'] = 'Mg/ha'
    zarr_array.attrs['nodata'] = 'None (using 0.0 for no biomass)'
    zarr_array.attrs['creation_date'] = pd.Timestamp.now().isoformat()
    zarr_array.attrs['crs'] = str(raster_info['crs'])
    zarr_array.attrs['transform'] = list(raster_info['transform'])
    zarr_array.attrs['bounds'] = list(raster_info['bounds'])
    zarr_array.attrs['height'] = height
    zarr_array.attrs['width'] = width
    zarr_array.attrs['pixel_size_x'] = abs(raster_info['transform'][0])
    zarr_array.attrs['pixel_size_y'] = abs(raster_info['transform'][4])
    zarr_array.attrs['spatial_shape'] = [height, width]
    zarr_array.attrs['chunk_size'] = list(chunk_size)
    zarr_array.attrs['expandable'] = True
    zarr_array.attrs['species_dimension'] = 0  # First dimension is species
    
    # Initialize species tracking
    species_codes = ['TOTAL']
    species_names = ['All Species Combined']
    
    zarr_array.attrs['species_codes'] = species_codes
    zarr_array.attrs['species_names'] = species_names
    zarr_array.attrs['n_species'] = len(species_codes)
    
    # Calculate file sizes
    input_size_mb = os.path.getsize(raster_path) / (1024 * 1024)
    output_size_mb = get_folder_size(output_path)
    
    print(f"\n✅ Expandable Zarr created successfully!")
    print(f"📁 Output: {output_path}")
    print(f"📊 Initial dimensions: {zarr_array.shape}")
    print(f"💾 Input size: {input_size_mb:.1f} MB")
    print(f"💾 Compressed size: {output_size_mb:.1f} MB")
    print(f"🗜️ Compression ratio: {input_size_mb / output_size_mb:.1f}x")
    print(f"🔧 Expandable: Ready for species appending")
    
    return output_path

def append_species_to_zarr(zarr_path, species_raster_path, species_code, species_name):
    """Append a new species layer to the existing zarr array."""
    print(f"\nAppending species {species_code} ({species_name}) to {zarr_path}")
    
    # Open existing zarr array
    zarr_array = zarr.open_array(zarr_path, mode='r+')
    
    # Read the new species raster
    with rasterio.open(species_raster_path) as src:
        species_data = src.read(1).astype(np.float32)
        if src.nodata is not None:
            species_data[species_data == src.nodata] = 0.0
    
    # Verify dimensions match
    if species_data.shape != (zarr_array.shape[1], zarr_array.shape[2]):
        raise ValueError(f"Species raster dimensions {species_data.shape} don't match zarr spatial dimensions {(zarr_array.shape[1], zarr_array.shape[2])}")
    
    # Append the new layer using zarr.append()
    print(f"Current shape: {zarr_array.shape}")
    new_shape = zarr_array.append(species_data[np.newaxis, :, :], axis=0)
    print(f"New shape after append: {new_shape}")
    
    # Update metadata
    species_codes = list(zarr_array.attrs['species_codes'])
    species_names = list(zarr_array.attrs['species_names'])
    
    species_codes.append(species_code)
    species_names.append(species_name)
    
    zarr_array.attrs['species_codes'] = species_codes
    zarr_array.attrs['species_names'] = species_names
    zarr_array.attrs['n_species'] = len(species_codes)
    zarr_array.attrs['last_updated'] = pd.Timestamp.now().isoformat()
    
    valid_pixels = np.count_nonzero(species_data)
    coverage_pct = valid_pixels / (zarr_array.shape[1] * zarr_array.shape[2]) * 100
    
    print(f"✅ Successfully appended {species_code}")
    print(f"   Coverage: {coverage_pct:.2f}% ({valid_pixels:,} pixels)")
    print(f"   Mean biomass: {species_data[species_data > 0].mean():.1f} Mg/ha")
    
    return new_shape

def get_folder_size(folder_path):
    """Calculate total size of folder in MB."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            total_size += os.path.getsize(filepath)
    return total_size / (1024 * 1024)

def create_xarray_interface(zarr_path="nc_biomass_expandable.zarr"):
    """Create an xarray interface to the expandable Zarr data for easy analysis."""
    print(f"\nCreating xarray interface...")
    
    # Load zarr array
    biomass_data = zarr.open_array(zarr_path, mode='r')
    
    # Get metadata from attributes
    species_codes = biomass_data.attrs['species_codes']
    species_names = biomass_data.attrs['species_names']
    transform = biomass_data.attrs['transform']
    height = biomass_data.attrs['height']
    width = biomass_data.attrs['width']
    
    # Create coordinate arrays
    x_coords = np.array([transform[2] + i * transform[0] for i in range(width)])
    y_coords = np.array([transform[5] + i * transform[4] for i in range(height)])
    
    # Create xarray Dataset
    ds = xr.Dataset(
        {
            'biomass': (
                ['species', 'y', 'x'], 
                biomass_data[:],
                {
                    'units': 'Mg/ha',
                    'long_name': 'Above Ground Biomass by Species',
                    'description': 'Above ground biomass by tree species (expandable)'
                }
            )
        },
        coords={
            'species': (
                ['species'], 
                species_codes,
                {
                    'long_name': 'Species Code',
                    'description': 'Species identifier (TOTAL = all species combined)'
                }
            ),
            'species_name': (
                ['species'], 
                species_names,
                {
                    'long_name': 'Species Name',
                    'description': 'Common species name'
                }
            ),
            'x': (
                ['x'], 
                x_coords,
                {
                    'units': 'meters',
                    'long_name': 'Easting',
                    'crs': biomass_data.attrs['crs']
                }
            ),
            'y': (
                ['y'], 
                y_coords,
                {
                    'units': 'meters', 
                    'long_name': 'Northing',
                    'crs': biomass_data.attrs['crs']
                }
            )
        },
        attrs={
            'title': 'North Carolina Above Ground Biomass by Species (Expandable)',
            'source': 'BIGMAP 2018',
            'crs': biomass_data.attrs['crs'],
            'creation_date': biomass_data.attrs['creation_date'],
            'expandable': True
        }
    )
    
    return ds

def demo_analysis(zarr_path="nc_biomass_expandable.zarr"):
    """Demonstrate analysis capabilities with the expandable zarr."""
    print(f"\n🔬 Demonstrating analysis capabilities...")
    
    # Load with xarray
    ds = create_xarray_interface(zarr_path)
    
    print(f"Dataset overview:")
    print(f"  Species: {len(ds.species)} ({', '.join(ds.species.values[:3])}{'...' if len(ds.species) > 3 else ''})")
    print(f"  Spatial extent: {len(ds.y)} × {len(ds.x)} pixels")
    print(f"  Total pixels: {len(ds.y) * len(ds.x):,}")
    
    # Calculate total biomass (first layer = total)
    total_biomass = ds.biomass.isel(species=0)
    valid_pixels = (total_biomass > 0).sum().values
    
    print(f"\nSummary statistics:")
    print(f"  Forest pixels: {valid_pixels:,}")
    print(f"  Forest coverage: {(valid_pixels / (len(ds.y) * len(ds.x))) * 100:.1f}%")
    print(f"  Total biomass range: {total_biomass.min().values:.1f} - {total_biomass.max().values:.1f} Mg/ha")
    print(f"  Mean biomass (forest pixels): {total_biomass.where(total_biomass > 0).mean(skipna=True).values:.1f} Mg/ha")
    print(f"  Total NC biomass: {total_biomass.sum().values / 1e6:.1f} million Mg")
    
    # Show species-level info if we have more than just total
    if len(ds.species) > 1:
        print(f"\nSpecies breakdown:")
        for i, species in enumerate(ds.species.values):
            if i == 0:  # Skip total for individual species analysis
                continue
            species_data = ds.biomass.isel(species=i)
            valid_count = (species_data > 0).sum().values
            coverage_pct = (valid_count / (len(ds.y) * len(ds.x))) * 100
            mean_biomass = species_data.where(species_data > 0).mean(skipna=True).values
            
            print(f"  {species} ({ds.species_name.values[i]}): {coverage_pct:.2f}% coverage, {mean_biomass:.1f} Mg/ha mean")
    
    return ds

def main():
    """Main processing function."""
    print("=== Creating Expandable NC Biomass Zarr ===\n")
    
    # Specify the input raster path (total biomass)
    base_raster_path = "nc_clipped_rasters/nc_clipped_Hosted_AGB_0000_2018_TOTAL_11172024101136.tif"
    output_path = "nc_biomass_expandable.zarr"
    
    # Check if input file exists
    if not os.path.exists(base_raster_path):
        print(f"❌ Input raster not found: {base_raster_path}")
        print("Available files in nc_clipped_rasters/:")
        nc_dir = Path("nc_clipped_rasters")
        if nc_dir.exists():
            for f in nc_dir.glob("*.tif"):
                print(f"  {f.name}")
        return
    
    # Create expandable Zarr with base total biomass
    zarr_path = create_expandable_zarr_from_base_raster(base_raster_path, output_path)
    
    # Demonstrate analysis capabilities
    ds = demo_analysis(zarr_path)
    
    print(f"\n🎯 Usage Examples:")
    print(f"  # Load in Python:")
    print(f"  import zarr, xarray as xr")
    print(f"  biomass = zarr.open('{zarr_path}')")
    print(f"  ds = xr.open_zarr('{zarr_path}')")
    print(f"  ")
    print(f"  # Access total biomass (first layer):")
    print(f"  total_biomass = ds.biomass.isel(species=0)")
    print(f"  ")
    print(f"  # Append new species:")
    print(f"  from {__file__} import append_species_to_zarr")
    print(f"  append_species_to_zarr('{zarr_path}', 'species_file.tif', 'SPCD0012', 'Oak')")
    print(f"  ")
    print(f"  # Calculate species ratios:")
    print(f"  total = ds.biomass.isel(species=0)")
    print(f"  oak = ds.biomass.isel(species=1)")
    print(f"  oak_ratio = oak / total")
    print(f"  ")
    print(f"  # Regional analysis:")
    print(f"  coastal = ds.sel(x=slice(2000000, 2200000))")
    print(f"  mountains = ds.sel(x=slice(1500000, 1800000))")

if __name__ == "__main__":
    main() 