"""
Repositorio para log de auditoría
"""
from loguru import logger

class AuditoriaRepositorio:
    """Maneja las operaciones de BD para auditoría"""
    
    def __init__(self, conn):
        """
        Inicializa el repositorio con una conexión a la BD
        
        Args:
            conn: Conexión a la base de datos
        """
        self.conn = conn
    
    def insertar(self, usuario, accion, tabla, registro_id, 
                 datos_anteriores, datos_nuevos, ip_address):
        """
        Inserta un registro en el log de auditoría
        
        Returns:
            bool: True si se insertó correctamente
        """
        try:
            cursor = self.conn.cursor()
            query = """
            INSERT INTO log_auditoria 
            (usuario, accion, tabla_afectada, registro_id, 
             datos_anteriores, datos_nuevos, ip_address, fecha_hora)
            VALUES (?, ?, ?, ?, ?, ?, ?, GETDATE())
            """
            cursor.execute(query, (
                usuario, accion, tabla, registro_id,
                datos_anteriores, datos_nuevos, ip_address
            ))
            self.conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error insertando auditoría: {e}")
            self.conn.rollback()
            return False
    
    def consultar_por_fecha(self, fecha_inicio, fecha_fin):
        """
        Consulta registros de auditoría por rango de fechas
        """
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT * FROM log_auditoria 
            WHERE fecha_hora BETWEEN ? AND ?
            ORDER BY fecha_hora DESC
            """
            cursor.execute(query, (fecha_inicio, fecha_fin))
            
            # Convertir a diccionario
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            result = [dict(zip(columns, row)) for row in rows]
            
            return result
            
        except Exception as e:
            logger.error(f"Error consultando auditoría: {e}")
            return []
    
    def consultar_por_usuario(self, usuario):
        """
        Consulta registros de un usuario específico
        """
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT * FROM log_auditoria 
            WHERE usuario = ?
            ORDER BY fecha_hora DESC
            """
            cursor.execute(query, (usuario,))
            
            # Convertir a diccionario
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            result = [dict(zip(columns, row)) for row in rows]
            
            return result
            
        except Exception as e:
            logger.error(f"Error consultando auditoría: {e}")
            return []
    
    def consultar_por_tabla(self, tabla, registro_id):
        """
        Consulta historial de cambios en un registro específico
        """
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT * FROM log_auditoria 
            WHERE tabla_afectada = ? AND registro_id = ?
            ORDER BY fecha_hora DESC
            """
            cursor.execute(query, (tabla, registro_id))
            
            # Convertir a diccionario
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            result = [dict(zip(columns, row)) for row in rows]
            
            return result
            
        except Exception as e:
            logger.error(f"Error consultando auditoría: {e}")
            return []
