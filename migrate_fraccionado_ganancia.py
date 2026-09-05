"""
Migración: Agregar columnas fraccionado, cantidad_fracciones y metodo_ganancia
a la tabla producto.

- fraccionado (TINYINT, default 0): Indica si el producto se vende fraccionado.
- cantidad_fracciones (INT, default NULL): Cuántas fracciones salen del paquete.
- metodo_ganancia (TINYINT, default 1): 1 = porcentaje, 0 = suma fija.
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

    columnas_a_agregar = [
        ("fraccionado", "TINYINT DEFAULT 0"),
        ("cantidad_fracciones", "INT DEFAULT NULL"),
        ("metodo_ganancia", "TINYINT DEFAULT 1"),
    ]

    try:
        # Verificar qué columnas ya existen
        cursor.execute("SHOW COLUMNS FROM producto")
        columnas_existentes = {row[0] for row in cursor.fetchall()}

        for col_name, col_def in columnas_a_agregar:
            if col_name in columnas_existentes:
                print(f"  ✓ Columna '{col_name}' ya existe, se omite.")
            else:
                sql = f"ALTER TABLE producto ADD COLUMN {col_name} {col_def}"
                cursor.execute(sql)
                print(f"  + Columna '{col_name}' agregada correctamente.")

        conn.commit()
        print("\nMigración completada exitosamente.")

    except Exception as e:
        conn.rollback()
        print(f"ERROR durante la migración: {e}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    migrate()
