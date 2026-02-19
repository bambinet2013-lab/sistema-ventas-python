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
        Lista todas las ventas
        
        Returns:
            list: Lista de ventas o lista vacía si hay error
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
            ORDER BY v.fecha DESC
            """
            cursor.execute(query)
            
            # Convertir a lista de diccionarios
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            result = [dict(zip(columns, row)) for row in rows]
            
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
              serie, numero_comprobante, igv, estado='REGISTRADO'):
        """
        Inserta una nueva venta (idcliente puede ser NULL)
        
        Args:
            idtrabajador (int): ID del trabajador
            idcliente (int or None): ID del cliente (puede ser None)
            tipo_comprobante (str): FACTURA, BOLETA, TICKET
            serie (str): Serie del comprobante
            numero_comprobante (str): Número del comprobante
            igv (float): Porcentaje de IGV
            estado (str): Estado de la venta
            
        Returns:
            int or None: ID de la venta creada o None si hay error
        """
        try:
            cursor = self.conn.cursor()
            
            # Construir la consulta
            query = """
            INSERT INTO venta 
            (idtrabajador, idcliente, fecha, tipo_comprobante, 
             serie, numero_comprobante, igv, estado)
            OUTPUT INSERTED.idventa
            VALUES (?, ?, GETDATE(), ?, ?, ?, ?, ?)
            """
            
            # Ejecutar la consulta
            cursor.execute(query, (
                idtrabajador, 
                idcliente,  # Puede ser None
                tipo_comprobante,
                serie, 
                numero_comprobante, 
                igv, 
                estado
            ))
            
            # Obtener el ID insertado
            row = cursor.fetchone()
            idventa = row[0] if row else None
            
            # Confirmar la transacción
            self.conn.commit()
            
            logger.info(f"✅ Venta creada con ID: {idventa}")
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
