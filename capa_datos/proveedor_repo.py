from typing import List, Dict, Optional
from loguru import logger

class ProveedorRepositorio:
    """Repositorio para operaciones CRUD de proveedores"""
    
    def __init__(self, conexion):
        self.conexion = conexion
        self.cursor = conexion.cursor()
    
    def listar(self) -> List[Dict]:
        """Lista todos los proveedores"""
        try:
            self.cursor.execute("""
                SELECT idproveedor, razon_social, sector_comercial,
                       tipo_documento, num_documento, direccion,
                       telefono, email, url
                FROM proveedor ORDER BY razon_social
            """)
            columnas = [column[0] for column in self.cursor.description]
            resultados = []
            for row in self.cursor.fetchall():
                resultados.append(dict(zip(columnas, row)))
            logger.info(f"✅ {len(resultados)} proveedores listados")
            return resultados
        except Exception as e:
            logger.error(f"❌ Error al listar proveedores: {e}")
            return []
    
    def obtener_por_id(self, idproveedor: int) -> Optional[Dict]:
        """Obtiene un proveedor por su ID"""
        try:
            self.cursor.execute(
                "SELECT * FROM proveedor WHERE idproveedor = ?",
                (idproveedor,)
            )
            row = self.cursor.fetchone()
            if row:
                columnas = [column[0] for column in self.cursor.description]
                return dict(zip(columnas, row))
            return None
        except Exception as e:
            logger.error(f"❌ Error al obtener proveedor {idproveedor}: {e}")
            return None
    
    def insertar(self, razon_social: str, sector_comercial: str,
                 tipo_documento: str, num_documento: str,
                 direccion: str = None, telefono: str = None,
                 email: str = None, url: str = None) -> bool:
        """Inserta un nuevo proveedor"""
        try:
            self.cursor.execute(
                """INSERT INTO proveedor 
                   (razon_social, sector_comercial, tipo_documento, num_documento,
                    direccion, telefono, email, url) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (razon_social, sector_comercial, tipo_documento, num_documento,
                 direccion, telefono, email, url)
            )
            self.cursor.commit()
            logger.success(f"✅ Proveedor '{razon_social}' insertado")
            return True
        except Exception as e:
            logger.error(f"❌ Error al insertar proveedor: {e}")
            return False
    
    def actualizar(self, idproveedor: int, razon_social: str, sector_comercial: str,
                   tipo_documento: str, num_documento: str,
                   direccion: str = None, telefono: str = None,
                   email: str = None, url: str = None) -> bool:
        """Actualiza un proveedor existente"""
        try:
            self.cursor.execute(
                """UPDATE proveedor 
                   SET razon_social = ?, sector_comercial = ?,
                       tipo_documento = ?, num_documento = ?,
                       direccion = ?, telefono = ?, email = ?, url = ?
                   WHERE idproveedor = ?""",
                (razon_social, sector_comercial, tipo_documento, num_documento,
                 direccion, telefono, email, url, idproveedor)
            )
            self.cursor.commit()
            logger.success(f"✅ Proveedor ID {idproveedor} actualizado")
            return True
        except Exception as e:
            logger.error(f"❌ Error al actualizar proveedor: {e}")
            return False
    
    def eliminar(self, idproveedor: int) -> bool:
        """Elimina un proveedor"""
        try:
            self.cursor.execute("DELETE FROM proveedor WHERE idproveedor = ?", (idproveedor,))
            self.cursor.commit()
            logger.success(f"✅ Proveedor ID {idproveedor} eliminado")
            return True
        except Exception as e:
            logger.error(f"❌ Error al eliminar proveedor: {e}")
            return False
