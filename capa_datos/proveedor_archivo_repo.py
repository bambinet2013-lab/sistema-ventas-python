from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger

class ProveedorArchivoRepositorio:
    """Repositorio para gestión de archivos de proveedores"""
    
    def __init__(self, conexion):
        self.conexion = conexion
        self.cursor = conexion.cursor()
    
    def listar_por_proveedor(self, idproveedor: int) -> List[Dict]:
        """Lista todos los archivos de un proveedor (sin contenido)"""
        try:
            self.cursor.execute("""
                SELECT idarchivo, nombre_archivo, tipo_archivo, tamano, fecha_subida, descripcion
                FROM proveedor_archivos
                WHERE idproveedor = ?
                ORDER BY fecha_subida DESC
            """, (idproveedor,))
            columnas = [column[0] for column in self.cursor.description]
            resultados = []
            for row in self.cursor.fetchall():
                resultados.append(dict(zip(columnas, row)))
            return resultados
        except Exception as e:
            logger.error(f"❌ Error al listar archivos del proveedor {idproveedor}: {e}")
            return []
    
    def obtener_archivo(self, idarchivo: int) -> Optional[Dict]:
        """Obtiene un archivo por su ID (incluyendo el contenido)"""
        try:
            self.cursor.execute("""
                SELECT pv.*, p.razon_social as proveedor
                FROM proveedor_archivos pv
                INNER JOIN proveedor p ON pv.idproveedor = p.idproveedor
                WHERE pv.idarchivo = ?
            """, (idarchivo,))
            row = self.cursor.fetchone()
            if row:
                columnas = [column[0] for column in self.cursor.description]
                return dict(zip(columnas, row))
            return None
        except Exception as e:
            logger.error(f"❌ Error al obtener archivo {idarchivo}: {e}")
            return None
    
    def insertar(self, idproveedor: int, nombre_archivo: str, 
                 tipo_archivo: str, contenido: bytes, 
                 descripcion: str = None) -> Optional[int]:
        """Inserta un nuevo archivo"""
        try:
            tamano = len(contenido)
            self.cursor.execute("""
                INSERT INTO proveedor_archivos 
                (idproveedor, nombre_archivo, tipo_archivo, tamano, contenido, descripcion)
                OUTPUT INSERTED.idarchivo
                VALUES (?, ?, ?, ?, ?, ?)
            """, (idproveedor, nombre_archivo, tipo_archivo, tamano, contenido, descripcion))
            idarchivo = self.cursor.fetchone()[0]
            self.cursor.commit()
            logger.success(f"✅ Archivo '{nombre_archivo}' subido para proveedor {idproveedor}")
            return idarchivo
        except Exception as e:
            logger.error(f"❌ Error al insertar archivo: {e}")
            return None
    
    def eliminar(self, idarchivo: int) -> bool:
        """Elimina un archivo"""
        try:
            self.cursor.execute("DELETE FROM proveedor_archivos WHERE idarchivo = ?", (idarchivo,))
            self.cursor.commit()
            logger.success(f"✅ Archivo ID {idarchivo} eliminado")
            return True
        except Exception as e:
            logger.error(f"❌ Error al eliminar archivo: {e}")
            return False
