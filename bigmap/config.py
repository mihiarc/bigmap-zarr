"""
Configuration management for BigMap using Pydantic.

This module defines configuration schemas and settings management
for the BigMap package, demonstrating best practices with Pydantic.
"""

from pathlib import Path
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings


class RasterConfig(BaseModel):
    """Configuration for raster processing parameters."""
    
    chunk_size: Tuple[int, int, int] = Field(
        default=(1, 1000, 1000),
        description="Chunk size for zarr arrays (species, height, width)"
    )
    pixel_size: float = Field(
        default=30.0,
        gt=0,
        description="Pixel size in meters"
    )
    compression: str = Field(
        default="lz4",
        description="Compression algorithm for zarr storage"
    )
    compression_level: int = Field(
        default=5,
        ge=1,
        le=9,
        description="Compression level (1-9)"
    )
    
    @validator('chunk_size')
    def validate_chunk_size(cls, v):
        """Ensure chunk size is reasonable."""
        if len(v) != 3:
            raise ValueError("Chunk size must have 3 dimensions")
        if any(x <= 0 for x in v):
            raise ValueError("All chunk dimensions must be positive")
        if v[1] * v[2] > 10_000_000:  # 10M pixels max per spatial chunk
            raise ValueError("Spatial chunk size too large (memory concern)")
        return v


class VisualizationConfig(BaseModel):
    """Configuration for visualization parameters."""
    
    default_dpi: int = Field(
        default=300,
        ge=72,
        le=600,
        description="Default DPI for output images"
    )
    default_figure_size: Tuple[float, float] = Field(
        default=(16, 12),
        description="Default figure size in inches (width, height)"
    )
    color_maps: dict = Field(
        default={
            "biomass": "viridis",
            "diversity": "plasma",
            "richness": "Spectral_r"
        },
        description="Default color maps for different data types"
    )
    font_size: int = Field(
        default=12,
        ge=8,
        le=24,
        description="Default font size for plots"
    )


class ProcessingConfig(BaseModel):
    """Configuration for data processing parameters."""
    
    max_workers: Optional[int] = Field(
        default=None,
        description="Maximum number of worker processes (None = auto-detect)"
    )
    memory_limit_gb: float = Field(
        default=8.0,
        gt=0,
        description="Memory limit in GB for processing"
    )
    temp_dir: Optional[Path] = Field(
        default=None,
        description="Temporary directory for processing"
    )
    
    @validator('temp_dir')
    def validate_temp_dir(cls, v):
        """Ensure temp directory exists or can be created."""
        if v is not None:
            v = Path(v)
            if not v.exists():
                try:
                    v.mkdir(parents=True, exist_ok=True)
                except OSError as e:
                    raise ValueError(f"Cannot create temp directory {v}: {e}")
        return v


class BigMapSettings(BaseSettings):
    """Main settings class for BigMap application."""
    
    # Application info
    app_name: str = "BigMap"
    debug: bool = Field(default=False, description="Enable debug mode")
    verbose: bool = Field(default=False, description="Enable verbose output")
    
    # File paths
    data_dir: Path = Field(
        default=Path("data"),
        description="Base directory for data files"
    )
    output_dir: Path = Field(
        default=Path("output"),
        description="Base directory for output files"
    )
    cache_dir: Path = Field(
        default=Path(".cache"),
        description="Directory for caching intermediate results"
    )
    
    # Processing configurations
    raster: RasterConfig = Field(default_factory=RasterConfig)
    visualization: VisualizationConfig = Field(default_factory=VisualizationConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    
    # Data validation
    species_codes: List[str] = Field(
        default_factory=list,
        description="List of valid species codes"
    )
    
    class Config:
        """Pydantic configuration."""
        env_prefix = "BIGMAP_"  # Environment variables start with BIGMAP_
        env_file = ".env"       # Load from .env file if present
        case_sensitive = False   # Case-insensitive environment variables
    
    @validator('data_dir', 'output_dir', 'cache_dir')
    def ensure_directories_exist(cls, v):
        """Ensure directories exist."""
        v = Path(v)
        v.mkdir(parents=True, exist_ok=True)
        return v
    
    def get_zarr_chunk_size(self) -> Tuple[int, int, int]:
        """Get the configured zarr chunk size."""
        return self.raster.chunk_size
    
    def get_output_path(self, filename: str) -> Path:
        """Get full output path for a filename."""
        return self.output_dir / filename
    
    def get_temp_path(self, filename: str) -> Path:
        """Get temporary file path."""
        temp_dir = self.processing.temp_dir or self.cache_dir
        return temp_dir / filename


# Global settings instance
settings = BigMapSettings()


def load_settings(config_file: Optional[Path] = None) -> BigMapSettings:
    """
    Load settings from file or environment.
    
    Args:
        config_file: Optional path to configuration file
        
    Returns:
        Configured settings instance
    """
    if config_file and config_file.exists():
        # Load from JSON/YAML file
        import json
        with open(config_file) as f:
            config_data = json.load(f)
        return BigMapSettings(**config_data)
    else:
        # Load from environment/defaults
        return BigMapSettings()


def save_settings(settings_obj: BigMapSettings, config_file: Path) -> None:
    """
    Save settings to file.
    
    Args:
        settings_obj: Settings to save
        config_file: Path to save configuration
    """
    import json
    
    config_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_file, 'w') as f:
        json.dump(
            settings_obj.dict(),
            f,
            indent=2,
            default=str  # Handle Path objects
        ) 