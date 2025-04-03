import pandas as pd
import os
from pathlib import Path
import re
from datetime import datetime

def extract_date_from_filename(filename):
    """Extract date information from filename"""
    # Try to find month name in Spanish
    month_map = {
        'ENERO': 1, 'FEBRERO': 2, 'MARZO': 3, 'ABRIL': 4, 'MAYO': 5, 'JUNIO': 6,
        'JULIO': 7, 'AGOSTO': 8, 'SEPTIEMBRE': 9, 'OCTUBRE': 10, 'NOVIEMBRE': 11, 'DICIEMBRE': 12
    }
    
    filename = filename.upper()
    for month_name, month_num in month_map.items():
        if month_name in filename:
            # Assume current year if not specified
            return 2024, month_num
    
    return 2024, 1  # Default to January 2024 if no month found

def find_data_start(df):
    """Find where the actual data starts in the DataFrame"""
    # Look for common column headers
    common_headers = ['Fecha', 'Pico', 'Manguera', 'Volumen', 'Importe', 'Surt', 'Mang', 'Fecha y Hora']
    
    for idx, row in df.iterrows():
        # Convert row values to string and check if any common headers are present
        row_values = [str(val).strip() for val in row.values if pd.notna(val)]
        if any(header in row_values for header in common_headers):
            return idx
    
    return 0  # Default to first row if no header found

def clean_date(date_str):
    """Clean and parse date string"""
    if pd.isna(date_str) or not isinstance(date_str, str):
        return None
    
    # Remove any text after numbers (like "Cantidad de cargas: 658")
    date_str = re.sub(r'[^\d/: ].*$', '', str(date_str))
    
    try:
        # Try different date formats
        for fmt in ['%d/%m/%Y', '%d/%m/%Y %H:%M:%S', '%Y-%m-%d %H:%M:%S']:
            try:
                return pd.to_datetime(date_str, format=fmt)
            except:
                continue
        return None
    except:
        return None

def extract_surtidor_manguera(value):
    """Extract surtidor and manguera from combined string"""
    if pd.isna(value):
        return None, None
    
    # Try to split by slash
    parts = str(value).split('/')
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    
    # Try to extract numbers
    match = re.search(r'(\d+)\s*([a-zA-Z])?', str(value))
    if match:
        surtidor = match.group(1)
        manguera = match.group(2) if match.group(2) else 'a'
        return surtidor, manguera
    
    return None, None

def process_excel_file(file_path):
    """Process a single Excel file and return a DataFrame with standardized columns"""
    print(f"\nProcessing {file_path}")
    
    try:
        # Try to read the Excel file with different engines
        if str(file_path).endswith('.xls'):
            print("Using xlrd engine for .xls file")
            df = pd.read_excel(file_path, engine='xlrd', header=None)
        else:
            print("Using openpyxl engine for .xlsx file")
            df = pd.read_excel(file_path, engine='openpyxl', header=None)
        
        # Find where the actual data starts
        data_start = find_data_start(df)
        print(f"Data starts at row {data_start}")
        
        # Use the row before data_start as header
        if data_start > 0:
            headers = df.iloc[data_start].values
            df = df.iloc[data_start + 1:].reset_index(drop=True)
            df.columns = headers
        
        # Clean column names
        df.columns = [str(col).strip() for col in df.columns]
        
        print(f"Original columns: {df.columns.tolist()}")
        print(f"Number of rows: {len(df)}")
        
        # Get date information from filename
        year, month = extract_date_from_filename(os.path.basename(file_path))
        print(f"Extracted date: {year}-{month}")
        
        # Determine if this is a GNC file
        is_gnc = 'GNC' in os.path.basename(file_path).upper()
        print(f"Is GNC file: {is_gnc}")
        
        # Create standardized DataFrame
        result = pd.DataFrame()
        
        # Add date columns
        result['Año'] = year
        result['Mes'] = month
        
        # Process date
        if 'Fecha y Hora' in df.columns:
            dates = df['Fecha y Hora'].apply(clean_date)
            result['Día'] = dates.dt.day
        elif 'Fecha' in df.columns:
            dates = df['Fecha'].apply(clean_date)
            result['Día'] = dates.dt.day
        else:
            result['Día'] = 1
        
        # Add fixed columns
        result['Cliente'] = 'Petrol'
        result['Sucursal'] = 'Petrol'
        
        # Process Pico column
        if 'Surt' in df.columns and 'Mang' in df.columns:
            result['Pico'] = df['Surt'].astype(str) + df['Mang'].astype(str).str.lower()
        elif 'Surtidor/Manguera' in df.columns:
            # Extract Surtidor and Manguera components
            surtidor_manguera = df['Surtidor/Manguera'].apply(extract_surtidor_manguera)
            df['Surtidor'] = surtidor_manguera.apply(lambda x: x[0])
            df['Manguera'] = surtidor_manguera.apply(lambda x: x[1])
            result['Pico'] = df['Surtidor'].astype(str) + df['Manguera'].astype(str).str.lower()
        elif 'Pico' in df.columns:
            result['Pico'] = df['Pico'].astype(str)
        else:
            result['Pico'] = '1'  # Default value if not found
        
        # Process Producto column
        if is_gnc:
            result['Producto'] = 'GNC'
        elif 'Producto' in df.columns:
            result['Producto'] = df['Producto']
        else:
            result['Producto'] = 'LIQUIDO'  # Default for non-GNC files
        
        # Process Importe column
        if 'Importe' in df.columns:
            result['Importe'] = pd.to_numeric(df['Importe'].astype(str).str.replace(r'[$,]', '', regex=True), errors='coerce')
        else:
            result['Importe'] = 0
        
        # Process Volumen column
        if 'Volumen' in df.columns:
            result['Volumen'] = pd.to_numeric(df['Volumen'], errors='coerce')
        else:
            result['Volumen'] = 0
        
        # Calculate PPU if not present
        if 'PPU' in df.columns:
            result['PPU'] = pd.to_numeric(df['PPU'], errors='coerce')
        else:
            # Calculate PPU as Importe/Volumen where both are non-zero
            mask = (result['Volumen'] != 0) & (result['Importe'] != 0)
            result['PPU'] = 0.0
            result.loc[mask, 'PPU'] = result.loc[mask, 'Importe'] / result.loc[mask, 'Volumen']
        
        # Remove rows with all null values or where key fields are null
        result = result.dropna(subset=['Importe', 'Volumen'], how='all')
        
        # Fill NaN values with appropriate defaults
        result = result.fillna({
            'Año': year,
            'Mes': month,
            'Día': 1,
            'Cliente': 'Petrol',
            'Sucursal': 'Petrol',
            'PPU': 0
        })
        
        print(f"Processed {len(result)} rows successfully")
        return result
    
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        import traceback
        print(f"Full error: {traceback.format_exc()}")
        return None

def main():
    # Get all Excel files in the data directory and its subdirectories
    data_dir = Path('data')
    excel_files = []
    for pattern in ['**/*.xls', '**/*.xlsx']:
        excel_files.extend(data_dir.glob(pattern))
    
    if not excel_files:
        print("No Excel files found in data directory or subdirectories")
        return
    
    print(f"Found {len(excel_files)} Excel files to process")
    
    # Process each file and combine results
    all_data = []
    for file_path in excel_files:
        print(f"\nProcessing {file_path}")
        df = process_excel_file(file_path)
        if df is not None and len(df) > 0:
            all_data.append(df)
    
    if not all_data:
        print("No data was processed successfully")
        return
    
    # Combine all DataFrames
    final_df = pd.concat(all_data, ignore_index=True)
    
    # Save to CSV
    output_path = data_dir / 'consolidated_data.csv'
    final_df.to_csv(output_path, index=False)
    print(f"\nData consolidated and saved to {output_path}")
    print(f"Total records: {len(final_df)}")
    print("\nSample of consolidated data:")
    print(final_df.head())
    
    # Print summary by product
    print("\nSummary by product:")
    summary = final_df.groupby('Producto').agg({
        'Importe': ['count', 'sum'],
        'Volumen': 'sum'
    }).round(2)
    print(summary)

if __name__ == '__main__':
    main() 