BigMap 🌲

A Python package for analyzing North Carolina forest biomass and species diversity using BIGMAP 2018 data.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Features

- 🗺️ **Spatial Analysis**: Clip and process large geospatial raster datasets
- 📊 **Species Diversity**: Calculate tree species diversity metrics
- 💾 **Efficient Storage**: Create compressed Zarr arrays for fast analysis
- 📈 **Visualization**: Generate publication-ready maps and charts
- 🔧 **Batch Processing**: Handle multiple species datasets efficiently

## Installation

### Using uv (Recommended)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create and activate virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install bigmap
uv pip install -e .

# Install with development dependencies
uv pip install -e ".[dev]"
```

### Using pip

```bash
pip install -e .
```

## Quick Start

```python
import bigmap
from bigmap.core import analyze_species_presence
from bigmap.visualization import create_nc_forest_map

# Analyze species presence in your data
analyze_species_presence()

# Create a biomass map
create_nc_forest_map(
    raster_path="data/biomass.tif",
    data_type="biomass",
    output_path="nc_biomass_map.png"
)
```

## Command Line Interface

BigMap provides convenient CLI commands:

```bash
# Analyze species data
bigmap-analyze --input data/ --output results/

# Create visualizations
bigmap-visualize --data-type diversity --output maps/

# Process batch rasters
bigmap-process --input /path/to/bigmap/data --boundary nc_boundary.geojson
```

## Project Structure

```
bigmap/
├── core/                   # Core analysis functions
│   ├── analyze_species_presence.py
│   └── create_species_diversity_map.py
├── utils/                  # Utility functions
│   ├── batch_append_species.py
│   ├── clip_rasters_to_nc.py
│   └── create_nc_biomass_zarr.py
├── visualization/          # Visualization and mapping
│   └── map_nc_forest.py
└── cli/                    # Command line interface
    └── __init__.py
```

## Data Requirements

This package works with BIGMAP 2018 forest data:

- **Input Format**: GeoTIFF raster files
- **Spatial Reference**: ESRI:102039 (recommended)
- **Data Type**: Above-ground biomass (Mg/ha)
- **Resolution**: 30m pixels

## Example Workflows

### 1. Process Raw BIGMAP Data

```python
from bigmap.utils import clip_rasters_to_nc, create_nc_biomass_zarr

# Clip rasters to North Carolina
clip_rasters_to_nc(
    input_dir="/path/to/bigmap/data",
    output_dir="nc_clipped_rasters/"
)

# Create compressed Zarr array
create_nc_biomass_zarr(
    base_raster="nc_clipped_rasters/total_biomass.tif",
    output_path="nc_biomass.zarr"
)
```

### 2. Analyze Species Diversity

```python
from bigmap.core import calculate_species_diversity

# Calculate diversity metrics
diversity_map = calculate_species_diversity("nc_biomass.zarr")

# Save results
diversity_map.to_netcdf("nc_species_diversity.nc")
```

### 3. Create Visualizations

```python
from bigmap.visualization import create_nc_forest_map

# Create multiple map types
for data_type in ['biomass', 'diversity', 'richness']:
    create_nc_forest_map(
        raster_path=f"nc_{data_type}.tif",
        data_type=data_type,
        output_path=f"nc_{data_type}_map.png"
    )
```

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/bigmap.git
cd bigmap

# Create virtual environment with uv
uv venv
source .venv/bin/activate

# Install in development mode with all dependencies
uv pip install -e ".[dev,test,docs]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=bigmap --cov-report=html

# Run specific test file
pytest tests/test_core.py
```

### Code Quality

This project uses several tools to maintain code quality:

```bash
# Format code
black bigmap/
isort bigmap/

# Lint code
flake8 bigmap/

# Type checking
mypy bigmap/

# Run all quality checks
pre-commit run --all-files
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass and code quality checks pass
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Citation

If you use this software in your research, please cite:

```bibtex
@software{bigmap2024,
  title={BigMap: North Carolina Forest Analysis Tools},
  author={Your Name},
  year={2024},
  url={https://github.com/yourusername/bigmap}
}
```

## Acknowledgments

- BIGMAP 2018 dataset for forest biomass data
- North Carolina forest research community
- Open source geospatial Python ecosystem

## Support

- 📖 [Documentation](https://bigmap.readthedocs.io/)
- 🐛 [Issue Tracker](https://github.com/yourusername/bigmap/issues)
- 💬 [Discussions](https://github.com/yourusername/bigmap/discussions)