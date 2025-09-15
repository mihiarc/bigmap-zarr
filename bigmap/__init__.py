"""
BigMap: Forest Biomass and Species Diversity Analysis Toolkit

A comprehensive Python package for accessing and analyzing forest biomass 
and species diversity data from the BIGMAP 2018 dataset.
Provides a clean API-first architecture for programmatic access.
"""

__version__ = "0.2.0"
__author__ = "Christopher Mihiar"
__email__ = "christopher.mihiar@usda.gov"
__license__ = "MIT"

# Main API - this is the primary interface
from bigmap.api import BigMapAPI

# Configuration management for advanced users
from bigmap.config import BigMapSettings, load_settings, save_settings

# Example utilities (for running examples)
from bigmap.utils.examples import (
    AnalysisConfig,
    cleanup_example_outputs,
    safe_download_species,
    safe_load_zarr_with_memory_check,
    create_zarr_from_rasters,
    create_sample_zarr,
    print_zarr_info,
    calculate_basic_stats,
    validate_species_codes
)

# Define what gets imported with "from bigmap import *"
__all__ = [
    # Main API (primary interface)
    "BigMapAPI",

    # Configuration management
    "BigMapSettings",
    "load_settings",
    "save_settings",

    # Example utilities
    "AnalysisConfig",
    "cleanup_example_outputs",
    "safe_download_species",
    "safe_load_zarr_with_memory_check",
    "create_zarr_from_rasters",
    "create_sample_zarr",
    "print_zarr_info",
    "calculate_basic_stats",
    "validate_species_codes",

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
        "description": "Forest biomass and species diversity analysis toolkit with API-first architecture",
    }
