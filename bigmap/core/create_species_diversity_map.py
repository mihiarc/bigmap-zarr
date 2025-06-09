#!/usr/bin/env python3
"""
Script to create a species diversity map from the NC biomass zarr.

This script:
1. Reads the 3D zarr array (species, height, width)
2. Counts the number of species with biomass > 0 at each pixel
3. Creates a 2D species diversity map
4. Saves as a GeoTIFF with proper spatial reference
"""

import os
import numpy as np
import zarr
import xarray as xr
import rasterio
from rasterio.transform import from_bounds
from pathlib import Path
import time
from tqdm import tqdm

def calculate_species_diversity_chunked(zarr_path="nc_biomass_expandable.zarr", chunk_size=1000):
    """
    Calculate species diversity by counting non-zero species per pixel using chunked processing.
    
    Parameters:
    -----------
    zarr_path : str
        Path to the zarr array
    chunk_size : int
        Size of spatial chunks to process at once for memory efficiency
        
    Returns:
    --------
    numpy.ndarray
        2D array of species counts per pixel
    """
    print(f"🔍 Opening zarr array: {zarr_path}")
    
    # Open zarr array in read-only mode
    biomass_zarr = zarr.open_array(zarr_path, mode='r')
    
    print(f"📊 Zarr array info:")
    print(f"   Shape: {biomass_zarr.shape}")
    print(f"   Species: {biomass_zarr.attrs['n_species']}")
    print(f"   Data type: {biomass_zarr.dtype}")
    
    n_species, height, width = biomass_zarr.shape
    
    # Initialize diversity array
    diversity_map = np.zeros((height, width), dtype=np.uint8)
    
    print(f"\n🧮 Calculating species diversity using chunked processing...")
    print(f"   Chunk size: {chunk_size} × {chunk_size}")
    
    # Calculate number of chunks
    n_chunks_y = (height + chunk_size - 1) // chunk_size
    n_chunks_x = (width + chunk_size - 1) // chunk_size
    total_chunks = n_chunks_y * n_chunks_x
    
    print(f"   Total chunks to process: {total_chunks}")
    
    # Process in chunks to manage memory
    start_time = time.time()
    
    with tqdm(total=total_chunks, desc="Processing chunks") as pbar:
        for y_chunk in range(n_chunks_y):
            for x_chunk in range(n_chunks_x):
                # Calculate chunk boundaries
                y_start = y_chunk * chunk_size
                y_end = min((y_chunk + 1) * chunk_size, height)
                x_start = x_chunk * chunk_size
                x_end = min((x_chunk + 1) * chunk_size, width)
                
                # Read chunk data for all species
                # Shape: (n_species, chunk_height, chunk_width)
                chunk_data = biomass_zarr[:, y_start:y_end, x_start:x_end]
                
                # Count non-zero species per pixel in this chunk
                # Use axis=0 to count along species dimension
                species_count = np.count_nonzero(chunk_data > 0, axis=0)
                
                # Store result in diversity map
                diversity_map[y_start:y_end, x_start:x_end] = species_count.astype(np.uint8)
                
                pbar.update(1)
    
    elapsed_time = time.time() - start_time
    print(f"✅ Species diversity calculation complete in {elapsed_time:.1f} seconds")
    
    return diversity_map, biomass_zarr.attrs

def save_diversity_geotiff(diversity_map, zarr_attrs, output_path="nc_species_diversity.tif"):
    """
    Save the diversity map as a GeoTIFF with proper spatial reference.
    
    Parameters:
    -----------
    diversity_map : numpy.ndarray
        2D array of species counts
    zarr_attrs : dict
        Zarr attributes containing spatial reference info
    output_path : str
        Output GeoTIFF path
    """
    print(f"\n💾 Saving diversity map as GeoTIFF: {output_path}")
    
    # Extract spatial reference from zarr attributes
    height, width = diversity_map.shape
    transform_list = zarr_attrs['transform']
    bounds = zarr_attrs['bounds']
    crs = zarr_attrs['crs']
    
    # Create rasterio transform from bounds
    transform = from_bounds(bounds[0], bounds[1], bounds[2], bounds[3], width, height)
    
    # Define output metadata
    profile = {
        'driver': 'GTiff',
        'dtype': diversity_map.dtype,
        'nodata': 0,
        'width': width,
        'height': height,
        'count': 1,
        'crs': crs,
        'transform': transform,
        'compress': 'lzw',
        'tiled': True,
        'blockxsize': 512,
        'blockysize': 512
    }
    
    # Write GeoTIFF
    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(diversity_map, 1)
        
        # Add metadata
        dst.update_tags(
            DESCRIPTION='Species diversity map - Count of tree species per pixel',
            SOURCE='BIGMAP 2018 North Carolina Above Ground Biomass',
            CREATION_DATE=time.strftime('%Y-%m-%d %H:%M:%S'),
            UNITS='Count (number of species)',
            NO_DATA_VALUE='0'
        )
    
    print(f"✅ GeoTIFF saved successfully")
    
    # Report file size
    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"   File size: {file_size_mb:.1f} MB")

def analyze_diversity_results(diversity_map, zarr_attrs):
    """
    Analyze and report diversity map statistics.
    
    Parameters:
    -----------
    diversity_map : numpy.ndarray
        2D array of species counts
    zarr_attrs : dict
        Zarr attributes
    """
    print(f"\n📈 Species Diversity Analysis:")
    
    # Basic statistics
    total_pixels = diversity_map.size
    forest_pixels = np.count_nonzero(diversity_map > 0)
    non_forest_pixels = total_pixels - forest_pixels
    
    print(f"   Total pixels: {total_pixels:,}")
    print(f"   Forest pixels: {forest_pixels:,} ({forest_pixels/total_pixels*100:.1f}%)")
    print(f"   Non-forest pixels: {non_forest_pixels:,} ({non_forest_pixels/total_pixels*100:.1f}%)")
    
    if forest_pixels > 0:
        forest_diversity = diversity_map[diversity_map > 0]
        
        print(f"\n   Species diversity statistics (forest pixels only):")
        print(f"     Min species per pixel: {forest_diversity.min()}")
        print(f"     Max species per pixel: {forest_diversity.max()}")
        print(f"     Mean species per pixel: {forest_diversity.mean():.2f}")
        print(f"     Median species per pixel: {np.median(forest_diversity):.1f}")
        
        # Diversity distribution
        print(f"\n   Diversity distribution:")
        unique_counts, frequencies = np.unique(forest_diversity, return_counts=True)
        
        for count, freq in zip(unique_counts[:10], frequencies[:10]):  # Show first 10
            pct = freq / forest_pixels * 100
            print(f"     {count} species: {freq:,} pixels ({pct:.1f}%)")
        
        if len(unique_counts) > 10:
            print(f"     ... and {len(unique_counts) - 10} more diversity levels")
        
        # High diversity areas
        high_diversity_threshold = np.percentile(forest_diversity, 95)
        high_diversity_pixels = np.count_nonzero(forest_diversity >= high_diversity_threshold)
        
        print(f"\n   High diversity areas (≥{high_diversity_threshold:.0f} species):")
        print(f"     Pixels: {high_diversity_pixels:,} ({high_diversity_pixels/forest_pixels*100:.1f}% of forest)")
        
        # Species information
        species_codes = zarr_attrs.get('species_codes', [])
        species_names = zarr_attrs.get('species_names', [])
        
        print(f"\n   Available species in dataset:")
        print(f"     Total species: {len(species_codes)}")
        if len(species_codes) <= 10:
            for i, (code, name) in enumerate(zip(species_codes, species_names)):
                print(f"     {i}: {code} - {name}")
        else:
            for i in range(5):
                print(f"     {i}: {species_codes[i]} - {species_names[i]}")
            print(f"     ...")
            for i in range(len(species_codes)-3, len(species_codes)):
                print(f"     {i}: {species_codes[i]} - {species_names[i]}")

def create_xarray_interface(diversity_map, zarr_attrs, output_path="nc_species_diversity.zarr"):
    """
    Create an xarray interface for the diversity map and optionally save as zarr.
    
    Parameters:
    -----------
    diversity_map : numpy.ndarray
        2D diversity map
    zarr_attrs : dict
        Spatial reference attributes
    output_path : str, optional
        Path to save diversity zarr
        
    Returns:
    --------
    xarray.Dataset
        Dataset with diversity map and coordinates
    """
    print(f"\n🗺️ Creating xarray interface...")
    
    # Extract spatial info
    transform_list = zarr_attrs['transform']
    height, width = diversity_map.shape
    
    # Create coordinate arrays
    x_coords = np.array([transform_list[2] + i * transform_list[0] for i in range(width)])
    y_coords = np.array([transform_list[5] + i * transform_list[4] for i in range(height)])
    
    # Create xarray Dataset
    ds = xr.Dataset(
        {
            'species_diversity': (
                ['y', 'x'],
                diversity_map,
                {
                    'units': 'count',
                    'long_name': 'Number of Tree Species',
                    'description': 'Count of tree species with biomass > 0 per pixel'
                }
            )
        },
        coords={
            'x': (
                ['x'],
                x_coords,
                {
                    'units': 'meters',
                    'long_name': 'Easting',
                    'crs': zarr_attrs['crs']
                }
            ),
            'y': (
                ['y'],
                y_coords,
                {
                    'units': 'meters',
                    'long_name': 'Northing', 
                    'crs': zarr_attrs['crs']
                }
            )
        },
        attrs={
            'title': 'North Carolina Tree Species Diversity Map',
            'source': 'BIGMAP 2018 - Species diversity derived from biomass data',
            'crs': zarr_attrs['crs'],
            'creation_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'description': 'Number of tree species with above-ground biomass > 0 per 30m pixel'
        }
    )
    
    print(f"   Dataset shape: {ds.species_diversity.shape}")
    print(f"   Coordinate system: {zarr_attrs['crs']}")
    
    # Optionally save as zarr
    if output_path:
        print(f"   Saving as zarr: {output_path}")
        ds.to_zarr(output_path, mode='w')
        zarr_size_mb = get_folder_size(output_path)
        print(f"   Zarr size: {zarr_size_mb:.1f} MB")
    
    return ds

def get_folder_size(folder_path):
    """Calculate total size of folder in MB."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                total_size += os.path.getsize(filepath)
            except (OSError, IOError):
                pass
    return total_size / (1024 * 1024)

def main():
    """Main processing function."""
    print("=== Creating NC Species Diversity Map ===\n")
    
    # Input/output paths
    zarr_path = "output/nc_biomass_expandable.zarr"
    geotiff_path = "output/nc_species_diversity.tif"
    diversity_zarr_path = "output/nc_species_diversity.zarr"
    
    # Check if input zarr exists
    if not os.path.exists(zarr_path):
        print(f"❌ Input zarr not found: {zarr_path}")
        print("Please run create_nc_biomass_zarr.py and batch_append_species.py first.")
        return
    
    # Step 1: Calculate species diversity
    diversity_map, zarr_attrs = calculate_species_diversity_chunked(zarr_path, chunk_size=1000)
    
    # Step 2: Analyze results
    analyze_diversity_results(diversity_map, zarr_attrs)
    
    # Step 3: Save as GeoTIFF
    save_diversity_geotiff(diversity_map, zarr_attrs, geotiff_path)
    
    # Step 4: Create xarray interface and save as zarr
    ds = create_xarray_interface(diversity_map, zarr_attrs, diversity_zarr_path)
    
    print(f"\n🎯 Usage Examples:")
    print(f"   # Load diversity GeoTIFF:")
    print(f"   import rasterio")
    print(f"   with rasterio.open('{geotiff_path}') as src:")
    print(f"       diversity = src.read(1)")
    print(f"   ")
    print(f"   # Load diversity xarray:")
    print(f"   import xarray as xr")
    print(f"   ds = xr.open_zarr('{diversity_zarr_path}')")
    print(f"   diversity = ds.species_diversity")
    print(f"   ")
    print(f"   # Analyze high diversity areas:")
    print(f"   high_diversity = diversity > 5  # Areas with >5 species")
    print(f"   plt.imshow(high_diversity, cmap='viridis')")
    print(f"   ")
    print(f"   # Calculate diversity statistics by region:")
    print(f"   coastal = ds.sel(x=slice(2000000, 2200000))")
    print(f"   mountain = ds.sel(x=slice(1500000, 1800000))")

if __name__ == "__main__":
    main() 