# heirs-fia

## Project Steps

1. Extract Halifax County data
   - Filter parcels for Halifax County from NC parcel data
   - Filter heirs parcels for Halifax County
   - Extract Halifax County boundary
   - Filter FIA plots for Halifax County

2. Define Roanoke Rapids study area
   - Create 20km buffer around Roanoke Rapids center point
   - Create 10km buffer for analysis area
   - Generate context map showing Roanoke Rapids in Halifax County
   - Generate detailed map of the Roanoke Rapids study area

3. Filter data for Roanoke Rapids study area
   - Filter parcels within 10km of Roanoke Rapids
   - Filter heirs parcels within 10km of Roanoke Rapids
   - Filter FIA plots within 10km of Roanoke Rapids

4. Analyze Plot-Parcel Relationships
   - Intersect FIA plots with parcels
   - Generate intersection statistics
   - Identify plots in heirs vs non-heirs parcels
   - Create summary report of relationships

5. Next Steps
   - Create visualizations of plot-parcel relationships
   - Analyze spatial patterns and clustering
   - Generate final report and recommendations

## Data files

1. 'data/raw/nc_fia_plots.csv'

This file contains plot level observations of forest inventory in the state of North Carolina.

2. 'data/raw/nc_county_boundaries.geojson'

This file contains the county boundaries for the state of North Carolina.

3. 'data/raw/nc_heirs_parcels.parquet'

This file contains tax parcel boundaries and attributes for Heirs Property in the state of North Carolina.

4. 'data/raw/nc_all_parcels.parquet'

This file contains tax parcel boundaries and attributes for all parcels in the state of North Carolina.

## Project Structure

```
.
├── config/
│   └── settings.yml      # Configuration settings for data paths and parameters
├── data/
│   ├── raw/             # Original input data
│   └── halifax_data/    # Processed data for Halifax County and Roanoke Rapids
├── src/
│   ├── extract_halifax_boundary.py       # Extract Halifax County boundary
│   ├── filter_halifax_parcels.py         # Filter parcels for Halifax County
│   ├── filter_fia_plots.py              # Filter FIA plots for Halifax County
│   ├── define_roanoke_area.py           # Define and map Roanoke Rapids study area
│   ├── filter_roanoke_rapids_parcels.py # Filter parcels for Roanoke Rapids
│   ├── filter_roanoke_rapids_fia.py     # Filter FIA plots for Roanoke Rapids
│   └── analyze_plot_parcel_intersections.py # Analyze relationships between plots and parcels
└── README.md
```
