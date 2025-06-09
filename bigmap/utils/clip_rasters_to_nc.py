#!/usr/bin/env python3
"""
Script to clip BIGMAP rasters to North Carolina state boundary.

This script:
1. Loads the US county shapefile
2. Filters for North Carolina counties
3. Creates a dissolved state boundary 
4. Saves the boundary as GeoJSON
5. Clips each raster to the NC boundary with proper CRS handling
"""

import os
import json
import geopandas as gpd
import rasterio
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
import numpy as np
from pathlib import Path
import math

def load_nc_counties():
    """Load and filter county shapefile for North Carolina."""
    print("Loading county shapefile...")
    counties = gpd.read_file("tl_2024_us_county/tl_2024_us_county.shp")
    
    print(f"Total counties loaded: {len(counties)}")
    print(f"County shapefile CRS: {counties.crs}")
    
    # Filter for North Carolina (STATEFP = '37')
    nc_counties = counties[counties['STATEFP'] == '37'].copy()
    print(f"North Carolina counties found: {len(nc_counties)}")
    
    if len(nc_counties) == 0:
        print("Available state codes:")
        print(counties['STATEFP'].value_counts().head(10))
        raise ValueError("No North Carolina counties found. Check STATEFP codes.")
    
    return nc_counties

def create_nc_boundary(nc_counties):
    """Create North Carolina state boundary by dissolving counties."""
    print("Creating North Carolina state boundary...")
    
    # Dissolve all NC counties into a single state boundary
    nc_boundary = nc_counties.dissolve()
    
    # Reset index to make it a proper geodataframe
    nc_boundary = nc_boundary.reset_index(drop=True)
    
    print(f"NC boundary CRS: {nc_boundary.crs}")
    print(f"NC boundary geometry type: {nc_boundary.geometry.iloc[0].geom_type}")
    
    return nc_boundary

def save_boundary_geojson(nc_boundary, output_path="nc_boundary.geojson"):
    """Save the NC boundary as GeoJSON."""
    print(f"Saving boundary to {output_path}...")
    
    # Convert to WGS84 for GeoJSON standard
    nc_boundary_wgs84 = nc_boundary.to_crs("EPSG:4326")
    nc_boundary_wgs84.to_file(output_path, driver="GeoJSON")
    
    print(f"Boundary saved to {output_path}")
    return output_path

def get_raster_info(raster_path):
    """Get basic information about a raster file."""
    with rasterio.open(raster_path) as src:
        return {
            'crs': src.crs,
            'bounds': src.bounds,
            'shape': src.shape,
            'dtype': src.dtypes[0],
            'nodata': src.nodata,
            'count': src.count
        }

def get_target_extent_and_transform(boundary_gdf, target_crs, pixel_size=30):
    """Calculate target extent and transform for consistent output dimensions."""
    # Reproject boundary to target CRS
    boundary_reproj = boundary_gdf.to_crs(target_crs)
    
    # Get bounds
    bounds = boundary_reproj.total_bounds
    minx, miny, maxx, maxy = bounds
    
    # Calculate grid-aligned bounds (snap to pixel grid)
    # Expand outward to ensure full coverage - fix western edge issue
    buffer = pixel_size * 3  # Increase buffer to 3 pixels for safety
    
    # For western (minx) edge, extend by additional 100m as requested
    western_extension = 100.0  # Additional 100 meter extension for western edge
    
    # For western (minx) and southern (miny) edges, we need to go MORE negative/smaller
    # Use floor operation to ensure we capture the full extent
    minx = math.floor(minx / pixel_size) * pixel_size - buffer - western_extension
    miny = math.floor(miny / pixel_size) * pixel_size - buffer
    
    # For eastern (maxx) and northern (maxy) edges, we need to go MORE positive/larger
    # Use ceil operation to ensure we capture the full extent  
    maxx = math.ceil(maxx / pixel_size) * pixel_size + buffer
    maxy = math.ceil(maxy / pixel_size) * pixel_size + buffer
    
    # Calculate dimensions
    width = int((maxx - minx) / pixel_size)
    height = int((maxy - miny) / pixel_size)
    
    # Create transform
    from rasterio.transform import from_bounds
    transform = from_bounds(minx, miny, maxx, maxy, width, height)
    
    print(f"  Enhanced target extent calculation:")
    print(f"    Original bounds: ({bounds[0]:.1f}, {bounds[1]:.1f}, {bounds[2]:.1f}, {bounds[3]:.1f})")
    print(f"    Grid-aligned bounds: ({minx:.1f}, {miny:.1f}, {maxx:.1f}, {maxy:.1f})")
    print(f"    Expansion: {buffer}m buffer + {western_extension}m western extension + grid alignment")
    
    return {
        'bounds': (minx, miny, maxx, maxy),
        'transform': transform,
        'width': width,
        'height': height
    }

def clip_raster_to_boundary(raster_path, boundary_gdf, output_path, target_extent=None):
    """Clip a raster to the boundary with consistent output dimensions."""
    print(f"\nProcessing: {raster_path}")
    
    # Get raster info
    raster_info = get_raster_info(raster_path)
    print(f"  Raster CRS: {raster_info['crs']}")
    print(f"  Raster shape: {raster_info['shape']}")
    print(f"  Raster bounds: {raster_info['bounds']}")
    
    with rasterio.open(raster_path) as src:
        # Reproject boundary to match raster CRS
        boundary_reproj = boundary_gdf.to_crs(src.crs)
        print(f"  Boundary reprojected to: {boundary_reproj.crs}")
        
        # If no target extent provided, calculate it from the boundary
        if target_extent is None:
            pixel_size = abs(src.transform[0])  # Get pixel size from source
            target_extent = get_target_extent_and_transform(boundary_gdf, src.crs, pixel_size)
        
        print(f"  Target dimensions: {target_extent['height']} × {target_extent['width']}")
        print(f"  Target bounds: {target_extent['bounds']}")
        
        # Convert boundary to geometry for masking
        boundary_geom = boundary_reproj.geometry.values
        
        # Read and reproject data to target grid
        print("  Reprojecting to target grid...")
        try:
            from rasterio.warp import reproject, Resampling
            import numpy as np
            
            # Create output array initialized with zeros
            out_data = np.zeros(
                (src.count, target_extent['height'], target_extent['width']), 
                dtype=np.float32  # Use float32 for biomass data
            )
            
            # Reproject source data to target grid
            reproject(
                source=rasterio.band(src, list(range(1, src.count + 1))),
                destination=out_data,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=target_extent['transform'],
                dst_crs=src.crs,
                resampling=Resampling.nearest,
                src_nodata=src.nodata,
                dst_nodata=0  # Use 0 as destination nodata
            )
            
            # Apply boundary mask
            print("  Applying boundary mask...")
            from rasterio.features import geometry_mask
            
            # Create mask from boundary geometry
            mask = geometry_mask(
                boundary_geom,
                transform=target_extent['transform'],
                invert=True,  # True inside boundary
                out_shape=(target_extent['height'], target_extent['width'])
            )
            
            # Apply mask to data - set areas outside NC boundary to 0
            for band in range(out_data.shape[0]):
                out_data[band][~mask] = 0.0
                
                # Also replace any nodata values with 0
                if src.nodata is not None:
                    out_data[band][out_data[band] == src.nodata] = 0.0
            
            # Update metadata
            out_meta = src.meta.copy()
            out_meta.update({
                "driver": "GTiff",
                "height": target_extent['height'],
                "width": target_extent['width'],
                "transform": target_extent['transform'],
                "dtype": np.float32,
                "nodata": None,  # No nodata value since we use 0
                "compress": "lzw"  # Add compression to reduce file size
            })
            
            # Write clipped raster
            print(f"  Writing clipped raster to: {output_path}")
            with rasterio.open(output_path, "w", **out_meta) as dest:
                dest.write(out_data)
            
            print(f"  ✓ Successfully clipped to {output_path}")
            print(f"  Output shape: {out_data.shape}")
            
            # Report statistics
            total_pixels = out_data.size
            nonzero_pixels = np.count_nonzero(out_data)
            print(f"  Non-zero pixels: {nonzero_pixels:,} ({(nonzero_pixels/total_pixels)*100:.1f}%)")
            
        except Exception as e:
            print(f"  ✗ Error clipping raster: {e}")
            raise

def discover_rasters(input_dir):
    """Discover all BIGMAP raster files in the input directory."""
    print(f"Scanning for rasters in: {input_dir}")
    
    raster_files = []
    input_path = Path(input_dir)
    
    if not input_path.exists():
        print(f"Error: Input directory not found: {input_dir}")
        return []
    
    # Look for directories matching BIGMAP pattern
    for species_dir in input_path.glob("BIGMAP_AGB_2018_SPCD*"):
        if species_dir.is_dir():
            # Look for .tif files in each species directory
            tif_files = list(species_dir.glob("*.tif"))
            
            if tif_files:
                # Take the first (and usually only) .tif file
                raster_file = tif_files[0]
                species_code = species_dir.name.split('_')[3]  # Extract SPCD code
                species_name = species_dir.name.split('_', 4)[4] if len(species_dir.name.split('_')) > 4 else species_code
                
                raster_files.append({
                    'path': str(raster_file),
                    'species_code': species_code,
                    'species_name': species_name,
                    'dir_name': species_dir.name
                })
                
                print(f"  Found: {species_code} - {species_name}")
    
    print(f"Total rasters discovered: {len(raster_files)}")
    return raster_files

def check_already_processed(raster_info, output_dir):
    """Check if a raster has already been processed."""
    raster_name = Path(raster_info['path']).stem
    output_file = output_dir / f"nc_clipped_{raster_name}.tif"
    
    if output_file.exists():
        # Check if output file is newer than input file
        input_mtime = os.path.getmtime(raster_info['path'])
        output_mtime = os.path.getmtime(output_file)
        
        if output_mtime > input_mtime:
            return True, "Already processed (up to date)"
        else:
            return False, "Output exists but is older than input"
    
    return False, "Not processed yet"

def main():
    """Main processing function."""
    print("=== BIGMAP Batch Raster Clipping to North Carolina (Fixed Extent) ===\n")
    
    # Define input directory
    input_dir = "/home/mihiarc/BIGMAP"
    
    # Create output directory
    output_dir = Path("nc_clipped_rasters")
    output_dir.mkdir(exist_ok=True)
    print(f"Output directory: {output_dir}")
    
    # Step 1: Load NC counties and create boundary (only once)
    print("\n--- Creating North Carolina Boundary ---")
    nc_counties = load_nc_counties()
    nc_boundary = create_nc_boundary(nc_counties)
    
    # Step 2: Save boundary as GeoJSON (only once)
    boundary_geojson = save_boundary_geojson(nc_boundary, output_dir / "nc_boundary.geojson")
    
    # Step 3: Calculate target extent once for all rasters
    print("\n--- Calculating Target Extent ---")
    # Use ESRI:102039 (common projection for BIGMAP rasters)
    target_crs = "ESRI:102039"
    target_extent = get_target_extent_and_transform(nc_boundary, target_crs, pixel_size=30)
    print(f"Target extent: {target_extent['bounds']}")
    print(f"Target dimensions: {target_extent['height']} × {target_extent['width']}")
    
    # Step 4: Discover all rasters
    print("\n--- Discovering Rasters ---")
    raster_files = discover_rasters(input_dir)
    
    if not raster_files:
        print("No raster files found. Exiting.")
        return
    
    # Step 5: Process each raster (with skip logic)
    print(f"\n--- Processing {len(raster_files)} Rasters ---")
    
    processed_count = 0
    skipped_count = 0
    error_count = 0
    
    for i, raster_info in enumerate(raster_files, 1):
        raster_path = raster_info['path']
        species_code = raster_info['species_code']
        species_name = raster_info['species_name']
        
        print(f"\n[{i}/{len(raster_files)}] {species_code} - {species_name}")
        print(f"  File: {raster_path}")
        
        # Check if file exists
        if not os.path.exists(raster_path):
            print(f"  ❌ SKIP: File not found")
            error_count += 1
            continue
        
        # Check if already processed
        already_processed, reason = check_already_processed(raster_info, output_dir)
        if already_processed:
            print(f"  ⏭️  SKIP: {reason}")
            skipped_count += 1
            continue
        
        # Generate output filename
        raster_name = Path(raster_path).stem
        output_path = output_dir / f"nc_clipped_{raster_name}.tif"
        
        print(f"  🔄 PROCESSING...")
        
        try:
            # Get file size for progress indication
            file_size_gb = os.path.getsize(raster_path) / (1024**3)
            print(f"  📁 Input file size: {file_size_gb:.1f} GB")
            
            clip_raster_to_boundary(raster_path, nc_boundary, output_path, target_extent)
            print(f"  ✅ SUCCESS: Clipped to {output_path}")
            processed_count += 1
            
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            error_count += 1
            # Remove partial output file if it exists
            if output_path.exists():
                output_path.unlink()
                print(f"  🧹 Cleaned up partial file")
    
    # Final summary
    print(f"\n=== Batch Processing Complete ===")
    print(f"📊 SUMMARY:")
    print(f"  • Total rasters found: {len(raster_files)}")
    print(f"  • Successfully processed: {processed_count}")
    print(f"  • Skipped (already done): {skipped_count}")
    print(f"  • Errors: {error_count}")
    print(f"  • Output directory: {output_dir}")
    print(f"  • North Carolina boundary: {boundary_geojson}")
    print(f"  • Target dimensions: {target_extent['height']} × {target_extent['width']}")
    
    if processed_count > 0:
        print(f"\n✨ {processed_count} new rasters clipped to North Carolina with consistent dimensions!")
    
    if error_count > 0:
        print(f"\n⚠️  {error_count} rasters had errors and may need manual attention.")

if __name__ == "__main__":
    main() 