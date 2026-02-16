from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger

class LoteRepositorio:
    """Repositorio para operaciones CRUD de lotes"""
    
    def __init__(self, conexion):
        self.conexion = conexion
        self.cursor = conexion.cursor()
    
    def listar_por_articulo(self, idarticulo: int) -> List[Dict]:
        """Lista los lotes de un artículo específico"""
        try:
            self.cursor.execute("""
                SELECT l.idlote, l.codigo_lote, l.fecha_produccion,
                       l.fecha_vencimiento, l.stock_actual,
                       i.fecha as fecha_ingreso
                FROM lote l
                INNER JOIN ingreso i ON l.idingreso = i.idingreso
                WHERE l.idarticulo = ?
                ORDER BY l.fecha_vencimiento ASC
            """, (idarticulo,))
            columnas = [column[0] for column in self.cursor.description]
            resultados = []
            for row in self.cursor.fetchall():
                resultados.append(dict(zip(columnas, row)))
            logger.info(f"✅ {len(resultados)} lotes listados para artículo {idarticulo}")
            return resultados
        except Exception as e:
            logger.error(f"❌ Error al listar lotes: {e}")
            return []
    
    def obtener_por_id(self, idlote: int) -> Optional[Dict]:
        """Obtiene un lote por su ID"""
        try:
            self.cursor.execute("""
                SELECT l.*, a.nombre as articulo, a.codigo
                FROM lote l
                INNER JOIN articulo a ON l.idarticulo = a.idarticulo
                WHERE l.idlote = ?
            """, (idlote,))
            row = self.cursor.fetchone()
            if row:
                columnas = [column[0] for column in self.cursor.description]
                return dict(zip(columnas, row))
            return None
        except Exception as e:
            logger.error(f"❌ Error al obtener lote {idlote}: {e}")
            return None
    
    def obtener_stock_articulo(self, idarticulo: int) -> int:
        """Obtiene el stock total de un artículo sumando todos sus lotes"""
        try:
            self.cursor.execute("""
                SELECT SUM(stock_actual) as stock_total
                FROM lote
                WHERE idarticulo = ?
            """, (idarticulo,))
            row = self.cursor.fetchone()
            return row[0] if row[0] else 0
        except Exception as e:
            logger.error(f"❌ Error al obtener stock del artículo {idarticulo}: {e}")
            return 0
    
    def insertar(self, idarticulo: int, idingreso: int,
                 codigo_lote: str = None,
                 fecha_produccion: datetime = None,
                 fecha_vencimiento: datetime = None,
                 stock_actual: int = 0) -> bool:
        """Inserta un nuevo lote"""
        try:
            self.cursor.execute("""
                INSERT INTO lote 
                (idarticulo, idingreso, codigo_lote, fecha_produccion, 
                 fecha_vencimiento, stock_actual) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (idarticulo, idingreso, codigo_lote, fecha_produccion,
                  fecha_vencimiento, stock_actual))
            self.cursor.commit()
            logger.success(f"✅ Lote insertado para artículo {idarticulo}")
            return True
        except Exception as e:
            logger.error(f"❌ Error al insertar lote: {e}")
            return False
    
    def actualizar_stock(self, idlote: int, nuevo_stock: int) -> bool:
        """Actualiza el stock de un lote específico"""
        try:
            self.cursor.execute("""
                UPDATE lote SET stock_actual = ?
                WHERE idlote = ?
            """, (nuevo_stock, idlote))
            self.cursor.commit()
            logger.success(f"✅ Stock del lote {idlote} actualizado a {nuevo_stock}")
            return True
        except Exception as e:
            logger.error(f"❌ Error al actualizar stock del lote: {e}")
            return False
    
    def eliminar(self, idlote: int) -> bool:
        """Elimina un lote"""
        try:
            self.cursor.execute("DELETE FROM lote WHERE idlote = ?", (idlote,))
            self.cursor.commit()
            logger.success(f"✅ Lote ID {idlote} eliminado")
            return True
        except Exception as e:
            logger.error(f"❌ Error al eliminar lote: {e}")
            return False
    
    def lotes_proximos_vencer(self, dias: int = 30) -> List[Dict]:
        """Lista los lotes que vencen en los próximos 'dias' días"""
        try:
            from datetime import datetime, timedelta
            fecha_limite = datetime.now() + timedelta(days=dias)
            
            self.cursor.execute("""
                SELECT l.idlote, l.codigo_lote, l.fecha_vencimiento, 
                       l.stock_actual, a.nombre as articulo, a.codigo
                FROM lote l
                INNER JOIN articulo a ON l.idarticulo = a.idarticulo
                WHERE l.fecha_vencimiento <= ? 
                  AND l.fecha_vencimiento >= GETDATE()
                  AND l.stock_actual > 0
                ORDER BY l.fecha_vencimiento ASC
            """, (fecha_limite,))
            columnas = [column[0] for column in self.cursor.description]
            resultados = []
            for row in self.cursor.fetchall():
                resultados.append(dict(zip(columnas, row)))
            logger.info(f"✅ {len(resultados)} lotes próximos a vencer")
            return resultados
        except Exception as e:
            logger.error(f"❌ Error al listar lotes próximos a vencer: {e}")
            return []
    
    def lotes_vencidos(self) -> List[Dict]:
        """Lista los lotes ya vencidos"""
        try:
            self.cursor.execute("""
                SELECT l.idlote, l.codigo_lote, l.fecha_vencimiento, 
                       l.stock_actual, a.nombre as articulo, a.codigo
                FROM lote l
                INNER JOIN articulo a ON l.idarticulo = a.idarticulo
                WHERE l.fecha_vencimiento < GETDATE()
                  AND l.stock_actual > 0
                ORDER BY l.fecha_vencimiento ASC
            """)
            columnas = [column[0] for column in self.cursor.description]
            resultados = []
            for row in self.cursor.fetchall():
                resultados.append(dict(zip(columnas, row)))
            logger.info(f"✅ {len(resultados)} lotes vencidos")
            return resultados
        except Exception as e:
            logger.error(f"❌ Error al listar lotes vencidos: {e}")
            return []
