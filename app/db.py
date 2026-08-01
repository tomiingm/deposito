import os
import mysql.connector
from mysql.connector import Error
import logging

# Configurar logging básico
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_connection():
    """
    Establece y retorna una conexión a la base de datos MySQL.
    
    NOTA: En un entorno de producción, las credenciales deben ser provistas
    a través de variables de entorno (ej. usando un archivo .env).
    """
    try:
        connection = mysql.connector.connect(
            host=os.environ.get('DB_HOST', 'localhost'),
            user=os.environ.get('DB_USER', 'root'),
            password=os.environ.get('DB_PASSWORD', ''),
            database=os.environ.get('DB_NAME', 'deposito')
        )
        if connection.is_connected():
            return connection
    except Error as e:
        logger.error(f"Error al conectar a la base de datos MySQL: {e}")
        return None
