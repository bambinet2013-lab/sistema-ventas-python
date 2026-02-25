"""
Repositorio para gestión de inventario (Kardex)
"""
from loguru import logger
from capa_datos.conexion import ConexionDB

class InventarioRepositorio:
    def __init__(self):
        """Inicializa el repositorio de inventario"""
        self.db = ConexionDB()
        self.conn = self.db.conectar()
    
    def obtener_stock_actual(self, idarticulo):
        """
        Obtiene el stock actual de un artículo desde kardex
        
        Args:
            idarticulo: ID del artículo
            
        Returns:
            int: Stock actual, 0 si no hay registros
        """
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT TOP 1 stock_nuevo 
            FROM kardex 
            WHERE idarticulo = ? 
            ORDER BY fecha_movimiento DESC
            """
            cursor.execute(query, (idarticulo,))
            resultado = cursor.fetchone()
            
            if resultado:
                return resultado[0]
            return 0
            
        except Exception as e:
            logger.error(f"Error obteniendo stock actual para artículo {idarticulo}: {e}")
            return 0
    
    def registrar_movimiento(self, idarticulo, tipo_movimiento, cantidad,
                            referencia, precio_compra=None, lote=None,
                            fecha_vencimiento=None):
        """
        Registra un movimiento en la tabla kardex
        
        Args:
            idarticulo: ID del artículo
            tipo_movimiento: 'INGRESO' o 'SALIDA' (valores permitidos por la BD)
            cantidad: Cantidad
            referencia: Documento de referencia
            precio_compra: Precio unitario (opcional)
            lote: Número de lote (no se usa en esta estructura)
            fecha_vencimiento: Fecha de vencimiento (no se usa en esta estructura)
            
        Returns:
            bool: True si se registró correctamente
        """
        try:
            cursor = self.conn.cursor()
            
            # Obtener stock actual
            stock_actual = self.obtener_stock_actual(idarticulo)
            
            # Validar y convertir tipo_movimiento a valores permitidos
            tipo_valido = tipo_movimiento
            if tipo_movimiento == 'ENTRADA':
                tipo_valido = 'INGRESO'  # Asumimos que acepta 'INGRESO'
            
            # Calcular stock nuevo
            if tipo_movimiento == 'ENTRADA':
                stock_nuevo = stock_actual + cantidad
            else:  # SALIDA
                stock_nuevo = stock_actual - cantidad
            
            # Calcular valor total
            valor_total = cantidad * precio_compra if precio_compra else 0
            
            query = """
            INSERT INTO kardex 
            (idarticulo, fecha_movimiento, tipo_movimiento, documento_referencia,
             cantidad, precio_unitario, valor_total, stock_anterior, stock_nuevo)
            VALUES (?, GETDATE(), ?, ?, ?, ?, ?, ?, ?)
            """
            
            cursor.execute(query, (
                idarticulo, tipo_valido, referencia,
                cantidad, precio_compra, valor_total,
                stock_actual, stock_nuevo
            ))
            
            self.conn.commit()
            logger.info(f"✅ Movimiento registrado en kardex: {tipo_valido} {cantidad} und - Art {idarticulo}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error registrando movimiento en kardex: {e}")
            self.conn.rollback()
            return False
    
    def obtener_movimientos_articulo(self, idarticulo, limite=100):
        """
        Obtiene los últimos movimientos de un artículo
        
        Args:
            idarticulo: ID del artículo
            limite: Número máximo de registros
            
        Returns:
            list: Lista de movimientos
        """
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT * FROM kardex 
            WHERE idarticulo = ? 
            ORDER BY fecha_movimiento DESC
            """
            cursor.execute(query, (idarticulo,))
            
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()][:limite]
            
        except Exception as e:
            logger.error(f"Error obteniendo movimientos para artículo {idarticulo}: {e}")
            return []
    
    def cerrar_conexion(self):
        """Cierra la conexión a la base de datos"""
        try:
            if hasattr(self, 'db'):
                self.db.cerrar()
        except:
            pass
