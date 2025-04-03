import xml.etree.ElementTree as ET
import pandas as pd

def process_excel_xml_file(file_path):
    """Process Excel XML file and return DataFrame with standardized columns."""
    try:
        # Read the XML file
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Find the Table element containing the data
        table = root.find('.//Table')
        if table is None:
            print(f"Warning: No Table element found in {file_path}")
            return None
            
        # Extract data from rows
        data = []
        for row in table.findall('Row'):
            cells = row.findall('Cell')
            if len(cells) >= 7:  # Ensure we have enough cells
                try:
                    # Extract date and time
                    date_time = cells[0].find('Data').text
                    date, time = date_time.split(' ')
                    
                    # Extract other fields
                    pump = cells[1].find('Data').text
                    product = cells[2].find('Data').text
                    controller = cells[3].find('Data').text
                    amount = float(cells[4].find('Data').text)
                    volume = float(cells[5].find('Data').text)
                    product_code = cells[6].find('Data').text
                    
                    # Calculate PPU
                    ppu = amount / volume if volume > 0 else 0
                    
                    data.append({
                        'date': date,
                        'time': time,
                        'pump': pump,
                        'product': product,
                        'controller': controller,
                        'amount': amount,
                        'volume': volume,
                        'product_code': product_code,
                        'ppu': ppu
                    })
                except (ValueError, AttributeError) as e:
                    print(f"Warning: Error processing row in {file_path}: {e}")
                    continue
        
        if not data:
            print(f"Warning: No valid data found in {file_path}")
            return None
            
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Standardize column names
        df = standardize_columns(df)
        
        return df
        
    except Exception as e:
        print(f"Error processing Excel XML file {file_path}: {e}")
        return None 