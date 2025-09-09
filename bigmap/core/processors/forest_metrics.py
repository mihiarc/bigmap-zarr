"""
Forest Metrics Processor

Processor for running forest metric calculations from zarr data arrays.
This module integrates with the calculation registry to run various
forest metrics on large-scale biomass data efficiently.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import warnings

import numpy as np
import zarr
import rasterio
from rasterio.transform import from_bounds, Affine
import xarray as xr
from tqdm import tqdm

from ...config import BigMapSettings, load_settings, CalculationConfig
from ..calculations import registry
from ..calculations.base import ForestCalculation

logger = logging.getLogger(__name__)


class ForestMetricsProcessor:
    """
    Processor for running forest metric calculations on zarr arrays.
    
    This class handles:
    - Loading and validating zarr arrays
    - Running calculations from the registry
    - Memory-efficient chunked processing
    - Saving results in multiple formats
    """
    
    def __init__(self, settings: Optional[BigMapSettings] = None):
        """
        Initialize the processor with settings.
        
        Parameters
        ----------
        settings : BigMapSettings, optional
            Configuration settings. If None, uses default settings.
        """
        self.settings = settings or BigMapSettings()
        self.chunk_size = (1, 1000, 1000)  # Default chunk size for processing
        self.zarr_group = None  # Will store the parent group if available
        
        logger.info(f"Initialized ForestMetricsProcessor with output dir: {self.settings.output_dir}")
    
    def run_calculations(self, zarr_path: str) -> Dict[str, str]:
        """
        Run forest metric calculations on zarr data.
        
        Parameters
        ----------
        zarr_path : str
            Path to the zarr array containing biomass data
            
        Returns
        -------
        Dict[str, str]
            Dictionary mapping calculation names to output file paths
        """
        logger.info(f"Starting forest metrics processing for: {zarr_path}")
        
        # Get enabled calculations
        enabled_calcs = self._get_enabled_calculations()
        if not enabled_calcs:
            raise ValueError("No calculations enabled in configuration")
        
        # Load and validate zarr array
        zarr_array, zarr_group = self._load_zarr_array(zarr_path)
        self.zarr_group = zarr_group  # Store for potential later use
        self._validate_zarr_array(zarr_array)
        
        # Extract metadata for output files
        metadata = self._extract_metadata(zarr_array)
        
        # Initialize calculation instances
        calc_instances = self._initialize_calculations(enabled_calcs)
        
        # Process data in chunks
        logger.info(f"Processing {len(calc_instances)} calculations on array shape {zarr_array.shape}")
        results = self._process_in_chunks(zarr_array, calc_instances)
        
        # Save results
        output_paths = self._save_results(results, metadata, self.settings.output_dir)
        
        logger.info(f"Completed {len(output_paths)} calculations successfully")
        return output_paths
    
    def _get_enabled_calculations(self) -> List[CalculationConfig]:
        """Get list of enabled calculations from settings."""
        return [calc for calc in self.settings.calculations if calc.enabled]
    
    def _load_zarr_array(self, zarr_path: str) -> Tuple[Any, Optional[zarr.Group]]:
        """
        Load zarr store and return both array and parent group.
        
        Parameters
        ----------
        zarr_path : str
            Path to zarr store (can be group or array)
            
        Returns
        -------
        Tuple[Any, Optional[zarr.Group]]
            Tuple of (zarr array or wrapper, parent group if available)
        """
        class ArrayWrapper:
            """Wrapper to combine array with group metadata."""
            def __init__(self, array, attrs_dict):
                self._array = array
                self.attrs = attrs_dict
                self.shape = array.shape
                self.ndim = array.ndim
                self.dtype = array.dtype
                self.chunks = array.chunks if hasattr(array, 'chunks') else None
                
            def __getitem__(self, key):
                return self._array[key]
                
            def __getattr__(self, name):
                return getattr(self._array, name)
        
        try:
            # First try to open as a group (most common case for our data)
            root = zarr.open_group(zarr_path, mode='r')
            
            # Look for biomass array
            if 'biomass' in root:
                array = root['biomass']
                # Create combined attributes dictionary
                combined_attrs = dict(array.attrs)
                if hasattr(root, 'attrs'):
                    combined_attrs.update(root.attrs)
                # Add species arrays as attributes if they exist
                if 'species_codes' in root:
                    species_codes = root['species_codes'][:]
                    combined_attrs['species_codes'] = list(species_codes) if hasattr(species_codes, '__iter__') else []
                if 'species_names' in root:
                    species_names = root['species_names'][:]
                    combined_attrs['species_names'] = list(species_names) if hasattr(species_names, '__iter__') else []
                # Return wrapped array with combined attributes
                return ArrayWrapper(array, combined_attrs), root
                
            # Fallback: look for other common array names
            for name in ['data', 'species']:
                if name in root:
                    array = root[name]
                    combined_attrs = dict(array.attrs)
                    if hasattr(root, 'attrs'):
                        combined_attrs.update(root.attrs)
                    return ArrayWrapper(array, combined_attrs), root
                    
            raise ValueError(f"No biomass/data array found in zarr group at {zarr_path}")
                    
        except Exception as e:
            # Try as standalone array (legacy support)
            try:
                array = zarr.open_array(zarr_path, mode='r')
                return array, None
            except:
                raise ValueError(f"Cannot open {zarr_path} as Zarr group or array: {e}")
    
    def _validate_zarr_array(self, zarr_array: zarr.Array) -> None:
        """
        Validate zarr array structure and metadata.
        
        Parameters
        ----------
        zarr_array : zarr.Array
            Array to validate
            
        Raises
        ------
        ValueError
            If array is invalid
        """
        # Check dimensions
        if zarr_array.ndim != 3:
            raise ValueError(f"Expected 3D array (species, y, x), got {zarr_array.ndim}D")
        
        # Check required attributes
        required_attrs = ['species_codes', 'crs']
        missing_attrs = [attr for attr in required_attrs if attr not in zarr_array.attrs]
        if missing_attrs:
            raise ValueError(f"Missing required attributes: {missing_attrs}")
        
        # Check species dimension matches metadata
        n_species = zarr_array.shape[0]
        species_codes = zarr_array.attrs.get('species_codes', [])
        if len(species_codes) != n_species:
            raise ValueError(
                f"Species dimension ({n_species}) doesn't match "
                f"species_codes length ({len(species_codes)})"
            )
        
        logger.info(f"Validated zarr array: {n_species} species, shape {zarr_array.shape}")
    
    def _extract_metadata(self, zarr_array: zarr.Array) -> Dict[str, Any]:
        """
        Extract spatial metadata from zarr array.
        
        Parameters
        ----------
        zarr_array : zarr.Array
            Source array
            
        Returns
        -------
        Dict[str, Any]
            Metadata dictionary with crs, transform, bounds, etc.
        """
        metadata = {
            'crs': zarr_array.attrs.get('crs', 'ESRI:102039'),
            'species_codes': zarr_array.attrs.get('species_codes', []),
            'species_names': zarr_array.attrs.get('species_names', []),
            'shape': zarr_array.shape[1:],  # Spatial dimensions only
            'dtype': zarr_array.dtype
        }
        
        # Extract or compute transform
        if 'transform' in zarr_array.attrs:
            transform_list = zarr_array.attrs['transform']
            if len(transform_list) == 6:
                metadata['transform'] = Affine(*transform_list)
            else:
                metadata['transform'] = Affine(*transform_list[:6])
        elif 'bounds' in zarr_array.attrs:
            bounds = zarr_array.attrs['bounds']
            height, width = zarr_array.shape[1:]
            metadata['transform'] = from_bounds(*bounds, width, height)
            metadata['bounds'] = bounds
        else:
            # Default transform
            logger.warning("No spatial reference found, using default transform")
            metadata['transform'] = Affine(1, 0, 0, 0, -1, zarr_array.shape[1])
        
        return metadata
    
    def _initialize_calculations(self, calc_configs: List[CalculationConfig]) -> List[ForestCalculation]:
        """
        Initialize calculation instances from configurations.
        
        Parameters
        ----------
        calc_configs : List[CalculationConfig]
            List of calculation configurations
            
        Returns
        -------
        List[ForestCalculation]
            Initialized calculation instances
        """
        calc_instances = []
        
        for config in calc_configs:
            try:
                # Get calculation instance from registry
                calc_instance = registry.get(config.name, **config.parameters)
                if calc_instance is None:
                    logger.warning(f"Calculation '{config.name}' not found in registry")
                    continue
                calc_instances.append(calc_instance)
                
                logger.debug(f"Initialized calculation: {config.name}")
                
            except Exception as e:
                logger.error(f"Failed to initialize calculation '{config.name}': {e}")
                continue
        
        return calc_instances
    
    def _process_in_chunks(
        self, 
        zarr_array: zarr.Array, 
        calculations: List[ForestCalculation]
    ) -> Dict[str, np.ndarray]:
        """
        Process array in memory-efficient chunks.
        
        Parameters
        ----------
        zarr_array : zarr.Array
            Input array
        calculations : List[ForestCalculation]
            Calculations to run
            
        Returns
        -------
        Dict[str, np.ndarray]
            Results for each calculation
        """
        # Initialize result arrays
        height, width = zarr_array.shape[1:]
        results = {}
        for calc in calculations:
            dtype = calc.get_output_dtype()
            results[calc.name] = np.zeros((height, width), dtype=dtype)
        
        # Calculate chunk parameters
        chunk_height, chunk_width = self.chunk_size[1:]
        n_chunks_y = (height + chunk_height - 1) // chunk_height
        n_chunks_x = (width + chunk_width - 1) // chunk_width
        total_chunks = n_chunks_y * n_chunks_x
        
        logger.info(f"Processing in {total_chunks} chunks of size {self.chunk_size}")
        
        # Process each chunk
        with tqdm(total=total_chunks, desc="Processing chunks") as pbar:
            for i in range(n_chunks_y):
                for j in range(n_chunks_x):
                    # Calculate chunk boundaries
                    y_start = i * chunk_height
                    y_end = min((i + 1) * chunk_height, height)
                    x_start = j * chunk_width
                    x_end = min((j + 1) * chunk_width, width)
                    
                    # Load chunk data
                    chunk_data = zarr_array[:, y_start:y_end, x_start:x_end]
                    
                    # Run calculations on chunk
                    chunk_results = self._process_chunk(chunk_data, calculations)
                    
                    # Store results
                    for calc_name, result in chunk_results.items():
                        results[calc_name][y_start:y_end, x_start:x_end] = result
                    
                    pbar.update(1)
        
        return results
    
    def _process_chunk(
        self, 
        chunk_data: np.ndarray, 
        calculations: List[ForestCalculation]
    ) -> Dict[str, np.ndarray]:
        """
        Process a single chunk of data.
        
        Parameters
        ----------
        chunk_data : np.ndarray
            Chunk of biomass data (species, y, x)
        calculations : List[ForestCalculation]
            Calculations to run
            
        Returns
        -------
        Dict[str, np.ndarray]
            Results for each calculation
        """
        chunk_results = {}
        
        for calc in calculations:
            try:
                # Validate data for this calculation
                if calc.validate_data(chunk_data):
                    # Preprocess if needed
                    processed_data = calc.preprocess_data(chunk_data)
                    
                    # Run calculation
                    result = calc.calculate(processed_data)
                    
                    # Postprocess if needed
                    result = calc.postprocess_result(result)
                    
                    chunk_results[calc.name] = result
                else:
                    # Return zeros if validation fails
                    logger.warning(f"Validation failed for {calc.name} on chunk")
                    chunk_results[calc.name] = np.zeros(chunk_data.shape[1:], dtype=calc.get_output_dtype())
                    
            except Exception as e:
                logger.error(f"Error in calculation {calc.name}: {e}")
                # Return zeros on error
                chunk_results[calc.name] = np.zeros(chunk_data.shape[1:], dtype=calc.get_output_dtype())
        
        return chunk_results
    
    def _save_results(
        self, 
        results: Dict[str, np.ndarray], 
        metadata: Dict[str, Any],
        output_dir: Path
    ) -> Dict[str, str]:
        """
        Save calculation results to files.
        
        Parameters
        ----------
        results : Dict[str, np.ndarray]
            Calculation results
        metadata : Dict[str, Any]
            Spatial metadata
        output_dir : Path
            Output directory
            
        Returns
        -------
        Dict[str, str]
            Paths to saved files
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_paths = {}
        
        for calc_name, result_array in results.items():
            try:
                # Get output format from calculation config
                calc_config = next(
                    (c for c in self.settings.calculations if c.name == calc_name),
                    None
                )
                output_format = calc_config.output_format if calc_config else "geotiff"
                output_name = calc_config.output_name if (calc_config and calc_config.output_name) else calc_name
                
                # Save based on format
                if output_format.lower() in ["geotiff", "tif", "tiff"]:
                    output_path = output_dir / f"{output_name}.tif"
                    self._save_geotiff(result_array, output_path, metadata)
                elif output_format.lower() == "zarr":
                    output_path = output_dir / f"{output_name}.zarr"
                    self._save_zarr(result_array, output_path, metadata, calc_name)
                elif output_format.lower() in ["netcdf", "nc"]:
                    output_path = output_dir / f"{output_name}.nc"
                    self._save_netcdf(result_array, output_path, metadata, calc_name)
                else:
                    logger.warning(f"Unknown format '{output_format}', defaulting to GeoTIFF")
                    output_path = output_dir / f"{output_name}.tif"
                    self._save_geotiff(result_array, output_path, metadata)
                
                output_paths[calc_name] = str(output_path)
                logger.info(f"Saved {calc_name} to {output_path}")
                
            except Exception as e:
                logger.error(f"Failed to save {calc_name}: {e}")
                continue
        
        return output_paths
    
    def _save_geotiff(self, data: np.ndarray, output_path: Path, metadata: Dict[str, Any]) -> None:
        """Save data as GeoTIFF."""
        with rasterio.open(
            output_path,
            'w',
            driver='GTiff',
            height=data.shape[0],
            width=data.shape[1],
            count=1,
            dtype=data.dtype,
            crs=metadata.get('crs', 'ESRI:102039'),
            transform=metadata.get('transform'),
            compress='lzw'
        ) as dst:
            dst.write(data, 1)
            
            # Add metadata tags
            dst.update_tags(
                SOFTWARE='BigMap Forest Metrics Processor',
                PROCESSED_BY='bigmap.core.processors.forest_metrics'
            )
    
    def _save_zarr(
        self, 
        data: np.ndarray, 
        output_path: Path, 
        metadata: Dict[str, Any],
        var_name: str
    ) -> None:
        """Save data as zarr array."""
        # Create zarr array
        z = zarr.open_array(
            str(output_path),
            mode='w',
            shape=data.shape,
            chunks=(1000, 1000),
            dtype=data.dtype
        )
        
        # Write data
        z[:] = data
        
        # Add metadata
        z.attrs.update({
            'crs': metadata.get('crs'),
            'transform': list(metadata.get('transform', Affine.identity())),
            'variable': var_name,
            'units': 'varies',  # Could be improved with calc-specific units
            'software': 'BigMap Forest Metrics Processor'
        })
    
    def _save_netcdf(
        self, 
        data: np.ndarray, 
        output_path: Path, 
        metadata: Dict[str, Any],
        var_name: str
    ) -> None:
        """Save data as NetCDF using xarray."""
        # Create coordinates
        transform = metadata.get('transform', Affine.identity())
        height, width = data.shape
        
        # Calculate coordinate arrays
        cols = np.arange(width)
        rows = np.arange(height)
        xs, _ = transform * (cols, np.zeros_like(cols))
        _, ys = transform * (np.zeros_like(rows), rows)
        
        # Create xarray dataset
        ds = xr.Dataset(
            {var_name: (['y', 'x'], data)},
            coords={
                'x': (['x'], xs),
                'y': (['y'], ys)
            }
        )
        
        # Add attributes
        ds.attrs['crs'] = metadata.get('crs', 'ESRI:102039')
        ds[var_name].attrs['units'] = 'varies'
        
        # Save to NetCDF
        ds.to_netcdf(output_path, engine='netcdf4', encoding={
            var_name: {'zlib': True, 'complevel': 5}
        })


def run_forest_analysis(
    zarr_path: str, 
    config_path: Optional[str] = None
) -> Dict[str, str]:
    """
    Run forest analysis with the given configuration.
    
    This is a convenience function that creates a processor
    and runs the analysis.
    
    Parameters
    ----------
    zarr_path : str
        Path to zarr array
    config_path : str, optional
        Path to configuration file
        
    Returns
    -------
    Dict[str, str]
        Results dictionary mapping calculation names to output paths
    """
    if config_path:
        settings = load_settings(Path(config_path))
        logger.info(f"Loaded configuration from {config_path}")
    else:
        settings = BigMapSettings()
        logger.info("Using default configuration")
    
    processor = ForestMetricsProcessor(settings)
    return processor.run_calculations(zarr_path)