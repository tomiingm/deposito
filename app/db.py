import os
import mysql.connector
from mysql.connector import Error
import logging
from dotenv import load_dotenv

load_dotenv()

# Configurar logging básico
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_connection():
    """
    Establece y retorna una conexión a la base de datos MySQL.
    """
    try:
        connection = mysql.connector.connect(
            # Si la variable no está en el .env, usará el segundo parámetro como respaldo (opcional)
            host=os.environ.get('DB_HOST', 'localhost'),
            user=os.environ.get('DB_USER', 'root'),
            password=os.environ.get('DB_PASSWORD'),
            database=os.environ.get('DB_NAME', 'deposito')
        )
        if connection.is_connected():
            return connection
    except Error as e:
        logger.error(f"Error al conectar a la base de datos MySQL: {e}")
        return None