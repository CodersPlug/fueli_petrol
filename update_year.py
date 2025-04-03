import pandas as pd

# Read the CSV file
df = pd.read_csv('data/consolidated_data.csv')

# Update the year to 2025
df['Año'] = 2025

# Save back to CSV
df.to_csv('data/consolidated_data.csv', index=False)

print('Year updated to 2025 in consolidated_data.csv') 