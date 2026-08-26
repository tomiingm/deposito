import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from app.db import get_connection

def migrate():
    conn = get_connection()
    if not conn:
        print("Error: Could not connect to DB.")
        return
    cursor = conn.cursor()
    try:
        # Check if column exists
        cursor.execute("SHOW COLUMNS FROM cliente LIKE 'telefono'")
        result = cursor.fetchone()
        if not result:
            cursor.execute("ALTER TABLE cliente ADD COLUMN telefono VARCHAR(30) NULL AFTER nombre;")
            conn.commit()
            print("Migration successful: Added 'telefono' column to 'cliente' table.")
        else:
            print("Column 'telefono' already exists in 'cliente' table.")
    except Exception as e:
        print(f"Migration error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    migrate()
