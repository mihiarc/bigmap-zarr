#!/usr/bin/env python3
"""
Analyze which species actually have biomass data in North Carolina.

This script examines each species layer in the zarr array and reports:
- Which species have non-zero biomass pixels
- Coverage statistics for each species
- Summary of species presence in NC
"""

import zarr
import numpy as np
from pathlib import Path

def analyze_species_presence():
    """Analyze species presence in North Carolina zarr data."""
    
    zarr_path = "nc_biomass_expandable.zarr"
    
    print("=== Analyzing Species Presence in North Carolina ===\n")
    
    # Load zarr array
    if not Path(zarr_path).exists():
        print(f"❌ Zarr file not found: {zarr_path}")
        return
    
    zarr_array = zarr.open_array(zarr_path, mode='r')
    species_codes = zarr_array.attrs['species_codes']
    species_names = zarr_array.attrs['species_names']
    
    print(f"📊 Total species in zarr: {len(species_codes)}")
    print(f"📊 Zarr shape: {zarr_array.shape}")
    print(f"📊 Total pixels per species: {zarr_array.shape[1] * zarr_array.shape[2]:,}")
    print()
    
    # Analyze each species
    species_with_data = []
    species_without_data = []
    
    print("🔍 Analyzing each species layer...")
    print("="*80)
    
    for i, (code, name) in enumerate(zip(species_codes, species_names)):
        print(f"Processing {i+1}/{len(species_codes)}: {code}", end=" ... ")
        
        # Load species data
        data = zarr_array[i]
        
        # Calculate statistics
        nonzero_pixels = np.count_nonzero(data)
        total_pixels = data.size
        coverage_pct = (nonzero_pixels / total_pixels) * 100
        
        if nonzero_pixels > 0:
            # Calculate additional stats for species with data
            nonzero_data = data[data > 0]
            mean_biomass = nonzero_data.mean()
            max_biomass = nonzero_data.max()
            
            species_with_data.append({
                'index': i,
                'code': code,
                'name': name,
                'pixels': nonzero_pixels,
                'coverage_pct': coverage_pct,
                'mean_biomass': mean_biomass,
                'max_biomass': max_biomass
            })
            print(f"✅ {nonzero_pixels:,} pixels ({coverage_pct:.3f}%)")
        else:
            species_without_data.append({
                'index': i,
                'code': code,
                'name': name
            })
            print("❌ No data")
    
    print("="*80)
    print()
    
    # Summary statistics
    print("📈 SUMMARY STATISTICS")
    print("="*50)
    print(f"Species with biomass data: {len(species_with_data):2d} ({len(species_with_data)/len(species_codes)*100:.1f}%)")
    print(f"Species without data:      {len(species_without_data):2d} ({len(species_without_data)/len(species_codes)*100:.1f}%)")
    print()
    
    # Species WITH data (sorted by coverage)
    if species_with_data:
        print("🌲 SPECIES WITH BIOMASS DATA IN NORTH CAROLINA")
        print("="*80)
        species_with_data.sort(key=lambda x: x['coverage_pct'], reverse=True)
        
        print(f"{'#':>2} {'Code':>8} {'Coverage':>10} {'Pixels':>12} {'Mean':>8} {'Max':>8} Species Name")
        print("-" * 80)
        
        for i, species in enumerate(species_with_data, 1):
            print(f"{i:2d} {species['code']:>8} {species['coverage_pct']:>9.3f}% "
                  f"{species['pixels']:>11,} {species['mean_biomass']:>7.1f} "
                  f"{species['max_biomass']:>7.1f} {species['name']}")
    
    print()
    
    # Species WITHOUT data
    if species_without_data:
        print("🚫 SPECIES WITHOUT BIOMASS DATA IN NORTH CAROLINA")
        print("="*80)
        print("These species likely don't naturally occur in North Carolina:")
        print()
        
        for i, species in enumerate(species_without_data, 1):
            print(f"{i:2d}. {species['code']}: {species['name']}")
    
    print()
    
    # Top species by coverage
    if len(species_with_data) > 0:
        print("🏆 TOP 10 SPECIES BY COVERAGE")
        print("="*50)
        for i, species in enumerate(species_with_data[:10], 1):
            print(f"{i:2d}. {species['name']} ({species['code']}) - {species['coverage_pct']:.3f}%")
    
    # Summary for next steps
    print()
    print("🎯 NEXT STEPS")
    print("="*30)
    print(f"• Use species indices 0-{len(species_with_data)-1} for analysis of NC forest species")
    print(f"• Total forest coverage: {species_with_data[0]['coverage_pct']:.1f}% of NC land area")
    print(f"• Most common species: {species_with_data[1]['name']} ({species_with_data[1]['coverage_pct']:.3f}%)")
    print(f"• Zarr file size: {get_folder_size(zarr_path):.1f} MB")

def get_folder_size(folder_path):
    """Calculate total size of folder in MB."""
    import os
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            total_size += os.path.getsize(filepath)
    return total_size / (1024 * 1024)

if __name__ == "__main__":
    analyze_species_presence() 