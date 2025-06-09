# NDVI Analysis Report
Generated on 2025-01-16 09:09:54

## Overview
This report compares the Normalized Difference Vegetation Index (NDVI) values between heirs property parcels and their neighboring parcels in Vance County, North Carolina. The analysis is based on NAIP imagery from 2018.

## Summary Statistics

### Heirs Property Parcels

| Statistic | Heirs Parcels |
|-----------|-------------|
| Count | 977 |
| Mean | 0.2103 |
| Std Dev | 0.0834 |
| Min | 0.0171 |
| 25% | 0.1493 |
| Median | 0.2017 |
| 75% | 0.2630 |
| Max | 0.5272 |


### Neighboring Parcels

| Statistic | Neighboring Parcels |
|-----------|-------------|
| Count | 1,864 |
| Mean | 0.2050 |
| Std Dev | 0.0797 |
| Min | -0.0495 |
| 25% | 0.1463 |
| Median | 0.1964 |
| 75% | 0.2569 |
| Max | 0.4623 |


## Key Findings

1. **Sample Sizes**:
   - Heirs Parcels: 1,008
   - Neighboring Parcels: 1,941

2. **Mean NDVI Comparison**:
   - Heirs Parcels: 0.2103
   - Neighboring Parcels: 0.2050
   - Difference (Heirs - Neighbors): 0.0053

3. **Area Coverage** (in pixels):
   - Heirs Parcels: 65,147,323
   - Neighboring Parcels: 264,137,095
   - Average Area per Parcel:
     - Heirs: 64,630.3
     - Neighbors: 136,083.0

## Distribution Comparison
![NDVI Distribution Comparison](ndvi_distribution_comparison.png)

The histogram above shows the distribution of mean NDVI values for both heirs parcels (green) and neighboring parcels (blue). The dashed lines represent the mean values for each group.

## Methodology
1. Parcels were filtered to include only those within the extent of the NAIP imagery
2. NDVI values were calculated for each pixel within each parcel
3. Statistics were computed for each parcel, including mean, median, and standard deviation of NDVI values
4. Neighboring parcels were defined as those sharing a boundary with heirs parcels

## Data Sources
- NAIP imagery (2018)
- Heirs property parcel database
- NC parcel database

## Files Generated
- `heirs_ndvi_stats.csv`: Detailed statistics for heirs parcels
- `neighbors_ndvi_stats.csv`: Detailed statistics for neighboring parcels
- `ndvi_distribution_comparison.png`: Visualization of NDVI distributions
