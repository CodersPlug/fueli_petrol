"""Database operations module"""
import sqlite3
import pandas as pd
from pathlib import Path

DATABASE_PATH = "data/fueli.db"

def ensure_db_exists():
    """Create database and tables if they don't exist"""
    db_path = Path(DATABASE_PATH)
    db_path.parent.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Create despachos table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS despachos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL,
        hora TIME DEFAULT '00:00',
        sucursal TEXT NOT NULL,
        pico TEXT,
        producto TEXT,
        volumen REAL,
        importe REAL,
        ppu REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    conn.close()

def migrate_csv_to_db():
    """Migrate data from CSV to SQLite database"""
    # Read CSV file
    df = pd.read_csv('data/consolidated_data.csv')
    
    # Create date from year, month, day
    df['fecha'] = pd.to_datetime({
        'year': df['Año'].astype(int),
        'month': df['Mes'].astype(int),
        'day': df['Día'].astype(int)
    }).dt.strftime('%Y-%m-%d')  # Store as YYYY-MM-DD string
    
    # Add hora column
    df['hora'] = '00:00'
    
    # Rename columns to match database schema
    df = df.rename(columns={
        'Sucursal': 'sucursal',
        'Pico': 'pico',
        'Producto': 'producto',
        'Volumen': 'volumen',
        'Importe': 'importe',
        'PPU': 'ppu'
    })
    
    # Select and order columns for database
    columns = ['fecha', 'hora', 'sucursal', 'pico', 'producto', 'volumen', 'importe', 'ppu']
    df = df[columns]
    
    # Connect to database
    conn = sqlite3.connect(DATABASE_PATH)
    
    # Insert data
    df.to_sql('despachos', conn, if_exists='replace', index=False)
    
    conn.close()

def get_despachos(organization=None, producto=None, start_date=None, end_date=None, pico=None):
    """Get despachos with optional filters"""
    conn = sqlite3.connect(DATABASE_PATH)
    
    query = "SELECT * FROM despachos WHERE 1=1"
    params = []
    
    if organization:
        if organization.lower() == 'posta':
            query += " AND sucursal LIKE 'Posta%'"
        else:
            query += " AND sucursal LIKE ?"
            params.append(f"%{organization}%")
    
    if producto:
        if isinstance(producto, list):
            placeholders = ','.join(['?' for _ in producto])
            query += f" AND producto IN ({placeholders})"
            params.extend(producto)
        else:
            query += " AND producto = ?"
            params.append(producto)
    
    if start_date:
        query += " AND fecha >= ?"
        params.append(start_date.strftime('%Y-%m-%d') if hasattr(start_date, 'strftime') else start_date)
    
    if end_date:
        query += " AND fecha <= ?"
        params.append(end_date.strftime('%Y-%m-%d') if hasattr(end_date, 'strftime') else end_date)
    
    if pico:
        if isinstance(pico, list):
            placeholders = ','.join(['?' for _ in pico])
            query += f" AND pico IN ({placeholders})"
            params.extend(pico)
        else:
            query += " AND pico = ?"
            params.append(pico)
    
    # Read data and parse dates
    df = pd.read_sql_query(query, conn, params=params)
    if not df.empty and 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'])
    
    conn.close()
    return df

# Initialize database
ensure_db_exists() 