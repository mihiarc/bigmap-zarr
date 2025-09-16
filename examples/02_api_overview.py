#!/usr/bin/env python3
"""
BigMap API Overview

Demonstrates all major API features and patterns.
Each example is self-contained and can be run independently.
"""

from pathlib import Path
from bigmap import BigMapAPI
from bigmap.config import BigMapSettings, CalculationConfig
from bigmap.examples import create_sample_zarr, print_zarr_info
from examples.common_locations import get_location_bbox, COUNTIES, STATES


def example_1_list_species():
    """List all available species in the BIGMAP dataset."""
    print("\n" + "=" * 60)
    print("Example 1: List Available Species")
    print("=" * 60)

    api = BigMapAPI()
    species = api.list_species()

    print(f"Total species available: {len(species)}")
    print("\nFirst 5 species:")
    for s in species[:5]:
        print(f"  {s.species_code}: {s.common_name} ({s.scientific_name})")

    # Find specific species
    pine_species = [s for s in species if "pine" in s.common_name.lower()]
    print(f"\nFound {len(pine_species)} pine species")


def example_2_location_config():
    """Demonstrate using predefined location bounding boxes."""
    print("\n" + "=" * 60)
    print("Example 2: Location Configurations")
    print("=" * 60)

    # Using predefined bounding boxes to avoid external dependencies
    print("Using predefined bounding boxes (no external downloads required)")

    # County example - using predefined bbox
    harris_bbox, harris_crs = get_location_bbox("harris_tx")
    print(f"\nCounty: Harris County, Texas")
    print(f"  Bbox: {harris_bbox}")
    print(f"  CRS: {harris_crs}")
    if "harris_tx" in COUNTIES:
        print(f"  Description: {COUNTIES['harris_tx']['description']}")

    # Another county example
    wake_bbox, wake_crs = get_location_bbox("wake_nc")
    print(f"\nCounty: Wake County, North Carolina")
    print(f"  Bbox: {wake_bbox}")
    print(f"  CRS: {wake_crs}")

    # Custom bounding box - no external dependencies needed
    custom_bbox = (-104.5, 44.0, -104.0, 44.5)
    print(f"\nCustom area:")
    print(f"  Bbox (WGS84): {custom_bbox}")
    print(f"  CRS: 4326")
    print("  Note: Custom bboxes work directly without boundary downloads")


def example_3_download_patterns():
    """Different patterns for downloading species data."""
    print("\n" + "=" * 60)
    print("Example 3: Download Patterns")
    print("=" * 60)

    api = BigMapAPI()

    # Note: These are examples - uncomment to actually download
    print("Download patterns using bounding boxes (not executed):")

    print("\n1. Single species, single county (using predefined bbox):")
    print('   bbox, crs = get_location_bbox("wake_nc")')
    print('   api.download_species(bbox=bbox, crs=crs, species_codes=["0131"])')

    print("\n2. Multiple species for a location:")
    print('   bbox, crs = get_location_bbox("harris_tx")')
    print('   api.download_species(bbox=bbox, crs=crs, species_codes=["0202", "0122"])')

    print("\n3. Custom bounding box:")
    print('   api.download_species(bbox=(-104.5, 44.0, -104.0, 44.5), crs="4326")')

    print("\n4. Using small test area:")
    print('   bbox, crs = get_location_bbox("raleigh_downtown")  # Small area for testing')
    print('   api.download_species(bbox=bbox, crs=crs, species_codes=["0068"])')


def example_4_zarr_operations():
    """Working with Zarr stores."""
    print("\n" + "=" * 60)
    print("Example 4: Zarr Operations")
    print("=" * 60)

    api = BigMapAPI()

    # Create sample data for demonstration
    sample_path = create_sample_zarr(Path("temp_sample.zarr"))

    # Validate zarr
    info = api.validate_zarr(sample_path)
    print(f"Zarr validation:")
    print(f"  Valid: {info.get('valid', False)}")
    print(f"  Shape: {info['shape']}")
    print(f"  Species: {info['num_species']}")

    # Get detailed info
    print_zarr_info(sample_path)

    # Clean up
    import shutil
    shutil.rmtree(sample_path)


def example_5_calculations():
    """Different calculation configurations."""
    print("\n" + "=" * 60)
    print("Example 5: Calculation Patterns")
    print("=" * 60)

    # Create sample data
    sample_path = create_sample_zarr(Path("temp_sample.zarr"))

    # Method 1: Simple calculation list
    api = BigMapAPI()
    results = api.calculate_metrics(
        zarr_path=sample_path,
        calculations=["species_richness", "shannon_diversity"]
    )
    print(f"Simple: Calculated {len(results)} metrics")

    # Method 2: Custom configuration
    settings = BigMapSettings(
        output_dir=Path("custom_output"),
        calculations=[
            CalculationConfig(
                name="species_richness",
                parameters={"biomass_threshold": 2.0},
                output_format="geotiff"
            ),
            CalculationConfig(
                name="total_biomass",
                output_format="geotiff"  # Changed from netcdf to geotiff
            )
        ]
    )
    api_custom = BigMapAPI(config=settings)
    results = api_custom.calculate_metrics(zarr_path=sample_path)
    print(f"Custom: Calculated {len(results)} metrics with custom settings")

    # Clean up
    import shutil
    shutil.rmtree(sample_path)
    if Path("custom_output").exists():
        shutil.rmtree("custom_output")


def example_6_visualization():
    """Creating visualizations."""
    print("\n" + "=" * 60)
    print("Example 6: Visualization Options")
    print("=" * 60)

    # Create sample data
    sample_path = create_sample_zarr(Path("temp_sample.zarr"))
    api = BigMapAPI()

    # Create output directory for all maps
    maps_dir = Path("example_maps")
    maps_dir.mkdir(exist_ok=True)

    # Different map types
    map_types = ["diversity", "species", "richness", "comparison"]
    all_created_files = []

    for map_type in map_types:
        output_subdir = maps_dir / map_type
        if map_type == "species":
            maps = api.create_maps(
                zarr_path=sample_path,
                map_type=map_type,
                output_dir=str(output_subdir),
                show_all=True
            )
        elif map_type == "comparison":
            maps = api.create_maps(
                zarr_path=sample_path,
                map_type=map_type,
                output_dir=str(output_subdir),
                species=["0001", "0002"]  # Compare first two species
            )
        else:
            maps = api.create_maps(
                zarr_path=sample_path,
                map_type=map_type,
                output_dir=str(output_subdir)
            )
        print(f"  {map_type}: Created {len(maps)} maps in {output_subdir}")
        all_created_files.extend(maps)

    print(f"\n📁 All visualization maps saved to: {maps_dir.absolute()}")
    print(f"   Total files created: {len(all_created_files)}")

    # Clean up only the temp zarr, keep the maps for user to see
    import shutil
    shutil.rmtree(sample_path)
    print("\nNote: Maps are preserved in 'example_maps/' for your review")


def example_7_batch_processing():
    """Batch processing multiple locations."""
    print("\n" + "=" * 60)
    print("Example 7: Batch Processing")
    print("=" * 60)

    api = BigMapAPI()

    locations = [
        {"state": "North Carolina", "counties": ["Wake", "Durham"]},
        {"state": "Montana", "counties": ["Missoula"]},
    ]

    print("Batch processing pattern:")
    for location in locations:
        state = location["state"]
        for county in location["counties"]:
            print(f"\n  Processing {county} County, {state}:")
            print(f"    1. Download species data")
            print(f"    2. Create zarr store")
            print(f"    3. Calculate metrics")
            print(f"    4. Generate visualizations")


def main():
    """Run all API examples."""
    print("\n" + "🌲" * 30)
    print("BigMap API Overview")
    print("Complete API Feature Demonstration")
    print("🌲" * 30)

    # Run examples
    example_1_list_species()
    example_2_location_config()
    example_3_download_patterns()
    example_4_zarr_operations()
    example_5_calculations()
    example_6_visualization()
    example_7_batch_processing()

    print("\n" + "=" * 60)
    print("API Overview Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  - Run specific examples for detailed workflows")
    print("  - See examples/README.md for full documentation")
    print("  - Check docs/tutorials/ for step-by-step guides")


if __name__ == "__main__":
    main()