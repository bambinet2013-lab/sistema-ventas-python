"""
Repositorio para gestión de compras
"""
from loguru import logger
from capa_datos.conexion import obtener_conexion

class CompraRepositorio:
    def __init__(self):
        self.conn = obtener_conexion()
    
    def crear(self, idproveedor, idtrabajador, tipo_comprobante, serie, numero,
              subtotal, iva, total, observaciones=None):
        try:
            cursor = self.conn.cursor()
            query = """
            INSERT INTO compra 
            (idproveedor, idtrabajador, fecha_hora, tipo_comprobante, serie, 
             numero_comprobante, subtotal, iva, total, estado, observaciones)
            OUTPUT INSERTED.idcompra
            VALUES (?, ?, GETDATE(), ?, ?, ?, ?, ?, ?, 'REGISTRADA', ?)
            """
            cursor.execute(query, (idproveedor, idtrabajador, tipo_comprobante, 
                                  serie, numero, subtotal, iva, total, observaciones))
            idcompra = cursor.fetchone()[0]
            self.conn.commit()
            logger.info(f"Compra #{idcompra} creada")
            return idcompra
        except Exception as e:
            logger.error(f"Error creando compra: {e}")
            self.conn.rollback()
            return None
    
    def agregar_detalle(self, idcompra, idarticulo, cantidad, precio_compra, subtotal):
        try:
            cursor = self.conn.cursor()
            query = """
            INSERT INTO detalle_compra (idcompra, idarticulo, cantidad, precio_compra, subtotal)
            OUTPUT INSERTED.iddetalle_compra
            VALUES (?, ?, ?, ?, ?)
            """
            cursor.execute(query, (idcompra, idarticulo, cantidad, precio_compra, subtotal))
            iddetalle = cursor.fetchone()[0]
            self.conn.commit()
            return iddetalle
        except Exception as e:
            logger.error(f"Error agregando detalle: {e}")
            self.conn.rollback()
            return None
    
    def listar(self):
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT c.idcompra, c.fecha_hora, c.tipo_comprobante, c.serie, c.numero_comprobante,
                   c.subtotal, c.iva, c.total, c.estado,
                   p.razon_social as proveedor,
                   t.nombre + ' ' + t.apellidos as trabajador
            FROM compra c
            JOIN proveedor p ON c.idproveedor = p.idproveedor
            JOIN trabajador t ON c.idtrabajador = t.idtrabajador
            ORDER BY c.fecha_hora DESC
            """
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error listando compras: {e}")
            return []
    
    def buscar_por_id(self, idcompra):
        try:
            cursor = self.conn.cursor()
            
            query = """
            SELECT c.*, p.razon_social as proveedor, p.rif,
                   t.nombre + ' ' + t.apellidos as trabajador
            FROM compra c
            JOIN proveedor p ON c.idproveedor = p.idproveedor
            JOIN trabajador t ON c.idtrabajador = t.idtrabajador
            WHERE c.idcompra = ?
            """
            cursor.execute(query, (idcompra,))
            cabecera = cursor.fetchone()
            
            if not cabecera:
                return None
            
            columns = [col[0] for col in cursor.description]
            resultado = dict(zip(columns, cabecera))
            
            query = """
            SELECT d.*, a.nombre as articulo, a.codigo_barras
            FROM detalle_compra d
            JOIN articulo a ON d.idarticulo = a.idarticulo
            WHERE d.idcompra = ?
            """
            cursor.execute(query, (idcompra,))
            detalles = cursor.fetchall()
            
            det_columns = [col[0] for col in cursor.description]
            resultado['detalles'] = [dict(zip(det_columns, row)) for row in detalles]
            
            return resultado
        except Exception as e:
            logger.error(f"Error buscando compra {idcompra}: {e}")
            return None
    
    def anular(self, idcompra):
        try:
            cursor = self.conn.cursor()
            query = "UPDATE compra SET estado = 'ANULADA' WHERE idcompra = ?"
            cursor.execute(query, (idcompra,))
            self.conn.commit()
            logger.info(f"Compra #{idcompra} anulada")
            return True
        except Exception as e:
            logger.error(f"Error anulando compra: {e}")
            self.conn.rollback()
            return False
