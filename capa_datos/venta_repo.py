from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger

class VentaRepositorio:
    """Repositorio para operaciones CRUD de ventas"""
    
    def __init__(self, conexion):
        self.conexion = conexion
        self.cursor = conexion.cursor()
    
    def listar(self) -> List[Dict]:
        """Lista todas las ventas"""
        try:
            query = """
                SELECT v.idventa, v.fecha, v.tipo_comprobante, v.serie, v.numero_comprobante,
                       v.igv, v.estado,
                       c.nombre + ' ' + c.apellidos as cliente,
                       t.nombre + ' ' + t.apellidos as trabajador
                FROM venta v
                INNER JOIN cliente c ON v.idcliente = c.idcliente
                INNER JOIN trabajador t ON v.idtrabajador = t.idtrabajador
                ORDER BY v.fecha DESC
            """
            self.cursor.execute(query)
            columnas = [column[0] for column in self.cursor.description]
            resultados = []
            for row in self.cursor.fetchall():
                resultados.append(dict(zip(columnas, row)))
            logger.info(f"✅ {len(resultados)} ventas listadas")
            return resultados
        except Exception as e:
            logger.error(f"❌ Error al listar ventas: {e}")
            return []
    
    def obtener_por_id(self, idventa: int) -> Optional[Dict]:
        """Obtiene una venta por su ID con su detalle"""
        try:
            # Obtener cabecera
            self.cursor.execute("""
                SELECT v.*, c.nombre + ' ' + c.apellidos as cliente,
                       t.nombre + ' ' + t.apellidos as trabajador
                FROM venta v
                INNER JOIN cliente c ON v.idcliente = c.idcliente
                INNER JOIN trabajador t ON v.idtrabajador = t.idtrabajador
                WHERE v.idventa = ?
            """, (idventa,))
            row = self.cursor.fetchone()
            
            if not row:
                return None
            
            columnas = [column[0] for column in self.cursor.description]
            venta = dict(zip(columnas, row))
            
            # Obtener detalle
            venta['detalle'] = self.obtener_detalle(idventa)
            
            return venta
        except Exception as e:
            logger.error(f"❌ Error al obtener venta {idventa}: {e}")
            return None
    
    def obtener_detalle(self, idventa: int) -> List[Dict]:
        """Obtiene el detalle de una venta"""
        try:
            self.cursor.execute("""
                SELECT dv.iddetalle_venta, dv.cantidad, dv.precio_venta,
                       a.idarticulo, a.codigo, a.nombre as articulo
                FROM detalle_venta dv
                INNER JOIN articulo a ON dv.idarticulo = a.idarticulo
                WHERE dv.idventa = ?
            """, (idventa,))
            columnas = [column[0] for column in self.cursor.description]
            resultados = []
            for row in self.cursor.fetchall():
                resultados.append(dict(zip(columnas, row)))
            return resultados
        except Exception as e:
            logger.error(f"❌ Error al obtener detalle de la venta: {e}")
            return []
    
    def insertar(self, idtrabajador: int, idcliente: int,
                 tipo_comprobante: str, serie: str, numero_comprobante: str,
                 igv: float, fecha: datetime = None,
                 detalle: List[Dict] = None) -> Optional[int]:
        """Inserta una nueva venta con su detalle"""
        try:
            # Iniciar transacción
            self.cursor.execute("BEGIN TRANSACTION")
            
            if not fecha:
                fecha = datetime.now()
            
            # Insertar cabecera
            self.cursor.execute("""
                INSERT INTO venta 
                (idtrabajador, idcliente, fecha, tipo_comprobante, 
                 serie, numero_comprobante, igv, estado)
                OUTPUT INSERTED.idventa
                VALUES (?, ?, ?, ?, ?, ?, ?, 'REGISTRADO')
            """, (idtrabajador, idcliente, fecha, tipo_comprobante,
                  serie, numero_comprobante, igv))
            
            idventa = self.cursor.fetchone()[0]
            
            # Insertar detalle
            if detalle:
                for item in detalle:
                    self.cursor.execute("""
                        INSERT INTO detalle_venta 
                        (idventa, idarticulo, cantidad, precio_venta)
                        VALUES (?, ?, ?, ?)
                    """, (idventa, item['idarticulo'], item['cantidad'], 
                          item['precio_venta']))
            
            self.cursor.execute("COMMIT TRANSACTION")
            logger.success(f"✅ Venta ID {idventa} insertada")
            return idventa
            
        except Exception as e:
            self.cursor.execute("ROLLBACK TRANSACTION")
            logger.error(f"❌ Error al insertar venta: {e}")
            return None
    
    def anular(self, idventa: int) -> bool:
        """Anula una venta"""
        try:
            self.cursor.execute("""
                UPDATE venta SET estado = 'ANULADO'
                WHERE idventa = ?
            """, (idventa,))
            self.cursor.commit()
            logger.success(f"✅ Venta ID {idventa} anulada")
            return True
        except Exception as e:
            logger.error(f"❌ Error al anular venta: {e}")
            return False
