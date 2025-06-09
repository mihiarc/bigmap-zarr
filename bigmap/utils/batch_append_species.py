#!/usr/bin/env python3
"""
Batch script to append all species to the expandable NC biomass zarr.

This script:
1. Discovers all species raster files in nc_clipped_rasters/
2. Extracts species information from filenames
3. Sequentially appends each species to the zarr
4. Provides progress tracking and error handling
"""

import os
import sys
from pathlib import Path
import zarr
import xarray as xr
from tqdm import tqdm
import time

# Import the append function from our main script
from bigmap.utils.create_nc_biomass_zarr import append_species_to_zarr, create_xarray_interface

def extract_species_info_from_filename(filename):
    """Extract species code and name from the BIGMAP filename format."""
    # Expected format: nc_clipped_Hosted_AGB_XXXX_2018_SPECIES_NAME_timestamp.tif
    # Example: nc_clipped_Hosted_AGB_0067_2018_SOUTHERN_REDCEDAR_06142023183600.tif
    
    stem = Path(filename).stem
    parts = stem.split('_')
    
    # Find the AGB and species code parts
    spcd_code = None
    species_name_parts = []
    
    for i, part in enumerate(parts):
        if part == "AGB" and i + 1 < len(parts):
            spcd_code = parts[i + 1]
            # Get species name parts (everything between year and timestamp)
            # Skip: nc, clipped, Hosted, AGB, XXXX, 2018, then collect until timestamp
            if i + 3 < len(parts):  # Skip year (2018)
                # Collect parts until we hit what looks like a timestamp
                for j in range(i + 3, len(parts)):
                    if len(parts[j]) > 10 and parts[j].isdigit():  # Timestamp detection
                        break
                    species_name_parts.append(parts[j])
            break
    
    if spcd_code and species_name_parts:
        species_name = " ".join(species_name_parts).title()
        return f"SPCD{spcd_code}", species_name
    else:
        raise ValueError(f"Could not parse species info from filename: {filename}")

def discover_species_rasters(input_dir="nc_clipped_rasters"):
    """Discover all species raster files, excluding the TOTAL file."""
    print(f"🔍 Discovering species rasters in: {input_dir}")
    
    species_files = []
    input_path = Path(input_dir)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Directory not found: {input_dir}")
    
    # Find all clipped raster files
    for raster_file in input_path.glob("nc_clipped_*.tif"):
        if raster_file.is_file():
            filename = raster_file.name
            
            # Skip the TOTAL file (already used as base)
            if "TOTAL" in filename:
                print(f"  ⏭️  Skipping TOTAL file: {filename}")
                continue
            
            try:
                species_code, species_name = extract_species_info_from_filename(filename)
                file_size_mb = raster_file.stat().st_size / (1024 * 1024)
                
                species_files.append({
                    'path': str(raster_file),
                    'filename': filename,
                    'species_code': species_code,
                    'species_name': species_name,
                    'file_size_mb': file_size_mb
                })
                print(f"  ✓ {species_code}: {species_name} ({file_size_mb:.1f} MB)")
            except ValueError as e:
                print(f"  ⚠️  Could not parse: {filename} - {e}")
    
    # Sort by species code for consistent ordering
    species_files.sort(key=lambda x: x['species_code'])
    
    print(f"\n📊 Found {len(species_files)} species files to process")
    return species_files

def batch_append_species():
    """Batch append all species to the zarr."""
    
    # File paths
    zarr_path = "nc_biomass_expandable.zarr"
    input_dir = "nc_clipped_rasters"
    
    print("=== Batch Appending Species to NC Biomass Zarr ===\n")
    
    # Check if zarr exists
    if not os.path.exists(zarr_path):
        print(f"❌ Zarr file not found: {zarr_path}")
        print("Please run create_nc_biomass_zarr.py first to create the base zarr.")
        return
    
    # Show initial zarr state
    print(f"📊 Initial zarr state:")
    zarr_array = zarr.open_array(zarr_path, mode='r')
    initial_species = zarr_array.attrs['species_codes']
    print(f"   Shape: {zarr_array.shape}")
    print(f"   Existing species: {initial_species}")
    print()
    
    # Discover species files
    try:
        species_files = discover_species_rasters(input_dir)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return
    
    if not species_files:
        print("❌ No species files found to process.")
        return
    
    # Check which species are already in the zarr
    existing_species = set(zarr_array.attrs['species_codes'])
    species_to_process = []
    
    for species_info in species_files:
        if species_info['species_code'] in existing_species:
            print(f"  ⏭️  Skipping {species_info['species_code']} (already in zarr)")
        else:
            species_to_process.append(species_info)
    
    if not species_to_process:
        print("✅ All species are already in the zarr. Nothing to process.")
        return
    
    print(f"\n🚀 Processing {len(species_to_process)} new species...")
    
    # Track processing statistics
    successful_appends = 0
    failed_appends = 0
    start_time = time.time()
    
    # Process each species with progress bar
    for i, species_info in enumerate(tqdm(species_to_process, desc="Appending species")):
        species_path = species_info['path']
        species_code = species_info['species_code']
        species_name = species_info['species_name']
        
        print(f"\n[{i+1}/{len(species_to_process)}] Processing {species_code}: {species_name}")
        print(f"   File: {Path(species_path).name}")
        print(f"   Size: {species_info['file_size_mb']:.1f} MB")
        
        try:
            # Append the species
            new_shape = append_species_to_zarr(zarr_path, species_path, species_code, species_name)
            successful_appends += 1
            print(f"   ✅ Success! New shape: {new_shape}")
            
        except Exception as e:
            failed_appends += 1
            print(f"   ❌ Failed: {e}")
            
            # Log error for debugging
            with open("append_errors.log", "a") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {species_code} ({species_name}): {e}\n")
    
    # Final summary
    elapsed_time = time.time() - start_time
    
    print(f"\n" + "="*60)
    print(f"📈 BATCH PROCESSING COMPLETE")
    print(f"="*60)
    print(f"⏱️  Total time: {elapsed_time:.1f} seconds")
    print(f"✅ Successful appends: {successful_appends}")
    print(f"❌ Failed appends: {failed_appends}")
    print(f"📊 Success rate: {successful_appends/(successful_appends+failed_appends)*100:.1f}%")
    
    # Show final zarr state
    zarr_array = zarr.open_array(zarr_path, mode='r')
    final_species = zarr_array.attrs['species_codes']
    
    print(f"\n📊 Final zarr state:")
    print(f"   Shape: {zarr_array.shape}")
    print(f"   Total species: {len(final_species)}")
    print(f"   Species added: {len(final_species) - len(initial_species)}")
    
    # Show species summary
    if len(final_species) <= 10:
        print(f"\n📋 All species in zarr:")
        for i, (code, name) in enumerate(zip(zarr_array.attrs['species_codes'], zarr_array.attrs['species_names'])):
            print(f"   {i}: {code} - {name}")
    else:
        print(f"\n📋 First 5 and last 5 species:")
        species_codes = zarr_array.attrs['species_codes']
        species_names = zarr_array.attrs['species_names']
        for i in range(5):
            print(f"   {i}: {species_codes[i]} - {species_names[i]}")
        print(f"   ...")
        for i in range(len(species_codes)-5, len(species_codes)):
            print(f"   {i}: {species_codes[i]} - {species_names[i]}")
    
    # Calculate storage efficiency
    total_input_size = sum([s['file_size_mb'] for s in species_files])
    zarr_size = get_folder_size(zarr_path)
    
    print(f"\n💾 Storage summary:")
    print(f"   Total input size: {total_input_size:.1f} MB")
    print(f"   Zarr compressed size: {zarr_size:.1f} MB")
    print(f"   Compression ratio: {total_input_size/zarr_size:.1f}x")
    
    if failed_appends > 0:
        print(f"\n⚠️  Check 'append_errors.log' for details on failed appends.")
    
    print(f"\n🎯 Next steps:")
    print(f"   # Load the complete zarr:")
    print(f"   ds = xr.open_zarr('{zarr_path}')")
    print(f"   total = ds.biomass.isel(species=0)")
    print(f"   species_ratios = ds.biomass / total")
    print(f"   ")
    print(f"   # Analyze species diversity:")
    print(f"   species_coverage = (ds.biomass > 0).sum(['y', 'x'])")
    print(f"   dominant_species = ds.biomass.argmax('species')")

def get_folder_size(folder_path):
    """Calculate total size of folder in MB."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            total_size += os.path.getsize(filepath)
    return total_size / (1024 * 1024)

if __name__ == "__main__":
    batch_append_species() 