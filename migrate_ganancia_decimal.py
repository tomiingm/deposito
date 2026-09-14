"""
Migración: Modificar la columna ganancia de la tabla producto a DECIMAL(12,2)
para permitir montos fijos o ganancias de más de 4 dígitos (superiores a 999.99).
"""

import os
import sys

# Agregar el directorio raíz del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import get_connection


def migrate():
    conn = get_connection()
    if not conn:
        print("ERROR: No se pudo conectar a la base de datos.")
        sys.exit(1)

    cursor = conn.cursor()

    try:
        print("Modificando columna 'ganancia' en tabla 'producto' a DECIMAL(12,2)...")
        cursor.execute("ALTER TABLE producto MODIFY COLUMN ganancia DECIMAL(12,2) DEFAULT NULL")
        conn.commit()
        print("[OK] Columna 'ganancia' modificada exitosamente a DECIMAL(12,2).")

    except Exception as e:
        conn.rollback()
        print(f"ERROR durante la migración: {e}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    migrate()
