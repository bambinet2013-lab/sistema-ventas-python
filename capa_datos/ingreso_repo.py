from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger

class IngresoRepositorio:
    """Repositorio para operaciones CRUD de ingresos"""
    
    def __init__(self, conexion):
        self.conexion = conexion
        self.cursor = conexion.cursor()
    
    def listar(self) -> List[Dict]:
        """Lista todos los ingresos"""
        try:
            query = """
                SELECT i.idingreso, i.fecha, i.tipo_comprobante, i.serie, i.numero_comprobante,
                       i.igv, i.estado,
                       p.razon_social as proveedor,
                       t.nombre + ' ' + t.apellidos as trabajador
                FROM ingreso i
                INNER JOIN proveedor p ON i.idproveedor = p.idproveedor
                INNER JOIN trabajador t ON i.idtrabajador = t.idtrabajador
                ORDER BY i.fecha DESC
            """
            self.cursor.execute(query)
            columnas = [column[0] for column in self.cursor.description]
            resultados = []
            for row in self.cursor.fetchall():
                resultados.append(dict(zip(columnas, row)))
            logger.info(f"✅ {len(resultados)} ingresos listados")
            return resultados
        except Exception as e:
            logger.error(f"❌ Error al listar ingresos: {e}")
            return []
    
    def obtener_por_id(self, idingreso: int) -> Optional[Dict]:
        """Obtiene un ingreso por su ID con su detalle"""
        try:
            # Obtener cabecera
            self.cursor.execute("""
                SELECT i.*, p.razon_social as proveedor,
                       t.nombre + ' ' + t.apellidos as trabajador
                FROM ingreso i
                INNER JOIN proveedor p ON i.idproveedor = p.idproveedor
                INNER JOIN trabajador t ON i.idtrabajador = t.idtrabajador
                WHERE i.idingreso = ?
            """, (idingreso,))
            row = self.cursor.fetchone()
            
            if not row:
                return None
            
            columnas = [column[0] for column in self.cursor.description]
            ingreso = dict(zip(columnas, row))
            
            # Obtener detalle
            ingreso['detalle'] = self.obtener_detalle(idingreso)
            
            return ingreso
        except Exception as e:
            logger.error(f"❌ Error al obtener ingreso {idingreso}: {e}")
            return None
    
    def obtener_detalle(self, idingreso: int) -> List[Dict]:
        """Obtiene el detalle de un ingreso"""
        try:
            self.cursor.execute("""
                SELECT di.iddetalle_ingreso, di.cantidad, di.precio_compra,
                       a.idarticulo, a.codigo, a.nombre as articulo
                FROM detalle_ingreso di
                INNER JOIN articulo a ON di.idarticulo = a.idarticulo
                WHERE di.idingreso = ?
            """, (idingreso,))
            columnas = [column[0] for column in self.cursor.description]
            resultados = []
            for row in self.cursor.fetchall():
                resultados.append(dict(zip(columnas, row)))
            return resultados
        except Exception as e:
            logger.error(f"❌ Error al obtener detalle del ingreso: {e}")
            return []
    
    def insertar(self, idtrabajador: int, idproveedor: int,
                 tipo_comprobante: str, serie: str, numero_comprobante: str,
                 igv: float, fecha: datetime = None,
                 detalle: List[Dict] = None) -> Optional[int]:
        """Inserta un nuevo ingreso con su detalle"""
        try:
            # Iniciar transacción
            self.cursor.execute("BEGIN TRANSACTION")
            
            if not fecha:
                fecha = datetime.now()
            
            # Insertar cabecera
            self.cursor.execute("""
                INSERT INTO ingreso 
                (idtrabajador, idproveedor, fecha, tipo_comprobante, 
                 serie, numero_comprobante, igv, estado)
                OUTPUT INSERTED.idingreso
                VALUES (?, ?, ?, ?, ?, ?, ?, 'REGISTRADO')
            """, (idtrabajador, idproveedor, fecha, tipo_comprobante,
                  serie, numero_comprobante, igv))
            
            idingreso = self.cursor.fetchone()[0]
            
            # Insertar detalle
            if detalle:
                for item in detalle:
                    self.cursor.execute("""
                        INSERT INTO detalle_ingreso 
                        (idingreso, idarticulo, cantidad, precio_compra)
                        VALUES (?, ?, ?, ?)
                    """, (idingreso, item['idarticulo'], item['cantidad'], 
                          item['precio_compra']))
            
            self.cursor.execute("COMMIT TRANSACTION")
            logger.success(f"✅ Ingreso ID {idingreso} insertado")
            return idingreso
            
        except Exception as e:
            self.cursor.execute("ROLLBACK TRANSACTION")
            logger.error(f"❌ Error al insertar ingreso: {e}")
            return None
    
    def anular(self, idingreso: int) -> bool:
        """Anula un ingreso"""
        try:
            self.cursor.execute("""
                UPDATE ingreso SET estado = 'ANULADO'
                WHERE idingreso = ?
            """, (idingreso,))
            self.cursor.commit()
            logger.success(f"✅ Ingreso ID {idingreso} anulado")
            return True
        except Exception as e:
            logger.error(f"❌ Error al anular ingreso: {e}")
            return False
