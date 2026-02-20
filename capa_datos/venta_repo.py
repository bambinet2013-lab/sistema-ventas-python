"""
Repositorio para la gestión de ventas en la base de datos
"""
from loguru import logger

class VentaRepositorio:
    """Clase que maneja las operaciones de base de datos para ventas"""
    
    def __init__(self, conn):
        """
        Inicializa el repositorio con una conexión a la base de datos
        
        Args:
            conn: Conexión a la base de datos
        """
        self.conn = conn
    
    def listar(self):
        """
        Lista todas las ventas con fecha_hora formateada
        """
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT v.idventa, 
                   CONVERT(varchar, v.fecha_hora, 103) + ' ' + CONVERT(varchar, v.fecha_hora, 108) as fecha,
                   v.fecha_hora,
                   v.tipo_comprobante, 
                   v.serie, 
                   v.numero_comprobante, 
                   v.igv, 
                   v.estado,
                   ISNULL(c.nombre + ' ' + c.apellidos, 'CONSUMIDOR FINAL') as cliente,
                   t.nombre + ' ' + t.apellidos as trabajador
            FROM venta v
            LEFT JOIN cliente c ON v.idcliente = c.idcliente
            LEFT JOIN trabajador t ON v.idtrabajador = t.idtrabajador
            ORDER BY v.fecha_hora DESC
            """
            cursor.execute(query)
            
            # Obtener los nombres de las columnas
            columns = [column[0] for column in cursor.description]
            
            # Convertir las filas a diccionarios
            rows = cursor.fetchall()
            result = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    row_dict[col] = row[i]
                result.append(row_dict)
            
            logger.info(f"✅ {len(result)} ventas listadas")
            return result
            
        except Exception as e:
            logger.error(f"Error al listar ventas: {e}")
            return []
    
    def obtener_por_id(self, idventa):
        """
        Obtiene una venta por su ID
        
        Args:
            idventa (int): ID de la venta
            
        Returns:
            dict: Datos de la venta o None si no existe
        """
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT v.idventa, v.fecha, v.tipo_comprobante, 
                   v.serie, v.numero_comprobante, v.igv, v.estado,
                   c.nombre + ' ' + c.apellidos as cliente,
                   c.idcliente,
                   t.nombre + ' ' + t.apellidos as trabajador,
                   t.idtrabajador
            FROM venta v
            LEFT JOIN cliente c ON v.idcliente = c.idcliente
            LEFT JOIN trabajador t ON v.idtrabajador = t.idtrabajador
            WHERE v.idventa = ?
            """
            cursor.execute(query, (idventa,))
            
            columns = [column[0] for column in cursor.description]
            row = cursor.fetchone()
            
            if row:
                return dict(zip(columns, row))
            return None
            
        except Exception as e:
            logger.error(f"Error al obtener venta {idventa}: {e}")
            return None
    
    def crear(self, idtrabajador, idcliente, tipo_comprobante, 
              serie, numero_comprobante, igv, estado='REGISTRADO',
              moneda='VES', tasa_cambio=1.0, monto_bs=None, monto_divisa=None):
        """
        Inserta una nueva venta con soporte multimoneda
        """
        try:
            cursor = self.conn.cursor()
            
            query = """
            INSERT INTO venta 
            (idtrabajador, idcliente, fecha_hora, tipo_comprobante, 
             serie, numero_comprobante, igv, estado,
             moneda, tasa_cambio, monto_bs, monto_divisa)
            OUTPUT INSERTED.idventa
            VALUES (?, ?, GETDATE(), ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            cursor.execute(query, (
                idtrabajador, 
                idcliente,
                tipo_comprobante,
                serie, 
                numero_comprobante, 
                igv, 
                estado,
                moneda,
                tasa_cambio,
                monto_bs,
                monto_divisa
            ))
            
            row = cursor.fetchone()
            idventa = row[0] if row else None
            self.conn.commit()
            
            logger.info(f"✅ Venta #{idventa} creada - Moneda: {moneda} - Tasa: {tasa_cambio}")
            return idventa
            
        except Exception as e:
            logger.error(f"❌ Error al crear venta: {e}")
            self.conn.rollback()
            return None
    
    def agregar_detalle(self, idventa, idarticulo, cantidad, precio_venta):
        """
        Agrega un detalle a una venta
        
        Args:
            idventa (int): ID de la venta
            idarticulo (int): ID del artículo
            cantidad (int): Cantidad vendida
            precio_venta (float): Precio unitario
            
        Returns:
            int or None: ID del detalle creado o None si hay error
        """
        try:
            cursor = self.conn.cursor()
            
            query = """
            INSERT INTO detalle_venta 
            (idventa, idarticulo, cantidad, precio_venta)
            OUTPUT INSERTED.iddetalle_venta
            VALUES (?, ?, ?, ?)
            """
            
            cursor.execute(query, (idventa, idarticulo, cantidad, precio_venta))
            
            row = cursor.fetchone()
            iddetalle = row[0] if row else None
            
            self.conn.commit()
            
            logger.info(f"✅ Detalle de venta agregado: {cantidad} x {precio_venta}")
            return iddetalle
            
        except Exception as e:
            logger.error(f"❌ Error al agregar detalle: {e}")
            self.conn.rollback()
            return None
    
    def obtener_detalles(self, idventa):
        """
        Obtiene los detalles de una venta
        
        Args:
            idventa (int): ID de la venta
            
        Returns:
            list: Lista de detalles
        """
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT dv.iddetalle_venta, dv.cantidad, dv.precio_venta,
                   a.idarticulo, a.nombre as articulo, a.codigo
            FROM detalle_venta dv
            JOIN articulo a ON dv.idarticulo = a.idarticulo
            WHERE dv.idventa = ?
            """
            cursor.execute(query, (idventa,))
            
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            result = [dict(zip(columns, row)) for row in rows]
            
            return result
            
        except Exception as e:
            logger.error(f"Error al obtener detalles de venta {idventa}: {e}")
            return []
    
    def anular(self, idventa):
        """
        Anula una venta (cambia estado a ANULADO)
        
        Args:
            idventa (int): ID de la venta a anular
            
        Returns:
            bool: True si se anuló correctamente
        """
        try:
            cursor = self.conn.cursor()
            query = "UPDATE venta SET estado = 'ANULADO' WHERE idventa = ?"
            cursor.execute(query, (idventa,))
            self.conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"✅ Venta {idventa} anulada")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error al anular venta {idventa}: {e}")
            self.conn.rollback()
            return False
    
    def ventas_por_cliente(self, idcliente):
        """
        Obtiene todas las ventas de un cliente
        
        Args:
            idcliente (int): ID del cliente
            
        Returns:
            list: Lista de ventas
        """
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT v.idventa, v.fecha, v.tipo_comprobante, 
                   v.serie, v.numero_comprobante, v.igv, v.estado,
                   v.idcliente
            FROM venta v
            WHERE v.idcliente = ?
            ORDER BY v.fecha DESC
            """
            cursor.execute(query, (idcliente,))
            
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            result = [dict(zip(columns, row)) for row in rows]
            
            return result
            
        except Exception as e:
            logger.error(f"Error al obtener ventas del cliente {idcliente}: {e}")
            return []
    
    def ventas_por_fecha(self, fecha_inicio, fecha_fin):
        """
        Obtiene ventas en un rango de fechas
        
        Args:
            fecha_inicio: Fecha inicial
            fecha_fin: Fecha final
            
        Returns:
            list: Lista de ventas
        """
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT v.idventa, v.fecha, v.tipo_comprobante, 
                   v.serie, v.numero_comprobante, v.igv, v.estado,
                   c.nombre + ' ' + c.apellidos as cliente,
                   t.nombre + ' ' + t.apellidos as trabajador
            FROM venta v
            LEFT JOIN cliente c ON v.idcliente = c.idcliente
            LEFT JOIN trabajador t ON v.idtrabajador = t.idtrabajador
            WHERE CAST(v.fecha AS DATE) BETWEEN ? AND ?
            ORDER BY v.fecha DESC
            """
            cursor.execute(query, (fecha_inicio, fecha_fin))
            
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            result = [dict(zip(columns, row)) for row in rows]
            
            return result
            
        except Exception as e:
            logger.error(f"Error al obtener ventas por fecha: {e}")
            return []
