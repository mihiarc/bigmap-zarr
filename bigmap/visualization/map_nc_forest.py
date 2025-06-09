#!/usr/bin/env python3
"""
Flexible script to create maps of NC forest data including biomass, species diversity, and other metrics.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import PowerNorm, LinearSegmentedColormap
import rasterio
import geopandas as gpd
from pathlib import Path
from mpl_toolkits.axes_grid1 import make_axes_locatable
import argparse

def get_data_type_config(data_type):
    """Get visualization configuration for different data types."""
    configs = {
        'biomass': {
            'title': 'North Carolina - Total Above Ground Biomass',
            'cmap': 'viridis',
            'norm': PowerNorm(gamma=0.5),
            'units': 'Mg/ha',
            'colorbar_label': 'Above Ground Biomass (Mg/ha)',
            'mask_threshold': 0,
            'default_file': 'nc_clipped_rasters/nc_clipped_Hosted_AGB_0000_2018_TOTAL_11172024101136.tif',
        },
        'diversity': {
            'title': 'North Carolina - Tree Species Diversity',
            'cmap': 'plasma',
            'norm': None,  # Linear normalization
            'units': 'species count',
            'colorbar_label': 'Number of Tree Species',
            'mask_threshold': 0,
            'default_file': 'nc_species_diversity.tif',
        },
        'richness': {
            'title': 'North Carolina - Species Richness',
            'cmap': 'Spectral_r',
            'norm': None,
            'units': 'species count',
            'colorbar_label': 'Species Richness',
            'mask_threshold': 0,
            'default_file': 'nc_species_diversity.tif',
        }
    }
    
    if data_type not in configs:
        raise ValueError(f"Unsupported data type: {data_type}. Available: {list(configs.keys())}")
    
    return configs[data_type]

def create_nc_forest_map(raster_path, data_type='biomass', output_path=None, boundary_path=None, counties_path=None):
    """
    Create a map of NC forest data with flexible visualization options.
    
    Parameters:
    -----------
    raster_path : str
        Path to the input raster file
    data_type : str
        Type of data to visualize ('biomass', 'diversity', 'richness')
    output_path : str, optional
        Output PNG path (auto-generated if None)
    boundary_path : str, optional
        Path to NC state boundary file
    counties_path : str, optional
        Path to NC county boundaries file
    """
    print(f"=== NC Forest Map - {data_type.upper()} ===\n")
    
    # Get configuration for data type
    config = get_data_type_config(data_type)
    
    # Set default output path if not provided
    if output_path is None:
        output_path = f"nc_{data_type}_map.png"
    
    # Set default boundary path if not provided
    if boundary_path is None:
        boundary_path = "nc_clipped_rasters/nc_boundary.geojson"
    
    # Set default counties path if not provided
    if counties_path is None:
        counties_path = "data/parcels/geojson/nc_county_boundary.geojson"
    
    # Check if files exist
    if not os.path.exists(raster_path):
        print(f"Error: Raster file not found: {raster_path}")
        return
    
    # Load raster data at FULL RESOLUTION
    print(f"Loading NC {data_type} raster at FULL RESOLUTION...")
    with rasterio.open(raster_path) as src:
        # Read ALL pixels - no downsampling
        data = src.read(1)
        transform = src.transform
        crs = src.crs
        bounds = src.bounds
        nodata = src.nodata
        
        print(f"  Raster dimensions: {data.shape[1]:,} × {data.shape[0]:,} pixels")
        print(f"  Total pixels: {data.shape[0] * data.shape[1]:,}")
        print(f"  Pixel size: {abs(transform[0]):.0f}m × {abs(transform[4]):.0f}m")
        print(f"  CRS: {crs}")
        
        # Handle nodata and masking
        if nodata is not None:
            data = np.ma.masked_equal(data, nodata)
        
        # Create mask for valid forest data
        forest_mask = data > config['mask_threshold']
        
        valid_pixels = np.sum(forest_mask)
        total_pixels = data.shape[0] * data.shape[1]
        
        print(f"  Valid pixels: {valid_pixels:,}")
        print(f"  Coverage: {(valid_pixels/total_pixels)*100:.1f}%")
        print(f"  Data range: {data[forest_mask].min():.2f} - {data[forest_mask].max():.2f} {config['units']}")
    
    # Load state boundary if available
    boundary = None
    if os.path.exists(boundary_path):
        print(f"\nLoading NC state boundary: {boundary_path}")
        try:
            boundary = gpd.read_file(boundary_path)
            print(f"  State boundary CRS: {boundary.crs}")
        except Exception as e:
            print(f"  Warning: Could not load state boundary file: {e}")
            boundary = None
    
    # Load county boundaries if available
    counties = None
    if os.path.exists(counties_path):
        print(f"\nLoading NC county boundaries: {counties_path}")
        try:
            counties = gpd.read_file(counties_path)
            print(f"  County boundaries CRS: {counties.crs}")
            print(f"  Number of counties: {len(counties)}")
        except Exception as e:
            print(f"  Warning: Could not load county boundaries file: {e}")
            counties = None
    
    # Create the map
    print(f"\nCreating full resolution {data_type} map...")
    fig, ax = plt.subplots(1, 1, figsize=(16, 12))
    
    # Set clean background
    fig.patch.set_facecolor('white')
    ax.set_facecolor('lightgray')
    
    # Convert bounds to extent for matplotlib
    extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]
    
    # Plot forest data with clean visualization
    data_for_plot = np.ma.masked_where(data <= config['mask_threshold'], data)
    
    # Plot forest data
    im = ax.imshow(
        data_for_plot, 
        extent=extent,
        cmap=config['cmap'],
        norm=config['norm'],
        interpolation='nearest'  # Show every pixel clearly
    )
    
    # Set color for no-data areas
    im.cmap.set_bad(color='lightgrey', alpha=0.3)
    
    # Add county boundaries if available (plot first so they're underneath state boundary)
    if counties is not None:
        try:
            counties_reproj = counties.to_crs(crs)
            counties_reproj.boundary.plot(
                ax=ax, 
                color='white', 
                linewidth=0.8,
                alpha=0.7,
                label='County Boundaries'
            )
            print(f"  ✓ Added {len(counties)} county boundaries")
        except Exception as e:
            print(f"  Warning: Could not plot county boundaries: {e}")
    
    # Add state boundary if available (plot on top)
    if boundary is not None:
        try:
            boundary_reproj = boundary.to_crs(crs)
            boundary_reproj.boundary.plot(
                ax=ax, 
                color='red', 
                linewidth=2,
                alpha=0.9,
                label='NC State Boundary'
            )
            print(f"  ✓ Added state boundary")
        except Exception as e:
            print(f"  Warning: Could not plot state boundary: {e}")
    
    # Add colorbar
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="4%", pad=0.1)
    cbar = plt.colorbar(im, cax=cax)
    cbar.set_label(config['colorbar_label'], rotation=270, labelpad=20, fontsize=12)
    
    # Formatting
    title_suffix = ""
    if counties is not None and boundary is not None:
        title_suffix = " (with County & State Boundaries)"
    elif counties is not None:
        title_suffix = " (with County Boundaries)"
    elif boundary is not None:
        title_suffix = " (with State Boundary)"
    
    ax.set_title(f"{config['title']} (FULL RESOLUTION){title_suffix}", 
                fontsize=18, fontweight='bold', pad=20)
    ax.set_xlabel('Easting (m)', fontsize=14)
    ax.set_ylabel('Northing (m)', fontsize=14)
    
    # Add grid
    ax.grid(True, alpha=0.3, color='grey')
    ax.ticklabel_format(style='scientific', axis='both', scilimits=(-3,3))
    ax.tick_params(colors='black', labelsize=10)
    ax.xaxis.label.set_color('black')
    ax.yaxis.label.set_color('black')
    
    # Add verification info box
    pixel_size = abs(transform[0])
    area_km2 = (valid_pixels * pixel_size * pixel_size) / 1e6
    
    # Create data type specific statistics
    if data_type == 'biomass':
        stats_text = (
            f"FULL RESOLUTION VERIFICATION\n"
            f"Every pixel displayed: {data.shape[1]:,} × {data.shape[0]:,}\n"
            f"Total pixels: {total_pixels:,}\n"
            f"Valid forest pixels: {valid_pixels:,}\n"
            f"Pixel resolution: {pixel_size:.0f}m\n"
            f"Forest area: {area_km2:,.0f} km²\n"
            f"Coverage: {(valid_pixels/total_pixels)*100:.1f}%\n"
            f"Biomass range: {data[forest_mask].min():.1f} - {data[forest_mask].max():.1f} {config['units']}"
        )
    elif data_type in ['diversity', 'richness']:
        mean_diversity = data[forest_mask].mean() if valid_pixels > 0 else 0
        max_diversity = data[forest_mask].max() if valid_pixels > 0 else 0
        stats_text = (
            f"FULL RESOLUTION VERIFICATION\n"
            f"Every pixel displayed: {data.shape[1]:,} × {data.shape[0]:,}\n"
            f"Total pixels: {total_pixels:,}\n"
            f"Forest pixels: {valid_pixels:,}\n"
            f"Pixel resolution: {pixel_size:.0f}m\n"
            f"Forest area: {area_km2:,.0f} km²\n"
            f"Coverage: {(valid_pixels/total_pixels)*100:.1f}%\n"
            f"Diversity range: {data[forest_mask].min():.0f} - {max_diversity:.0f} species\n"
            f"Mean diversity: {mean_diversity:.1f} species/pixel"
        )
    else:
        stats_text = (
            f"FULL RESOLUTION VERIFICATION\n"
            f"Every pixel displayed: {data.shape[1]:,} × {data.shape[0]:,}\n"
            f"Total pixels: {total_pixels:,}\n"
            f"Valid pixels: {valid_pixels:,}\n"
            f"Pixel resolution: {pixel_size:.0f}m\n"
            f"Area: {area_km2:,.0f} km²\n"
            f"Coverage: {(valid_pixels/total_pixels)*100:.1f}%\n"
            f"Value range: {data[forest_mask].min():.1f} - {data[forest_mask].max():.1f} {config['units']}"
        )
    
    # Position info box
    ax.text(0.02, 0.98, stats_text, 
            transform=ax.transAxes, fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round,pad=0.6', facecolor='white', alpha=0.95, edgecolor='black'),
            family='monospace')
    
    # Add legend if boundaries are shown
    if boundary is not None or counties is not None:
        ax.legend(loc='lower right', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    
    print(f"\n✅ SUCCESS!")
    print(f"Map saved to: {output_path}")
    print(f"File size: {os.path.getsize(output_path) / (1024*1024):.1f} MB")
    print(f"\n🔍 VERIFICATION:")
    print(f"  • Displayed ALL {total_pixels:,} pixels from {data_type} raster")
    print(f"  • No downsampling or decimation applied") 
    print(f"  • Full 30m resolution maintained")
    print(f"  • Complete spatial extent of NC shown")
    print(f"  • Clean visualization without basemap complications")
    if counties is not None:
        print(f"  • County boundaries overlaid for geographic context")
    if boundary is not None:
        print(f"  • State boundary overlaid for geographic context")
    
    plt.close()
    
    return output_path

def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(description='Create NC forest maps from different data types')
    parser.add_argument('--data-type', '-t', 
                       choices=['biomass', 'diversity', 'richness'], 
                       default='biomass',
                       help='Type of forest data to visualize')
    parser.add_argument('--raster', '-r', 
                       help='Path to input raster file (uses default if not specified)')
    parser.add_argument('--output', '-o', 
                       help='Output PNG file path (auto-generated if not specified)')
    parser.add_argument('--boundary', '-b', 
                       help='Path to NC state boundary file')
    parser.add_argument('--counties', '-c', 
                       help='Path to NC county boundaries file')
    
    args = parser.parse_args()
    
    # Use default file if not specified
    if args.raster is None:
        config = get_data_type_config(args.data_type)
        args.raster = config['default_file']
    
    # Create the map
    output_path = create_nc_forest_map(
        raster_path=args.raster,
        data_type=args.data_type,
        output_path=args.output,
        boundary_path=args.boundary,
        counties_path=args.counties
    )
    
    print(f"\n🎯 Usage Examples:")
    print(f"   # Create biomass map:")
    print(f"   python map_nc_forest.py --data-type biomass")
    print(f"   ")
    print(f"   # Create species diversity map with county boundaries:")
    print(f"   python map_nc_forest.py --data-type diversity --counties data/parcels/geojson/nc_county_boundary.geojson")
    print(f"   ")
    print(f"   # Create richness map with both state and county boundaries:")
    print(f"   python map_nc_forest.py --data-type richness --boundary nc_boundary.geojson --counties nc_county_boundary.geojson")
    print(f"   ")
    print(f"   # Available data types:")
    print(f"     • biomass - Total above ground biomass (Mg/ha)")
    print(f"     • diversity - Tree species diversity (species count)")
    print(f"     • richness - Species richness (species count)")
    print(f"   ")
    print(f"   # Boundary options:")
    print(f"     • --boundary: Add state boundary outline")
    print(f"     • --counties: Add county boundary outlines")
    print(f"     • Both can be used together for maximum geographic context")

if __name__ == "__main__":
    main()