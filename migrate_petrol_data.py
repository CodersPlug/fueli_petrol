"""Script to migrate data from Petrol's consolidated data into SQLite database"""
import pandas as pd
import sqlite3
from pathlib import Path
from database import DATABASE_PATH, ensure_db_exists
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def standardize_petrol_dataframe(df):
    """Convert Petrol's data format to match database schema"""
    # Create fecha from Año, Mes, Día, forcing year to be 2024
    df['fecha'] = pd.to_datetime({
        'year': pd.Series([2024] * len(df)),  # Force all years to 2024
        'month': df['Mes'].astype(int),
        'day': df['Día'].astype(int)
    }).dt.strftime('%Y-%m-%d')
    
    # Map columns to match database schema
    df = df.rename(columns={
        'Pico': 'pico',
        'Producto': 'producto',
        'Volumen': 'volumen',
        'Importe': 'importe',
        'PPU': 'ppu',
        'Sucursal': 'sucursal'
    })
    
    # Add hora column with default value
    df['hora'] = '00:00'
    
    # Standardize product names
    product_mapping = {
        'NS XXI': 'GNC',  # Assuming NS XXI is GNC
        'INFINIA': 'INFINIA',
        'D.DIESEL500': 'DIESEL 500',
        'GO-INFINIA DIESEL': 'INFINIA DIESEL'
    }
    df['producto'] = df['producto'].map(product_mapping)
    
    # Keep only the columns we need
    required_columns = ['fecha', 'hora', 'pico', 'producto', 'volumen', 'importe', 'ppu', 'sucursal']
    df = df[required_columns]
    
    # Drop rows with missing values
    df = df.dropna(subset=['fecha', 'pico', 'producto', 'volumen', 'importe'])
    
    return df

def main():
    """Main function to process Petrol data."""
    # Ensure database exists
    ensure_db_exists()
    
    # Create our own database connection
    conn = sqlite3.connect(DATABASE_PATH)
    
    try:
        # Read consolidated data
        print("\nReading Petrol consolidated data...")
        df = pd.read_csv('data/consolidated_data.csv')
        
        if df.empty:
            print("No data found in consolidated_data.csv")
            return
            
        print(f"Found {len(df)} records")
        
        # Standardize DataFrame
        print("\nStandardizing data format...")
        df = standardize_petrol_dataframe(df)
        print(f"Standardized {len(df)} records")
        
        # Check if we have any data
        if df.empty:
            print("No valid data after standardization")
            return
            
        # Insert into database
        print("\nInserting into database...")
        df.to_sql('despachos', conn, if_exists='append', index=False)
        
        # Verify the data was inserted
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM despachos WHERE sucursal = 'Petrol'")
        count = cursor.fetchone()[0]
        print(f"Successfully inserted {count} Petrol records into the database")
        
    except Exception as e:
        print(f"Error processing Petrol data: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    main() 