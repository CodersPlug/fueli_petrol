import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime
import os

def adapt_datetime(dt):
    return dt.isoformat()

def convert_datetime(val):
    return datetime.fromisoformat(val)

def process_xml_file(xml_file):
    # Connect to the database and set up datetime handling
    sqlite3.register_adapter(datetime, adapt_datetime)
    sqlite3.register_converter("DATETIME", convert_datetime)
    conn = sqlite3.connect('fueli.db', detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    
    # Create the fuel_data table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fuel_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_time DATETIME,
            pump TEXT,
            fuel_type TEXT,
            amount REAL,
            volume REAL,
            product_code INTEGER,
            organization TEXT,
            sucursal TEXT
        )
    ''')
    
    # Parse the XML file
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    # Get the worksheet data
    worksheet = root.find('.//{urn:schemas-microsoft-com:office:spreadsheet}Worksheet')
    table = worksheet.find('.//{urn:schemas-microsoft-com:office:spreadsheet}Table')
    
    records_processed = 0
    errors = 0
    
    # Get all rows and skip the header row
    rows = table.findall('.//{urn:schemas-microsoft-com:office:spreadsheet}Row')
    if len(rows) > 1:  # Make sure we have at least a header and one data row
        for row in rows[1:]:  # Skip header row
            cells = row.findall('.//{urn:schemas-microsoft-com:office:spreadsheet}Cell')
            
            if len(cells) >= 7:  # Ensure we have all required columns
                try:
                    # Extract data from cells with safety checks
                    def get_cell_text(cell):
                        data = cell.find('.//{urn:schemas-microsoft-com:office:spreadsheet}Data')
                        return data.text if data is not None else None
                    
                    date_time = get_cell_text(cells[0])
                    pump = get_cell_text(cells[1])
                    fuel_type = get_cell_text(cells[2])
                    amount_text = get_cell_text(cells[4])
                    volume_text = get_cell_text(cells[5])
                    product_code_text = get_cell_text(cells[6])
                    
                    # Skip row if any required field is missing
                    if not all([date_time, pump, fuel_type, amount_text, volume_text, product_code_text]):
                        errors += 1
                        continue
                    
                    # Convert numeric values
                    amount = float(amount_text)
                    volume = float(volume_text)
                    product_code = int(product_code_text)
                    
                    # Convert date string to datetime
                    date_time = datetime.strptime(date_time, '%d/%m/%Y %H:%M:%S')
                    
                    # Insert into database
                    cursor.execute('''
                        INSERT INTO fuel_data (
                            date_time, pump, fuel_type, amount, volume, product_code,
                            organization, sucursal
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        date_time, pump, fuel_type, amount, volume, product_code,
                        'Posta', 'Posta'
                    ))
                    records_processed += 1
                    
                except (AttributeError, ValueError, TypeError) as e:
                    print(f"Error processing row: {e}")
                    errors += 1
                    continue
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print(f"Processing complete. {records_processed} records inserted. {errors} errors encountered.")

if __name__ == '__main__':
    xml_file = 'data/POSTA/reportDispatchs (42).xml'
    if os.path.exists(xml_file):
        process_xml_file(xml_file)
    else:
        print(f"Error: File {xml_file} not found") 