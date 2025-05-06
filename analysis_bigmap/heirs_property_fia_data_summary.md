# Heirs Property and FIA Data Summary

This document summarizes three datasets that analyze the relationship between heirs properties and Forest Inventory and Analysis (FIA) plots in North Carolina.

## Overview of Datasets

1. **heirs_properties_with_fia_plots.csv**: Contains information about heir properties with FIA plots located on them, including property details and FIA plot characteristics.

2. **fia_plots_in_heirs_properties.csv**: Details the FIA plots located within heir properties, including forestry measurements and property information.

3. **non_heirs_fia_plots_by_distance.csv**: Lists FIA plots that are not on heir properties but are within certain distances of heir properties, categorized by distance.

## Heirs Properties with FIA Plots

This dataset combines heir property records with FIA plot data. Key information includes:

- **Property Details**: Parcel IDs, addresses, ownership information, property values, land size, etc.
- **Heir Property Indicators**: "HEIRS" flag, "HRS" (heirs) or "ESTATE" designations in ownership fields
- **FIA Plot Information**: Plot IDs, coordinates, forest type codes, measurements
- **Geography**: Coordinates, county names, state information (all in North Carolina)

Most properties are explicitly marked with "HEIRS" in the heir_searc column or contain "HEIRS", "HRS", or "ESTATE" in the ownership fields.

## FIA Plots in Heirs Properties

This dataset focuses on the Forest Inventory and Analysis plots located within heir properties:

- **FIA Measurements**: Plot IDs (PLT_CN), evaluation groups (EVAL_GRP), forest type codes (FORTYPCD), tree density (TPA)
- **Forest Characteristics**: Stand age (STDAGE), stand size (STDSZCD), slope, aspect, disturbance codes and years
- **Geographic Information**: Coordinates, state codes, county codes
- **Property Information**: Ownership details, land values, parcel numbers
- **Heirs Status**: Marked with "HEIRS", "HRS", "ESTATE" or similar indicators

Many plots are from recent inventory years (2010-2022), showing current forest conditions on heir properties.

## Non-Heirs FIA Plots by Distance

This dataset contains information about FIA plots not on heir properties but within proximity:

- **Distance Classification**: 
  - Plots are categorized by distance from heir properties (e.g., "0-5km")
  - A "distance" column shows the specific distance measurement
- **Plot Details**: Same FIA measurements as the other datasets
- **Geographic Distribution**: Plots across various North Carolina counties
- **Temporal Range**: Survey years span from 1974 to 2022

This dataset allows for comparative analysis between forests on heir properties and nearby non-heir properties.

## Key Observations

1. **Geographic Distribution**: The data focuses on North Carolina counties, with heir properties containing FIA plots spread across multiple counties.

2. **Property Characteristics**: Heir properties vary significantly in size, from small parcels (<10 acres) to larger tracts (>500 acres).

3. **Forest Types**: Various forest type codes (FORTYPCD) are represented, indicating diversity in forest composition on heir properties.

4. **Ownership Patterns**: Most heir properties are explicitly identified by "HEIRS" designation or similar terminology in owner fields.

5. **Data Timeline**: FIA plot measurements span several decades (1970s-2020s), allowing for temporal analysis of forest conditions.

This data could support analysis of:
- Forest management differences between heir and non-heir properties
- Spatial patterns of heir property forests
- The relationship between heir status and forest characteristics
- Potential policy implications for sustainable forestry on heir properties 