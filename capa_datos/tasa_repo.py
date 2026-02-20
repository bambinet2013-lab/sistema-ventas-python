"""
Repositorio para gestión de tasas de cambio
"""
from loguru import logger

class TasaRepositorio:
    """Maneja operaciones de BD para tasas de cambio"""
    
    def __init__(self, conn):
        """
        Inicializa el repositorio con una conexión a la BD
        
        Args:
            conn: Conexión a la base de datos
        """
        self.conn = conn
        logger.info("✅ TasaRepositorio inicializado")
    
    def obtener_ultima_tasa(self, moneda='USD'):
        """
        Obtiene la última tasa registrada para una moneda
        
        Args:
            moneda (str): USD, EUR
            
        Returns:
            float: Tasa o None si no existe
        """
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT TOP 1 tasa 
            FROM tasa_cambio 
            WHERE moneda_origen = ? 
            ORDER BY fecha_hora_registro DESC
            """
            cursor.execute(query, (moneda,))
            row = cursor.fetchone()
            
            if row and row[0] is not None:
                tasa = float(row[0])
                logger.info(f"✅ Última tasa {moneda}: {tasa:.2f}")
                return tasa
            else:
                logger.warning(f"⚠️ No hay tasa registrada para {moneda}")
                return None
            
        except Exception as e:
            logger.error(f"Error obteniendo última tasa: {e}")
            return None
    
    def insertar_tasa(self, idfuente, moneda_origen, tasa, 
                      usuario=None, observaciones=None):
        """
        Inserta una nueva tasa en el histórico
        
        Args:
            idfuente (int): ID de la fuente (1 = MANUAL)
            moneda_origen (str): USD, EUR
            tasa (float): Valor de la tasa
            usuario (str): Nombre del usuario que registra
            observaciones (str): Observaciones adicionales
            
        Returns:
            bool: True si se insertó correctamente
        """
        try:
            cursor = self.conn.cursor()
            query = """
            INSERT INTO tasa_cambio 
            (idfuente, moneda_origen, moneda_destino, tasa, 
             fecha, fecha_hora_registro, usuario_registro, observaciones)
            VALUES (?, ?, 'VES', ?, CAST(GETDATE() AS DATE), GETDATE(), ?, ?)
            """
            cursor.execute(query, (idfuente, moneda_origen, tasa, usuario, observaciones))
            self.conn.commit()
            logger.info(f"✅ Tasa {moneda_origen} registrada: {tasa:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"Error insertando tasa: {e}")
            self.conn.rollback()
            return False
    
    def obtener_historial(self, moneda='USD', dias=30):
        """
        Obtiene historial de tasas para una moneda
        
        Args:
            moneda (str): USD, EUR
            dias (int): Número de días hacia atrás
            
        Returns:
            list: Lista de tasas históricas
        """
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT 
                t.idtasa,
                t.fecha,
                t.tasa,
                f.nombre as fuente,
                t.usuario_registro,
                t.fecha_hora_registro
            FROM tasa_cambio t
            INNER JOIN fuente_tasa f ON t.idfuente = f.idfuente
            WHERE t.moneda_origen = ? 
              AND t.fecha >= DATEADD(day, -?, GETDATE())
            ORDER BY t.fecha DESC, t.fecha_hora_registro DESC
            """
            cursor.execute(query, (moneda, dias))
            
            # Convertir a diccionarios
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            result = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    row_dict[col] = row[i]
                result.append(row_dict)
            
            return result
            
        except Exception as e:
            logger.error(f"Error obteniendo historial: {e}")
            return []
    
    def obtener_tasas_del_dia(self):
        """
        Obtiene todas las tasas registradas hoy
        
        Returns:
            list: Lista de tasas del día
        """
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT 
                moneda_origen,
                tasa,
                usuario_registro,
                fecha_hora_registro
            FROM tasa_cambio 
            WHERE CAST(fecha_hora_registro AS DATE) = CAST(GETDATE() AS DATE)
            ORDER BY moneda_origen, fecha_hora_registro DESC
            """
            cursor.execute(query)
            
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            result = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    row_dict[col] = row[i]
                result.append(row_dict)
            
            return result
            
        except Exception as e:
            logger.error(f"Error obteniendo tasas del día: {e}")
            return []
