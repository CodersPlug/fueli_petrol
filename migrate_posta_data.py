"""Script to migrate data from Posta's folders into SQLite database"""
import pandas as pd
import os
from pathlib import Path
import sqlite3
from database import DATABASE_PATH, ensure_db_exists
import xml.etree.ElementTree as ET
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_excel_xml_file(file_path, sucursal):
    """Process an Excel XML file and return a DataFrame."""
    try:
        # Register the namespace
        ET.register_namespace('ss', 'urn:schemas-microsoft-com:office:spreadsheet')
        
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Define namespace for searching
        ns = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet'}
        
        rows = []
        for row in root.findall('.//ss:Row', ns):
            try:
                # Get all cells in the row
                cells = row.findall('.//ss:Cell', ns)
                if not cells:
                    continue
                
                # Extract cell data
                cell_data = {}
                for cell in cells:
                    data = cell.find('.//ss:Data', ns)
                    if data is None:
                        continue
                        
                    # Get cell index
                    index = cell.get('{urn:schemas-microsoft-com:office:spreadsheet}Index')
                    if not index:
                        continue
                        
                    # Get cell type and value
                    cell_type = data.get('{urn:schemas-microsoft-com:office:spreadsheet}Type')
                    value = data.text
                    
                    if not value:
                        continue
                        
                    # Store based on index
                    cell_data[int(index)] = (cell_type, value)
                
                # Skip if we don't have enough data
                if len(cell_data) < 6:
                    continue
                
                # Extract required fields
                fecha_hora = cell_data.get(1, (None, None))[1]
                pico = cell_data.get(2, (None, None))[1]
                producto = cell_data.get(3, (None, None))[1]
                importe = cell_data.get(5, (None, None))[1]
                volumen = cell_data.get(6, (None, None))[1]
                
                # Skip if any required field is missing
                if not all([fecha_hora, pico, producto, importe, volumen]):
                    continue
                
                # Parse date and time
                try:
                    fecha_hora = datetime.strptime(fecha_hora, '%d/%m/%Y %H:%M:%S')
                    fecha = fecha_hora.date()
                    hora = fecha_hora.time()
                except ValueError:
                    logging.warning(f"Invalid date format in {file_path}: {fecha_hora}")
                    continue
                
                # Standardize product names
                producto = producto.strip()
                if producto == 'NS XXI':
                    producto = 'GNC'
                elif producto == 'GO-INFINIA DIESEL':
                    producto = 'INFINIA DIESEL'
                
                # Convert numeric values
                try:
                    importe = float(importe.replace(',', '.'))
                    volumen = float(volumen.replace(',', '.'))
                except ValueError:
                    logging.warning(f"Invalid numeric values in {file_path}: importe={importe}, volumen={volumen}")
                    continue
                
                # Calculate price per unit
                ppu = importe / volumen if volumen != 0 else 0
                
                # Add row data
                row_data = {
                    'fecha': fecha,
                    'hora': hora,
                    'pico': pico,
                    'producto': producto,
                    'volumen': volumen,
                    'importe': importe,
                    'ppu': ppu,
                    'sucursal': sucursal
                }
                rows.append(row_data)
                
            except Exception as e:
                logging.warning(f"Error processing row in {file_path}: {str(e)}")
                continue
        
        if not rows:
            logging.warning(f"No valid data found in {file_path}")
            return None
            
        return pd.DataFrame(rows)
        
    except Exception as e:
        logging.error(f"Error processing file {file_path}: {str(e)}")
        return None

def clean_numeric_string(value):
    """Clean numeric string by removing currency symbols, units, and formatting"""
    if pd.isna(value):
        return None
    
    value = str(value)
    # Remove currency symbols, units, and spaces
    value = (value
             .replace('$', '')
             .replace('Ltr', '')
             .replace('M3', '')  # Remove cubic meters unit
             .replace('$/Ltr', '')
             .replace('/', '')  # Remove trailing slashes
             .replace(' ', '')
             .replace('\xa0', ''))
    
    # Handle numbers with multiple thousands separators
    if '.' in value and ',' in value:
        # If both . and , are present, assume . is thousands separator
        value = value.replace('.', '')
        value = value.replace(',', '.')
    elif '.' in value:
        # If only . is present and there are multiple occurrences, it's a thousands separator
        if value.count('.') > 1:
            value = value.replace('.', '')
    elif ',' in value:
        # If only , is present, it's a decimal separator
        value = value.replace(',', '.')
    
    try:
        return float(value.strip())
    except ValueError:
        print(f"Warning: Could not convert '{value}' to float")
        return None

def process_csv_file(file_path):
    """Process a CSV file and return a DataFrame"""
    # Read CSV file, skipping the second row which contains 'expand_less'
    df = pd.read_csv(file_path, skiprows=[1])
    
    # Clean up numeric columns
    if 'Monto' in df.columns:
        df['Monto'] = df['Monto'].apply(clean_numeric_string)
    if 'Precio' in df.columns:
        df['Precio'] = df['Precio'].apply(clean_numeric_string)
    if 'Volumen' in df.columns:
        df['Volumen'] = df['Volumen'].apply(clean_numeric_string)
    
    # Remove rows where 'Fecha final' contains 'Surtidor'
    if 'Fecha final' in df.columns:
        df = df[~df['Fecha final'].str.contains('Surtidor', na=False)]
    
    return df

def standardize_dataframe(df):
    """Standardize column names and formats."""
    logging.info(f"Columns before cleanup: {df.columns.tolist()}")
    
    # Drop duplicate columns, keeping the last occurrence
    df = df.loc[:, ~df.columns.duplicated(keep='last')]
    
    # Define column mappings
    column_mappings = {
        'Fecha final': 'fecha',
        'Hora final': 'hora',
        'Manguera': 'pico',
        'Combust.': 'producto',
        'Volumen': 'volumen',
        'Monto': 'importe',
        'Precio': 'ppu'
    }
    
    # Rename columns that exist in the DataFrame
    for old_col, new_col in column_mappings.items():
        if old_col in df.columns:
            df = df.rename(columns={old_col: new_col})
    
    # Keep only the columns we need
    required_columns = ['fecha', 'hora', 'pico', 'producto', 'volumen', 'importe', 'ppu', 'sucursal']
    existing_columns = [col for col in required_columns if col in df.columns]
    df = df[existing_columns]
    
    # Ensure fecha is in YYYY-MM-DD format and handle missing dates
    if 'fecha' in df.columns:
        # Convert any datetime objects to string format
        df['fecha'] = pd.to_datetime(df['fecha'], format='mixed', errors='coerce')
        
        # Drop rows with invalid dates
        df = df.dropna(subset=['fecha'])
        
        # Convert to YYYY-MM-DD format
        df['fecha'] = df['fecha'].dt.strftime('%Y-%m-%d')
    
    logging.info(f"Final columns: {df.columns.tolist()}")
    return df

def process_excel_file(file_path, sucursal):
    """Process an Excel file and return a DataFrame."""
    try:
        # For Hersu files, we know the data starts at row 16 (15 rows to skip, including column headers)
        if 'Hersu' in file_path:
            df = pd.read_excel(file_path, skiprows=15, names=['Fecha y Hora', 'Surtidor/Manguera', 'Producto', 'Tipo de Pago', 'Importe', 'Volumen', 'PPU', 'Densidad'])
            print(f"\nReading Hersu file with skiprows=15 and predefined column names")
            print(f"Columns: {df.columns.tolist()}")
            print(f"First row: {df.iloc[0].tolist()}")
            
            # Remove summary section at the end (rows starting with "CANTIDAD")
            df = df[~df['Fecha y Hora'].astype(str).str.contains('CANTIDAD')]
        else:
            # For other files, try different approaches
            dfs = []
            
            # Try reading with different numbers of header rows
            for skip_rows in range(10):
                try:
                    df = pd.read_excel(file_path, skiprows=skip_rows)
                    print(f"\nTrying with skiprows={skip_rows}")
                    print(f"Columns: {df.columns.tolist()}")
                    print(f"First row: {df.iloc[0].tolist()}")
                    dfs.append((skip_rows, df))
                except Exception as e:
                    print(f"Error with skiprows={skip_rows}: {str(e)}")
                    continue
            
            if not dfs:
                raise ValueError("Could not read Excel file with any configuration")
                
            # Try to identify the best DataFrame based on column names or content
            best_df = None
            best_skip_rows = None
            best_score = 0
            
            for skip_rows, df in dfs:
                # Look for the most complete data table
                columns = [str(col).upper() for col in df.columns]
                score = 0
                
                # Score based on presence of expected columns
                if any('FECHA' in col for col in columns):
                    score += 2
                if any(word in ' '.join(columns) for word in ['VOLUMEN', 'LITROS']):
                    score += 2
                if any(word in ' '.join(columns) for word in ['IMPORTE', 'MONTO']):
                    score += 2
                if any(word in ' '.join(columns) for word in ['PRODUCTO', 'COMBUSTIBLE']):
                    score += 2
                if any(word in ' '.join(columns) for word in ['PICO', 'SURTIDOR']):
                    score += 1
                    
                # Check data quality
                if df.shape[1] >= 4:  # Should have at least date, product, volume, amount
                    score += 2
                if not df.iloc[:5].isnull().all(axis=1).any():  # No completely empty rows in first 5
                    score += 1
                    
                if best_df is None or score > best_score:
                    best_df = df
                    best_skip_rows = skip_rows
                    best_score = score
            
            if best_df is None:
                raise ValueError("Could not identify valid data table in Excel file")
                
            print(f"\nSelected configuration with skiprows={best_skip_rows}")
            print(f"Columns: {best_df.columns.tolist()}")
            print(f"First row: {best_df.iloc[0].tolist()}")
            
            df = best_df
        
        # Clean up the data
        df = df.dropna(how='all')  # Drop completely empty rows
        
        # Create standardized DataFrame
        result = pd.DataFrame()
        
        # For Hersu files, we know the exact column names
        if 'Hersu' in file_path:
            result['fecha'] = pd.to_datetime(df['Fecha y Hora'], format='mixed')
            result['hora'] = result['fecha'].dt.strftime('%H:%M')  # Extract time from fecha
            result['fecha'] = result['fecha'].dt.strftime('%Y-%m-%d')  # Keep only the date part
            result['pico'] = df['Surtidor/Manguera'].astype(str)
            result['producto'] = df['Producto']
            result['volumen'] = pd.to_numeric(df['Volumen'].astype(str).str.replace(',', '.'), errors='coerce')
            result['importe'] = pd.to_numeric(df['Importe'].astype(str).str.replace('$', '').str.replace(',', '.'), errors='coerce')
            result['ppu'] = pd.to_numeric(df['PPU'].astype(str).str.replace('$', '').str.replace(',', '.'), errors='coerce')
        else:
            # For other files, try to identify columns by their content
            fecha_col = None
            for col in df.columns:
                sample_values = df[col].astype(str).head()
                if any('/' in str(val) for val in sample_values):
                    fecha_col = col
                    break
                    
            if not fecha_col:
                # Try looking for date-like column names
                for col in df.columns:
                    if isinstance(col, str) and any(x in col.upper() for x in ['FECHA', 'DATE']):
                        fecha_col = col
                        break
                        
            if not fecha_col:
                raise ValueError(f"No date column found. Available columns: {df.columns.tolist()}")
                
            # Add required columns
            result['fecha'] = pd.to_datetime(df[fecha_col], format='mixed')
            result['hora'] = '00:00'  # Default value since time might not be available
            
            # Try to identify columns by their content
            for col in df.columns:
                col_str = str(col).upper()
                sample_values = df[col].astype(str).head()
                
                # Look for pump/pico column
                if any(word in col_str for word in ['PICO', 'SURTIDOR', 'BOMBA']):
                    result['pico'] = df[col].astype(str)
                    continue
                    
                # Look for product column
                if any(word in col_str for word in ['PRODUCTO', 'COMBUSTIBLE', 'TIPO']):
                    result['producto'] = df[col]
                    continue
                    
                # Look for volume column (numeric values without $ symbol)
                if any(word in col_str for word in ['VOLUMEN', 'LITROS', 'CANTIDAD']):
                    result['volumen'] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
                    continue
                    
                # Look for amount column (numeric values with possible $ symbol)
                if any(word in col_str for word in ['IMPORTE', 'MONTO', 'TOTAL', 'VALOR']):
                    result['importe'] = pd.to_numeric(df[col].astype(str).str.replace('$', '').str.replace(',', '.'), errors='coerce')
                    continue
                    
                # Look for price column
                if any(word in col_str for word in ['PRECIO', 'PPU', 'UNITARIO']):
                    result['ppu'] = pd.to_numeric(df[col].astype(str).str.replace('$', '').str.replace(',', '.'), errors='coerce')
        
        # Fill in missing columns with defaults
        if 'pico' not in result.columns:
            result['pico'] = '1'
        if 'producto' not in result.columns:
            result['producto'] = 'LIQUIDO'
        if 'ppu' not in result.columns and 'volumen' in result.columns and 'importe' in result.columns:
            result['ppu'] = result['importe'] / result['volumen']
            
        result['sucursal'] = sucursal
        
        # Clean up the data
        result = result.dropna(subset=['fecha', 'volumen', 'importe'])  # Remove rows with missing critical data
        
        # Standardize product names
        product_mapping = {
            'NS XXI': 'GNC',
            'INFINIA': 'INFINIA',
            'D.DIESEL500': 'DIESEL 500',
            'GO-INFINIA DIESEL': 'INFINIA DIESEL',
            'SUPER': 'SUPER',
            'DIESEL': 'DIESEL'
        }
        result['producto'] = result['producto'].map(lambda x: product_mapping.get(str(x).strip(), x))
        
        print(f"Successfully processed {len(result)} records from {file_path}")
        return result
        
    except Exception as e:
        logging.error(f"Error processing Excel file {file_path}: {str(e)}")
        return None

def process_folder(folder_path, sucursal):
    """Process all files in a folder and return a consolidated DataFrame"""
    logger.info(f"Processing folder: {folder_path}")
    all_data = []
    
    if not os.path.exists(folder_path):
        logger.warning(f"Folder not found: {folder_path}")
        return pd.DataFrame()
    
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)
        if not os.path.isfile(file_path):
            continue
            
        logger.info(f"Processing file: {file_name}")
        df = None
        
        if file_name.endswith('.xls') or file_name.endswith('.xlsx'):
            df = process_excel_file(file_path, sucursal)
        elif file_name.endswith('.csv'):
            df = process_csv_file(file_path)
        elif file_name.endswith('.xml'):
            df = process_excel_xml_file(file_path, sucursal)
        
        if df is not None and not df.empty:
            df['sucursal'] = sucursal
            all_data.append(df)
    
    if not all_data:
        logger.warning(f"No data found in folder: {folder_path}")
        return pd.DataFrame()
    
    return pd.concat(all_data, ignore_index=True)

def ensure_db_exists():
    """Ensure database and table exist."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Create table with standardized column names
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS despachos (
        fecha TEXT NOT NULL,
        hora TEXT NOT NULL,
        pico TEXT NOT NULL,
        producto TEXT NOT NULL,
        volumen REAL NOT NULL,
        importe REAL NOT NULL,
        ppu REAL NOT NULL,
        sucursal TEXT NOT NULL
    )
    ''')
    
    conn.commit()
    return conn

def main():
    # Ensure database exists
    ensure_db_exists()
    
    # Process Cepia data
    print("\nProcessing Posta Cepia data...")
    cepia_df = process_folder("data/Cepia", "Posta Cepia")
    if cepia_df is not None and not cepia_df.empty:
        print(f"Successfully processed {len(cepia_df)} records from Cepia")
        cepia_df = standardize_dataframe(cepia_df)
    
    # Process Hersu data
    print("\nProcessing Posta Hersu data...")
    hersu_df = process_folder("data/Hersu", "Posta Hersu")
    if hersu_df is not None and not hersu_df.empty:
        print(f"Successfully processed {len(hersu_df)} records from Hersu")
        hersu_df = standardize_dataframe(hersu_df)
    
    # Process Erezcano data
    print("\nProcessing Posta Erezcano data...")
    erezcano_df = process_folder("data/Erezcano", "Posta Erezcano")
    if erezcano_df is not None and not erezcano_df.empty:
        print(f"Successfully processed {len(erezcano_df)} records from Erezcano")
        erezcano_df = standardize_dataframe(erezcano_df)
    
    # Combine all DataFrames
    dfs = []
    if cepia_df is not None and not cepia_df.empty:
        dfs.append(cepia_df)
    if hersu_df is not None and not hersu_df.empty:
        dfs.append(hersu_df)
    if erezcano_df is not None and not erezcano_df.empty:
        dfs.append(erezcano_df)
    
    if not dfs:
        print("No data found in any folder")
        return
    
    # Combine standardized DataFrames
    combined_df = pd.concat(dfs, ignore_index=True)
    print(f"\nTotal records: {len(combined_df)}")
    
    # Insert into database
    conn = sqlite3.connect(DATABASE_PATH)
    combined_df.to_sql('despachos', conn, if_exists='replace', index=False)
    conn.close()
    
    print("\nData successfully imported into database")

if __name__ == "__main__":
    main() 