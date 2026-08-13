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
        cursor.execute("ALTER TABLE producto ADD COLUMN activo TINYINT(1) DEFAULT 1;")
        conn.commit()
        print("Migration successful: Added 'activo' column.")
    except Exception as e:
        print(f"Migration error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    migrate()
