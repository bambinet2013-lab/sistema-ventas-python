"""
Repositorio para gestión de órdenes de compra
"""
from loguru import logger
from capa_datos.conexion import ConexionDB

class OrdenCompraRepositorio:
    def __init__(self):
        self.db = ConexionDB()
        self.conn = self.db.conectar()
    
    def crear(self, codigo_factura, idproveedor, idtrabajador, fecha_compra,
              monto_total_usd, monto_total_bs, tasa_bcv, fecha_estimada_llegada,
              archivo_adjunto, estatus, observaciones):
        """Crea una nueva orden de compra"""
        try:
            cursor = self.conn.cursor()
            query = """
            INSERT INTO orden_compra 
            (codigo_factura, idproveedor, idtrabajador, fecha_orden, fecha_compra,
             fecha_estimada_llegada, monto_total_usd, monto_total_bs, tasa_bcv,
             archivo_adjunto, estatus, observaciones)
            OUTPUT INSERTED.idorden
            VALUES (?, ?, ?, GETDATE(), ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(query, (
                codigo_factura, idproveedor, idtrabajador, fecha_compra,
                fecha_estimada_llegada, monto_total_usd, monto_total_bs, tasa_bcv,
                archivo_adjunto, estatus, observaciones
            ))
            idorden = cursor.fetchone()[0]
            self.conn.commit()
            return idorden
        except Exception as e:
            logger.error(f"Error creando orden: {e}")
            self.conn.rollback()
            return None
    
    def buscar_por_codigo_factura(self, codigo_factura):
        """Busca orden por código de factura"""
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT o.*, p.razon_social as proveedor, p.num_documento as rif,
                   t.nombre + ' ' + t.apellidos as trabajador
            FROM orden_compra o
            JOIN proveedor p ON o.idproveedor = p.idproveedor
            JOIN trabajador t ON o.idtrabajador = t.idtrabajador
            WHERE o.codigo_factura = ?
            """
            cursor.execute(query, (codigo_factura,))
            row = cursor.fetchone()
            if row:
                columns = [col[0] for col in cursor.description]
                return dict(zip(columns, row))
            return None
        except Exception as e:
            logger.error(f"Error buscando orden: {e}")
            return None
    
    def listar_por_estatus(self, estatus):
        """Lista órdenes por estatus"""
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT o.*, p.razon_social as proveedor
            FROM orden_compra o
            JOIN proveedor p ON o.idproveedor = p.idproveedor
            WHERE o.estatus = ?
            ORDER BY o.fecha_orden DESC
            """
            cursor.execute(query, (estatus,))
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error listando órdenes: {e}")
            return []
    
    def actualizar_estatus(self, idorden, estatus):
        """Actualiza estatus de la orden"""
        try:
            cursor = self.conn.cursor()
            query = "UPDATE orden_compra SET estatus = ? WHERE idorden = ?"
            cursor.execute(query, (estatus, idorden))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error actualizando estatus: {e}")
            self.conn.rollback()
            return False
    
    def __del__(self):
        try:
            if hasattr(self, 'db'):
                self.db.cerrar()
        except:
            pass
