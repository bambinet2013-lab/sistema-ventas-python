import pyodbc
import os
from dotenv import load_dotenv
from loguru import logger

# Cargar variables de entorno
load_dotenv()

class ConexionDB:
    """Singleton para manejar la conexión a SQL Server"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._inicializar()
        return cls._instance
    
    def _inicializar(self):
        self.server = os.getenv('DB_SERVER', 'localhost,1433')
        self.database = os.getenv('DB_NAME', 'SistemaVentas')
        self.username = os.getenv('DB_USER', 'sa')
        self.password = os.getenv('DB_PASSWORD', 'Santi07.')
        self.driver = os.getenv('DB_DRIVER', '{ODBC Driver 18 for SQL Server}')
        self.conn = None
    
    def conectar(self):
        """Establece conexión con la base de datos"""
        try:
            conn_str = (
                f"DRIVER={self.driver};"
                f"SERVER={self.server};"
                f"DATABASE={self.database};"
                f"UID={self.username};"
                f"PWD={self.password};"
                f"TrustServerCertificate=yes;"
            )
            self.conn = pyodbc.connect(conn_str)
            logger.success("✅ Conexión exitosa a SQL Server")
            return self.conn
        except Exception as e:
            logger.error(f"❌ Error de conexión: {e}")
            return None
    
    def cerrar(self):
        if self.conn:
            self.conn.close()
            logger.info("🔒 Conexión cerrada")
