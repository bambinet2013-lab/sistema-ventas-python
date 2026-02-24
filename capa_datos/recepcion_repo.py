"""
Repositorio para gestión de recepciones de mercancía
"""
from loguru import logger
from capa_datos.conexion import obtener_conexion

class RecepcionRepositorio:
    def __init__(self):
        self.conn = obtener_conexion()
    
    def crear_recepcion(self, idproveedor, idtrabajador, idcompra_original=None, observaciones=None):
        """Crea una nueva recepción"""
        try:
            cursor = self.conn.cursor()
            query = """
            INSERT INTO recepcion (idcompra_original, idproveedor, idtrabajador, 
                                   fecha_recepcion, observaciones, estatus)
            OUTPUT INSERTED.idrecepcion
            VALUES (?, ?, ?, GETDATE(), ?, 'RECIBIDA')
            """
            cursor.execute(query, (idcompra_original, idproveedor, idtrabajador, observaciones))
            idrecepcion = cursor.fetchone()[0]
            self.conn.commit()
            logger.info(f"✅ Recepción #{idrecepcion} creada")
            return idrecepcion
        except Exception as e:
            logger.error(f"❌ Error creando recepción: {e}")
            self.conn.rollback()
            return None
    
    def agregar_detalle(self, idrecepcion, idarticulo, cantidad_recibida, costo_unitario_usd, 
                        tasa_bcv, iddetalle_compra_original=None, cantidad_pedida=None, 
                        lote=None, fecha_vencimiento=None):
        """Agrega un detalle a la recepción"""
        try:
            subtotal_usd = cantidad_recibida * costo_unitario_usd
            subtotal_bs = subtotal_usd * tasa_bcv
            
            cursor = self.conn.cursor()
            query = """
            INSERT INTO detalle_recepcion 
            (idrecepcion, idarticulo, iddetalle_compra_original, cantidad_pedida, 
             cantidad_recibida, costo_unitario_usd, tasa_bcv, subtotal_usd, subtotal_bs,
             lote, fecha_vencimiento)
            OUTPUT INSERTED.iddetalle
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(query, (idrecepcion, idarticulo, iddetalle_compra_original, 
                                  cantidad_pedida, cantidad_recibida, costo_unitario_usd, 
                                  tasa_bcv, subtotal_usd, subtotal_bs, lote, fecha_vencimiento))
            iddetalle = cursor.fetchone()[0]
            self.conn.commit()
            return iddetalle
        except Exception as e:
            logger.error(f"❌ Error agregando detalle a recepción: {e}")
            self.conn.rollback()
            return None
    
    def buscar_recepciones_pendientes(self, idcompra=None):
        """Busca recepciones pendientes (para completar órdenes)"""
        try:
            cursor = self.conn.cursor()
            if idcompra:
                query = """
                SELECT r.*, p.razon_social as proveedor
                FROM recepcion r
                JOIN proveedor p ON r.idproveedor = p.idproveedor
                WHERE r.idcompra_original = ? AND r.estatus = 'RECIBIDA'
                ORDER BY r.fecha_recepcion DESC
                """
                cursor.execute(query, (idcompra,))
            else:
                query = """
                SELECT r.*, p.razon_social as proveedor
                FROM recepcion r
                JOIN proveedor p ON r.idproveedor = p.idproveedor
                WHERE r.estatus = 'RECIBIDA'
                ORDER BY r.fecha_recepcion DESC
                """
                cursor.execute(query)
            
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ Error buscando recepciones: {e}")
            return []
    
    def obtener_detalles_recepcion(self, idrecepcion):
        """Obtiene los detalles de una recepción"""
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT d.*, a.nombre as articulo, a.codigo_barras
            FROM detalle_recepcion d
            JOIN articulo a ON d.idarticulo = a.idarticulo
            WHERE d.idrecepcion = ?
            """
            cursor.execute(query, (idrecepcion,))
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ Error obteniendo detalles: {e}")
            return []
