"""
Command Line Interface for BigMap package.

This module provides command-line tools for common BigMap operations.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

import click
import xarray as xr
from rich.console import Console
from rich.table import Table

from bigmap import __version__
from bigmap.core.analyze_species_presence import analyze_species_presence
from bigmap.core.create_species_diversity_map import main as diversity_main
from bigmap.utils.batch_append_species import batch_append_species
from bigmap.utils.clip_rasters_to_nc import main as clip_main
from bigmap.utils.create_nc_biomass_zarr import main as zarr_main
from bigmap.visualization.map_nc_forest import main as map_main

from ..console import print_success, print_error, print_info, create_species_table, display_configuration
from ..config import load_settings
from ..api import BigMapRestClient

console = Console()

# Create main CLI group
@click.group()
@click.version_option(version=__version__)
def bigmap_cli():
    """BigMap: North Carolina Forest Biomass and Species Diversity Analysis Tools."""
    pass


def analyze() -> None:
    """CLI entry point for bigmap-analyze command."""
    parser = argparse.ArgumentParser(
        description="Analyze species presence and biomass data",
        prog="bigmap-analyze"
    )
    
    parser.add_argument(
        "--version", 
        action="version", 
        version=f"%(prog)s {__version__}"
    )
    
    parser.add_argument(
        "--zarr-path",
        "-z",
        default="nc_biomass_expandable.zarr",
        help="Path to the zarr array file (default: nc_biomass_expandable.zarr)"
    )
    
    parser.add_argument(
        "--output-dir",
        "-o",
        default="output",
        help="Output directory for analysis results (default: output)"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    try:
        print(f"BigMap Analyzer v{__version__}")
        print(f"Analyzing data from: {args.zarr_path}")
        
        # Create output directory if it doesn't exist
        Path(args.output_dir).mkdir(exist_ok=True, parents=True)
        
        # Run species presence analysis
        analyze_species_presence()
        
        # Run diversity analysis
        diversity_main()
        
        print(f"\n✅ Analysis complete! Results saved to {args.output_dir}/")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}", file=sys.stderr)
        sys.exit(1)


def visualize() -> None:
    """CLI entry point for bigmap-visualize command."""
    parser = argparse.ArgumentParser(
        description="Create visualizations and maps from BigMap data",
        prog="bigmap-visualize"
    )
    
    parser.add_argument(
        "--version", 
        action="version", 
        version=f"%(prog)s {__version__}"
    )
    
    parser.add_argument(
        "--data-type",
        "-t",
        choices=["biomass", "diversity", "richness"],
        default="biomass",
        help="Type of data to visualize (default: biomass)"
    )
    
    parser.add_argument(
        "--raster",
        "-r",
        help="Path to input raster file"
    )
    
    parser.add_argument(
        "--output",
        "-o",
        help="Output file path for the visualization"
    )
    
    parser.add_argument(
        "--boundary",
        "-b",
        help="Path to boundary file (GeoJSON)"
    )
    
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="Output resolution in DPI (default: 300)"
    )
    
    args = parser.parse_args()
    
    try:
        print(f"BigMap Visualizer v{__version__}")
        print(f"Creating {args.data_type} visualization...")
        
        # Import and run visualization
        from bigmap.visualization.map_nc_forest import create_nc_forest_map, get_data_type_config
        
        # Use default raster if not specified
        if args.raster is None:
            config = get_data_type_config(args.data_type)
            args.raster = config['default_file']
        
        # Create the map
        output_path = create_nc_forest_map(
            raster_path=args.raster,
            data_type=args.data_type,
            output_path=args.output,
            boundary_path=args.boundary
        )
        
        print(f"✅ Visualization saved to: {output_path}")
        
    except Exception as e:
        print(f"❌ Error during visualization: {e}", file=sys.stderr)
        sys.exit(1)


def process() -> None:
    """CLI entry point for bigmap-process command."""
    parser = argparse.ArgumentParser(
        description="Process and prepare BigMap data",
        prog="bigmap-process"
    )
    
    parser.add_argument(
        "--version", 
        action="version", 
        version=f"%(prog)s {__version__}"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Processing commands")
    
    # Clip command
    clip_parser = subparsers.add_parser("clip", help="Clip rasters to North Carolina")
    clip_parser.add_argument(
        "--input-dir",
        "-i",
        required=True,
        help="Input directory containing BIGMAP rasters"
    )
    clip_parser.add_argument(
        "--output-dir",
        "-o",
        default="nc_clipped_rasters",
        help="Output directory for clipped rasters"
    )
    clip_parser.add_argument(
        "--boundary",
        "-b",
        help="Path to NC boundary file"
    )
    
    # Zarr command
    zarr_parser = subparsers.add_parser("zarr", help="Create Zarr array from rasters")
    zarr_parser.add_argument(
        "--base-raster",
        "-r",
        required=True,
        help="Base raster file (typically total biomass)"
    )
    zarr_parser.add_argument(
        "--output",
        "-o",
        default="nc_biomass_expandable.zarr",
        help="Output Zarr file path"
    )
    
    # Append command
    append_parser = subparsers.add_parser("append", help="Append species to existing Zarr")
    append_parser.add_argument(
        "--zarr-path",
        "-z",
        default="nc_biomass_expandable.zarr",
        help="Path to existing Zarr array"
    )
    append_parser.add_argument(
        "--input-dir",
        "-i",
        default="nc_clipped_rasters",
        help="Directory containing species rasters"
    )
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return
    
    try:
        print(f"BigMap Processor v{__version__}")
        
        if args.command == "clip":
            print(f"Clipping rasters from {args.input_dir} to {args.output_dir}")
            clip_main()
            
        elif args.command == "zarr":
            print(f"Creating Zarr array from {args.base_raster}")
            zarr_main()
            
        elif args.command == "append":
            print(f"Appending species to {args.zarr_path}")
            batch_append_species()
        
        print("✅ Processing complete!")
        
    except Exception as e:
        print(f"❌ Error during processing: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="BigMap: North Carolina Forest Analysis Tools",
        prog="bigmap"
    )
    
    parser.add_argument(
        "--version", 
        action="version", 
        version=f"%(prog)s {__version__}"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Add subcommands
    subparsers.add_parser("analyze", help="Run analysis workflows")
    subparsers.add_parser("visualize", help="Create visualizations")
    subparsers.add_parser("process", help="Process and prepare data")
    
    args = parser.parse_args()
    
    if args.command == "analyze":
        analyze()
    elif args.command == "visualize":
        visualize()
    elif args.command == "process":
        process()
    else:
        parser.print_help()


@bigmap_cli.command("list-api-species")
def list_api_species():
    """List all available species from the REST API."""
    print_info("Connecting to FIA BIGMAP ImageServer...")
    
    client = BigMapRestClient()
    species_list = client.list_available_species()
    
    if species_list:
        print_success(f"Found {len(species_list)} species available via REST API")
        
        # Create Rich table
        table = Table(title="Available Species from FIA BIGMAP REST API")
        table.add_column("Species Code", style="cyan")
        table.add_column("Common Name", style="green")
        table.add_column("Scientific Name", style="yellow")
        
        for species in species_list[:20]:  # Show first 20
            table.add_row(
                species['species_code'],
                species['common_name'],
                species['scientific_name']
            )
        
        console.print(table)
        
        if len(species_list) > 20:
            print_info(f"Showing first 20 of {len(species_list)} species. Use --export to get full list.")
    else:
        print_error("Failed to retrieve species list from REST API")


@bigmap_cli.command("download-species-api")
@click.option('--species-codes', '-s', multiple=True, help='Species codes to download (e.g., 0131, 0068)')
@click.option('--output-dir', '-o', type=click.Path(), default='data/rest_api_downloads', help='Output directory')
@click.option('--bbox', '-b', help='Bounding box as "xmin,ymin,xmax,ymax" in Web Mercator')
def download_species_api(species_codes, output_dir, bbox):
    """Download species data via REST API."""
    from pathlib import Path
    
    config = load_settings()
    output_path = Path(output_dir)
    
    # Use NC bbox if not provided
    if not bbox:
        # North Carolina bounds in Web Mercator (approximate)
        nc_bbox = (-9200000, 4000000, -8400000, 4400000)
        print_info(f"Using default North Carolina bounding box: {nc_bbox}")
    else:
        try:
            coords = [float(x.strip()) for x in bbox.split(',')]
            if len(coords) != 4:
                raise ValueError("Bbox must have 4 coordinates")
            nc_bbox = tuple(coords)
        except ValueError as e:
            print_error(f"Invalid bbox format: {e}")
            return
    
    client = BigMapRestClient()
    
    if not species_codes:
        print_info("No species codes specified. Getting top 10 NC species...")
        # Default to top NC species
        species_codes = ['0131', '0068', '0132', '0110', '0316', '0762', '0833', '0318', '0621', '0802']
    
    print_info(f"Downloading {len(species_codes)} species to {output_path}")
    
    exported_files = client.batch_export_nc_species(
        nc_bbox=nc_bbox,
        output_dir=output_path,
        species_codes=list(species_codes)
    )
    
    if exported_files:
        print_success(f"Successfully downloaded {len(exported_files)} species rasters")
        for file_path in exported_files:
            print_info(f"  - {file_path}")
    else:
        print_error("Failed to download any species data")


@bigmap_cli.command("identify-point")
@click.option('--species-code', '-s', required=True, help='Species code (e.g., 0131)')
@click.option('--x', type=float, required=True, help='X coordinate (Web Mercator)')
@click.option('--y', type=float, required=True, help='Y coordinate (Web Mercator)')
def identify_point(species_code, x, y):
    """Get biomass value for a species at a specific point."""
    client = BigMapRestClient()
    
    print_info(f"Identifying biomass for species {species_code} at ({x}, {y})")
    
    value = client.identify_pixel_value(species_code, x, y)
    
    if value is not None:
        print_success(f"Biomass value: {value:.2f} tons/acre")
    else:
        print_error("Failed to identify pixel value")


@bigmap_cli.command("species-stats")
@click.option('--species-code', '-s', required=True, help='Species code (e.g., 0131)')
def species_stats(species_code):
    """Get statistics for a species across the entire dataset."""
    client = BigMapRestClient()
    
    print_info(f"Getting statistics for species {species_code}")
    
    stats = client.get_species_statistics(species_code)
    
    if stats:
        # Display statistics in a nice format
        table = Table(title=f"Statistics for Species {species_code}")
        table.add_column("Statistic", style="cyan")
        table.add_column("Value", style="green")
        
        for key, value in stats.items():
            if isinstance(value, (int, float)):
                table.add_row(str(key), f"{value:.4f}")
            else:
                table.add_row(str(key), str(value))
        
        console.print(table)
    else:
        print_error("Failed to get statistics")


if __name__ == "__main__":
    main()