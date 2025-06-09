"""
BigMap: North Carolina Forest Biomass and Species Diversity Analysis Tools

A comprehensive Python package for processing, analyzing, and visualizing
forest biomass and species diversity data from the BIGMAP 2018 dataset.
"""

__version__ = "0.1.0"
__author__ = "Christopher Mihiar"
__email__ = "christopher.mihiar@usda.gov"
__license__ = "MIT"

# Import main functionality for easy access
from bigmap.core.analyze_species_presence import analyze_species_presence
from bigmap.core.create_species_diversity_map import (
    calculate_species_diversity_chunked,
    create_xarray_interface,
)
from bigmap.utils.create_nc_biomass_zarr import (
    create_expandable_zarr_from_base_raster,
    append_species_to_zarr,
)
from bigmap.visualization.map_nc_forest import create_nc_forest_map

# Import new modules for configuration and console output
from bigmap.config import BigMapSettings, settings, load_settings, save_settings
from bigmap.console import console, print_success, print_error, print_warning, print_info
from bigmap.api import BigMapRestClient

# Define what gets imported with "from bigmap import *"
__all__ = [
    # Core analysis functions
    "analyze_species_presence",
    "calculate_species_diversity_chunked",
    "create_xarray_interface",
    # Data processing functions
    "create_expandable_zarr_from_base_raster",
    "append_species_to_zarr",
    # Visualization functions
    "create_nc_forest_map",
    # API access
    "BigMapRestClient",
    # Package metadata
    "__version__",
    "__author__",
    "__email__",
    "__license__",
]


def get_version() -> str:
    """Return the package version."""
    return __version__


def get_package_info() -> dict:
    """Return package information as a dictionary."""
    return {
        "name": "bigmap",
        "version": __version__,
        "author": __author__,
        "email": __email__,
        "license": __license__,
        "description": "North Carolina forest biomass and species diversity analysis tools",
    }
