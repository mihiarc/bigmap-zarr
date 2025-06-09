
# Understanding NDVI and Land Cover Analysis

## What is NDVI?
NDVI (Normalized Difference Vegetation Index) is a measure that helps us understand vegetation density and health on a piece of land. It uses satellite imagery to calculate a score between -1 and 1:

- Higher values (closer to 1) indicate denser, healthier vegetation
- Lower values (closer to 0 or negative) indicate less vegetation or bare ground
- Typical values for different land types:
  * Dense, healthy vegetation: 0.6 to 0.9
  * Moderate vegetation: 0.2 to 0.5
  * Sparse vegetation or bare soil: -0.1 to 0.1
  * Water: -1 to 0

## Why This Matters
Understanding NDVI helps us:
- Assess land use and vegetation health
- Compare different properties' vegetation coverage
- Track changes in land condition over time
- Identify areas that might need conservation attention

---

# NDVI Analysis Report: Heirs vs Non-Heirs Property Comparison
Generated on 2025-01-24 11:55:03

## Overview
This report analyzes the Normalized Difference Vegetation Index (NDVI) values between heirs and non-heirs property parcels across North Carolina counties. NDVI is a measure of vegetation density and health, ranging from -1 to 1, where higher values indicate denser, healthier vegetation.

## Overall Comparison
![NDVI Distribution Comparison](figures/ndvi_comparison.png)

## Statistical Summary
### Heirs Properties
- Count: 4,632
- Mean NDVI: 0.2025
- Median NDVI: 0.1944
- Standard Deviation: 0.0977
- Range: -0.2916 to 0.5663


### Non-Heirs Properties
- Count: 669,706
- Mean NDVI: 0.1773
- Median NDVI: 0.1716
- Standard Deviation: 0.0919
- Range: -0.6510 to 0.7248


## East vs West Comparison

### Eastern Region
- Number of Counties: 9
- Total Parcels:
  - Heirs: 2,359
  - Non-Heirs: 197,623
- Mean NDVI Values:
  - Heirs Properties: 0.1957
  - Non-Heirs Properties: 0.1669
- NDVI Difference (Heirs - Non-Heirs):
  - Mean: 0.0288
  - Standard Deviation: 0.0185
  - Range: 0.0001 to 0.0530

### Western Region
- Number of Counties: 10
- Total Parcels:
  - Heirs: 2,318
  - Non-Heirs: 480,244
- Mean NDVI Values:
  - Heirs Properties: 0.1936
  - Non-Heirs Properties: 0.1764
- NDVI Difference (Heirs - Non-Heirs):
  - Mean: 0.0172
  - Standard Deviation: 0.0143
  - Range: -0.0072 to 0.0368



![Regional Comparison](figures/regional_comparison.png)

## Regional Analysis

### Eastern Region
**Number of Counties:** 9

**Regional Statistics:**
- Total Heirs Parcels: 2,359
- Total Non-Heirs Parcels: 197,623
- Mean NDVI Difference (Heirs - Non-Heirs): 0.0288

**County Breakdown:**
| County | Heirs Count | Non-Heirs Count | NDVI Difference |
|--------|-------------|-----------------|------------------|
| Warren | 89 | 22,823 | 0.0463 |
| Vance | 999 | 25,382 | 0.0205 |
| Washington | 38 | 12,396 | 0.0530 |
| Chowan | 16 | 12,745 | 0.0499 |
| Edgecombe | 22 | 31,090 | 0.0354 |
| Halifax | 73 | 39,292 | 0.0149 |
| Bertie | 791 | 17,986 | 0.0266 |
| Northampton | 222 | 20,257 | 0.0001 |
| Hertford | 109 | 15,652 | 0.0125 |

### Western Region
**Number of Counties:** 10

**Regional Statistics:**
- Total Heirs Parcels: 2,318
- Total Non-Heirs Parcels: 480,244
- Mean NDVI Difference (Heirs - Non-Heirs): 0.0172

**County Breakdown:**
| County | Heirs Count | Non-Heirs Count | NDVI Difference |
|--------|-------------|-----------------|------------------|
| Cherokee | 55 | 33,762 | 0.0124 |
| Alexander | 55 | 25,015 | 0.0368 |
| Buncombe | 135 | 131,682 | 0.0333 |
| Catawba | 1,496 | 86,414 | 0.0355 |
| Burke | 49 | 58,318 | 0.0085 |
| Clay | 69 | 15,754 | 0.0174 |
| Caldwell | 245 | 52,460 | 0.0160 |
| Alleghany | 82 | 14,599 | 0.0136 |
| Avery | 28 | 23,687 | 0.0053 |
| Ashe | 104 | 38,553 | -0.0072 |



## Methodology
1. NDVI values were calculated for each pixel within each parcel using NAIP imagery (2022)
2. Parcel-level statistics were computed (mean, median, standard deviation)
3. Comparisons were made between heirs and non-heirs parcels at both county and regional levels
4. Statistical analyses were performed to validate the comparisons

## Data Sources
- NAIP imagery (2022)
- Heirs property parcel database
- NC parcel database
