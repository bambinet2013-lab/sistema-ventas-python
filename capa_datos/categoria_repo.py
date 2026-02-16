from typing import List, Dict, Optional
from loguru import logger

class CategoriaRepositorio:
    """Repositorio para operaciones CRUD de categoría"""
    
    def __init__(self, conexion):
        self.conexion = conexion
        self.cursor = conexion.cursor()
    
    def listar(self) -> List[Dict]:
        """Lista todas las categorías"""
        try:
            self.cursor.execute("SELECT idcategoria, nombre, descripcion FROM categoria ORDER BY nombre")
            columnas = [column[0] for column in self.cursor.description]
            resultados = []
            for row in self.cursor.fetchall():
                resultados.append(dict(zip(columnas, row)))
            logger.info(f"✅ {len(resultados)} categorías listadas")
            return resultados
        except Exception as e:
            logger.error(f"❌ Error al listar categorías: {e}")
            return []
    
    def obtener_por_id(self, idcategoria: int) -> Optional[Dict]:
        """Obtiene una categoría por su ID"""
        try:
            self.cursor.execute(
                "SELECT idcategoria, nombre, descripcion FROM categoria WHERE idcategoria = ?",
                (idcategoria,)
            )
            row = self.cursor.fetchone()
            if row:
                return {
                    'idcategoria': row[0],
                    'nombre': row[1],
                    'descripcion': row[2]
                }
            return None
        except Exception as e:
            logger.error(f"❌ Error al obtener categoría {idcategoria}: {e}")
            return None
    
    def insertar(self, nombre: str, descripcion: str = None) -> bool:
        """Inserta una nueva categoría"""
        try:
            self.cursor.execute(
                "INSERT INTO categoria (nombre, descripcion) VALUES (?, ?)",
                (nombre, descripcion)
            )
            self.cursor.commit()
            logger.success(f"✅ Categoría '{nombre}' insertada")
            return True
        except Exception as e:
            logger.error(f"❌ Error al insertar categoría: {e}")
            return False
    
    def actualizar(self, idcategoria: int, nombre: str, descripcion: str = None) -> bool:
        """Actualiza una categoría existente"""
        try:
            self.cursor.execute(
                "UPDATE categoria SET nombre = ?, descripcion = ? WHERE idcategoria = ?",
                (nombre, descripcion, idcategoria)
            )
            self.cursor.commit()
            logger.success(f"✅ Categoría ID {idcategoria} actualizada")
            return True
        except Exception as e:
            logger.error(f"❌ Error al actualizar categoría: {e}")
            return False
    
    def eliminar(self, idcategoria: int) -> bool:
        """Elimina una categoría"""
        try:
            self.cursor.execute("DELETE FROM categoria WHERE idcategoria = ?", (idcategoria,))
            self.cursor.commit()
            logger.success(f"✅ Categoría ID {idcategoria} eliminada")
            return True
        except Exception as e:
            logger.error(f"❌ Error al eliminar categoría: {e}")
            return False
