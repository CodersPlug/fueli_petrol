import sqlite3
from datetime import datetime

def update_dates_to_2025():
    """Update all dates in the database to 2025 while preserving the month and day."""
    conn = sqlite3.connect('data/fueli.db')
    cursor = conn.cursor()
    
    # Get total records count before update
    cursor.execute("SELECT COUNT(*) FROM despachos")
    total_records = cursor.fetchone()[0]
    
    # Update all records in a single SQL statement
    cursor.execute("""
        UPDATE despachos 
        SET fecha = substr('2025' || substr(fecha, 5), 1, 10)
        WHERE fecha IS NOT NULL
    """)
    
    # Commit the changes
    conn.commit()
    
    # Print summary
    print(f"Updated all {total_records} records to 2025")
    
    # Close the connection
    conn.close()

if __name__ == "__main__":
    update_dates_to_2025() 