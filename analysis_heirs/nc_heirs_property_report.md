# North Carolina Heirs Property Analysis Report

*Report generated on April 07, 2025*

## Executive Summary

This report analyzes the distribution and characteristics of heirs properties across North Carolina counties. Heirs property is a type of ownership where land is passed down without a will, resulting in multiple owners as tenants-in-common. This form of ownership can create challenges for landowners including limited access to capital, difficulty managing the property, and vulnerability to land loss.

**Key Findings:**
- North Carolina has **24,349** identified heirs properties across **100** counties
- The top 5 counties account for **28.9%** of all heirs properties in the state
- The top 10 counties account for **49.5%** of all heirs properties in the state

## Distribution of Heirs Properties

The distribution of heirs properties varies significantly across North Carolina counties. The map below shows the number of heirs properties in each county.

![North Carolina Heirs Property Distribution](output/nc_heirs_distribution_map.png)

### Top Counties by Heirs Property Count

![Top Counties](output/top_counties_bar_chart.png)

### Top 10 Counties

| County | Heirs Properties | % of State Total |
|--------|-----------------|------------------|
| Gaston County | 1,572 | 6.5% |
| Catawba County | 1,498 | 6.2% |
| Rockingham County | 1,473 | 6.0% |
| Wake County | 1,286 | 5.3% |
| Wayne County | 1,196 | 4.9% |
| Beaufort County | 1,164 | 4.8% |
| Craven County | 1,020 | 4.2% |
| Duplin County | 1,010 | 4.1% |
| Vance County | 1,000 | 4.1% |
| Randolph County | 829 | 3.4% |

## County-Level Analysis

This section examines the characteristics of heirs properties in the top counties and compares them with the overall property landscape in each county.

### Gaston County

**Key Statistics:**
- Total Heirs Properties: 1,572.00
- Total Heirs Property Acreage: 4,221.00
- Average Heirs Property Size: 2.69
- Median Heirs Property Size: 0.38
- Total Value of Heirs Properties: 65387130
- Average Heirs Property Value: 41,594.87
- Percentage of County Land: 1.97%
- Percentage of County Property Value: 0.21%

**Heirs Property Size Distribution:**

![Property Size Distribution](output/gaston_property_size.png)

**Heirs Property Value Distribution:**

![Property Value Distribution](output/gaston_property_value.png)

### Catawba County

**Key Statistics:**
- Total Heirs Properties: 1,498.00
- Total Heirs Property Acreage: 5,079.25
- Average Heirs Property Size: 3.39
- Median Heirs Property Size: 0.60
- Total Value of Heirs Properties: 86839300
- Average Heirs Property Value: 57,970.16
- Percentage of County Land: 2.01%
- Percentage of County Property Value: 0.33%

**Heirs Property Size Distribution:**

![Property Size Distribution](output/catawba_property_size.png)

**Heirs Property Value Distribution:**

![Property Value Distribution](output/catawba_property_value.png)

### Rockingham County

**Key Statistics:**
- Total Heirs Properties: 1,473.00
- Total Heirs Property Acreage: 9,638.80
- Average Heirs Property Size: 6.54
- Median Heirs Property Size: 0.61
- Total Value of Heirs Properties: 66073969
- Average Heirs Property Value: 44,856.73
- Percentage of County Land: 2.83%
- Percentage of County Property Value: 1.01%

**Heirs Property Size Distribution:**

![Property Size Distribution](output/rockingham_property_size.png)

**Heirs Property Value Distribution:**

![Property Value Distribution](output/rockingham_property_value.png)

### Wake County

**Key Statistics:**
- Total Heirs Properties: 1,286.00
- Total Heirs Property Acreage: 4,117.04
- Average Heirs Property Size: 3.20
- Median Heirs Property Size: 0.43
- Total Value of Heirs Properties: 235941533
- Average Heirs Property Value: 183,469.31
- Percentage of County Land: 0.72%
- Percentage of County Property Value: 0.08%

**Heirs Property Size Distribution:**

![Property Size Distribution](output/wake_property_size.png)

**Heirs Property Value Distribution:**

![Property Value Distribution](output/wake_property_value.png)

### Wayne County

**Key Statistics:**
- Total Heirs Properties: 1,196.00
- Total Heirs Property Acreage: 5,206.52
- Average Heirs Property Size: 4.35
- Median Heirs Property Size: 0.46
- Total Value of Heirs Properties: 41839412
- Average Heirs Property Value: 34,982.79
- Percentage of County Land: 1.46%
- Percentage of County Property Value: 0.50%

**Heirs Property Size Distribution:**

![Property Size Distribution](output/wayne_property_size.png)

**Heirs Property Value Distribution:**

![Property Value Distribution](output/wayne_property_value.png)

## Key Insights and Patterns

Based on the analysis of heirs properties across North Carolina counties, several patterns emerge:

1. **Geographic Concentration**: Heirs properties are not evenly distributed across the state. The highest concentrations are found in select counties, particularly in the western and northeastern regions.

2. **Property Size**: Heirs properties tend to be smaller than the average parcel size in their respective counties, with median sizes often below one acre.

3. **Property Value**: The market value of heirs properties is typically lower than the county average, which may reflect challenges in property maintenance, investment, and development due to the complex ownership structure.

4. **Economic Impact**: Although heirs properties represent a small percentage of total county land and value, they can have significant implications for community development, particularly in rural areas with limited economic opportunities.

## Conclusions

The analysis of heirs property in North Carolina highlights the importance of addressing the challenges associated with this form of land ownership. As heirs properties represent a vulnerable form of land tenure, targeted interventions may be needed to help landowners navigate legal complexities, access capital for property maintenance and development, and preserve this land for future generations.

Further research could explore:
- The demographic characteristics of heirs property owners
- The economic impact of resolving title issues for heirs properties
- The relationship between heirs property and community development outcomes
- Temporal trends in the creation and resolution of heirs properties

## Methodology

This analysis was conducted using Python with the following tools and data sources:

**Data Sources:**
- Heirs property data from `nc-hp_v2.parquet`
- County parcel data from Lightbox (`county_fixed_parcels.parquet` files)
- North Carolina county boundaries from `nc_county_boundary.geojson`

**Analysis Process:**
1. Partitioned heirs property data by county
2. Calculated county-level statistics and visualizations
3. Generated maps showing the distribution of heirs properties
4. Performed detailed analysis of key counties
