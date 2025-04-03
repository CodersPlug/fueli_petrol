import sqlite3

def delete_gnc_data():
    """Delete GNC data from Posta stations (excluding Cepia)."""
    conn = sqlite3.connect('data/fueli.db')
    cursor = conn.cursor()
    
    # Get count before deletion
    cursor.execute("""
        SELECT COUNT(*) 
        FROM despachos 
        WHERE producto LIKE '%GNC%' 
        AND sucursal IN ('Posta Erezcano', 'Posta Hersu')
    """)
    records_to_delete = cursor.fetchone()[0]
    
    # Delete the records
    cursor.execute("""
        DELETE FROM despachos 
        WHERE producto LIKE '%GNC%' 
        AND sucursal IN ('Posta Erezcano', 'Posta Hersu')
    """)
    
    # Commit the changes
    conn.commit()
    
    # Get total count after deletion
    cursor.execute("SELECT COUNT(*) FROM despachos")
    total_records = cursor.fetchone()[0]
    
    print(f"Deleted {records_to_delete} GNC records from Posta Erezcano and Posta Hersu")
    print(f"Total records remaining in database: {total_records}")
    
    # Close the connection
    conn.close()

if __name__ == "__main__":
    delete_gnc_data() 