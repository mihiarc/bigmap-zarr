import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load the data
print("Loading data...")
data = pd.read_csv('tables/heirs_property_combined_data.csv')

# Identify heirs properties
print("Identifying heirs properties...")
# Create a heirs property flag based on the 'heir_searc' column and OWN1 field containing HEIRS, HEIR, HRS, ESTATE, or EST
data['is_heirs'] = 0

# Set to 1 if heir_searc is 'HEIRS'
heirs_mask = data['heir_searc'] == 'HEIRS'
data.loc[heirs_mask, 'is_heirs'] = 1

# Set to 1 if estate indicators in OWN1
estate_indicators = ['HEIRS', 'HEIR', 'HRS', 'ESTATE', 'EST']
for indicator in estate_indicators:
    mask = data['OWN1'].str.contains(indicator, case=False, na=False)
    data.loc[mask, 'is_heirs'] = 1

# Count heirs and non-heirs properties
heirs_count = data['is_heirs'].sum()
non_heirs_count = (data['is_heirs'] == 0).sum()
print(f"Found {heirs_count} heirs properties and {non_heirs_count} non-heirs properties")

# Remove parcel size outliers using IQR method
print("Removing parcel size outliers...")
Q1 = data['land_acre'].quantile(0.25)
Q3 = data['land_acre'].quantile(0.75)
IQR = Q3 - Q1
lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR

# Display original data statistics
print(f"Original data: {len(data)} parcels")
print(f"Land acre statistics - Min: {data['land_acre'].min():.2f}, Max: {data['land_acre'].max():.2f}, Mean: {data['land_acre'].mean():.2f}, Median: {data['land_acre'].median():.2f}")

# Filter outliers
data_filtered = data[(data['land_acre'] >= lower_bound) & (data['land_acre'] <= upper_bound)]

# Display filtered data statistics
print(f"After removing outliers: {len(data_filtered)} parcels")
print(f"Land acre statistics - Min: {data_filtered['land_acre'].min():.2f}, Max: {data_filtered['land_acre'].max():.2f}, Mean: {data_filtered['land_acre'].mean():.2f}, Median: {data_filtered['land_acre'].median():.2f}")
print(f"Removed {len(data) - len(data_filtered)} outliers")

# Count heirs and non-heirs properties after filtering
heirs_count = data_filtered['is_heirs'].sum()
non_heirs_count = (data_filtered['is_heirs'] == 0).sum()
print(f"After filtering: {heirs_count} heirs properties and {non_heirs_count} non-heirs properties")

# Function to calculate statistics for a column
def calculate_stats(df, column, is_heirs=None):
    if is_heirs is not None:
        df = df[df['is_heirs'] == is_heirs]
    
    stats = {
        'mean': df[column].mean(),
        'median': df[column].median(),
        'std': df[column].std(),
        'min': df[column].min(),
        'max': df[column].max(),
        'count': df[column].count()
    }
    return stats

# List of pine species columns
pine_columns = [
    'All_Pines_Combined_mean',
    'Shortleaf Pine_mean',
    'Longleaf Pine_mean',
    'Slash Pine_mean',
    'Loblolly Pine_mean'
]

# Calculate statistics for each pine species
print("Calculating statistics...")
results = {}

for column in pine_columns:
    species_name = column.replace('_mean', '')
    results[species_name] = {
        'heirs': calculate_stats(data_filtered, column, is_heirs=1),
        'non_heirs': calculate_stats(data_filtered, column, is_heirs=0)
    }

# Print the results
print("\nComparison of Pine Species Distribution between Heirs and Non-Heirs Properties (Outliers Removed)")
print("=" * 100)

for species, stats in results.items():
    print(f"\n{species}:")
    print("-" * 100)
    print(f"{'Statistic':<10} {'Heirs Properties':<20} {'Non-Heirs Properties':<20} {'Difference':<15} {'% Difference':<15}")
    print("-" * 100)
    
    for stat in ['mean', 'median', 'std', 'min', 'max', 'count']:
        heirs_val = stats['heirs'][stat]
        non_heirs_val = stats['non_heirs'][stat]
        
        if stat != 'count' and heirs_val is not None and non_heirs_val is not None:
            diff = heirs_val - non_heirs_val
            if non_heirs_val != 0:
                pct_diff = (diff / non_heirs_val) * 100
            else:
                pct_diff = float('nan')
        else:
            diff = 'N/A'
            pct_diff = 'N/A'
        
        # Format the values
        if stat == 'count':
            heirs_formatted = f"{heirs_val:.0f}"
            non_heirs_formatted = f"{non_heirs_val:.0f}"
        else:
            heirs_formatted = f"{heirs_val:.2f}"
            non_heirs_formatted = f"{non_heirs_val:.2f}"
        
        # Format the difference values
        if diff != 'N/A':
            diff_formatted = f"{diff:.2f}"
            pct_diff_formatted = f"{pct_diff:.2f}%"
        else:
            diff_formatted = diff
            pct_diff_formatted = pct_diff
        
        print(f"{stat:<10} {heirs_formatted:<20} {non_heirs_formatted:<20} {diff_formatted:<15} {pct_diff_formatted:<15}")

# Create visualization
plt.figure(figsize=(12, 8))

# Set up data for grouped bar chart
species_names = [name.replace('_mean', '') for name in pine_columns]
heirs_means = [results[name]['heirs']['mean'] for name in species_names]
non_heirs_means = [results[name]['non_heirs']['mean'] for name in species_names]

# Set up bar positions
x = np.arange(len(species_names))
width = 0.35

# Create bars
bars1 = plt.bar(x - width/2, heirs_means, width, label='Heirs Properties')
bars2 = plt.bar(x + width/2, non_heirs_means, width, label='Non-Heirs Properties')

# Add labels and title
plt.xlabel('Pine Species')
plt.ylabel('Mean Coverage (%)')
plt.title('Comparison of Pine Species Coverage between Heirs and Non-Heirs Properties\n(Outliers Removed)')
plt.xticks(x, [name.replace('All_Pines_Combined', 'All Pines') for name in species_names])
plt.legend()

# Add value labels on bars
def add_labels(bars):
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{height:.1f}%', ha='center', va='bottom')

add_labels(bars1)
add_labels(bars2)

# Save the figure
plt.tight_layout()
plt.savefig('pine_species_comparison_no_outliers.png')
print("\nVisualization saved to 'pine_species_comparison_no_outliers.png'")

# Analyze the acreage differences
print("\nAnalyzing land acreage differences...")
heirs_acreage = calculate_stats(data_filtered, 'land_acre', is_heirs=1)
non_heirs_acreage = calculate_stats(data_filtered, 'land_acre', is_heirs=0)

print("\nLand Acreage Comparison (Outliers Removed):")
print("-" * 100)
print(f"{'Statistic':<10} {'Heirs Properties':<20} {'Non-Heirs Properties':<20} {'Difference':<15} {'% Difference':<15}")
print("-" * 100)

for stat in ['mean', 'median', 'std', 'min', 'max', 'count']:
    heirs_val = heirs_acreage[stat]
    non_heirs_val = non_heirs_acreage[stat]
    
    if stat != 'count' and heirs_val is not None and non_heirs_val is not None:
        diff = heirs_val - non_heirs_val
        if non_heirs_val != 0:
            pct_diff = (diff / non_heirs_val) * 100
        else:
            pct_diff = float('nan')
    else:
        diff = 'N/A'
        pct_diff = 'N/A'
    
    # Format the values
    if stat == 'count':
        heirs_formatted = f"{heirs_val:.0f}"
        non_heirs_formatted = f"{non_heirs_val:.0f}"
    else:
        heirs_formatted = f"{heirs_val:.2f}"
        non_heirs_formatted = f"{non_heirs_val:.2f}"
    
    # Format the difference values
    if diff != 'N/A':
        diff_formatted = f"{diff:.2f}"
        pct_diff_formatted = f"{pct_diff:.2f}%"
    else:
        diff_formatted = diff
        pct_diff_formatted = pct_diff
    
    print(f"{stat:<10} {heirs_formatted:<20} {non_heirs_formatted:<20} {diff_formatted:<15} {pct_diff_formatted:<15}") 