from typing import List, Dict, Optional
from loguru import logger

class ArticuloRepositorio:
    """Repositorio para operaciones CRUD de artículos"""
    
    def __init__(self, conexion):
        self.conexion = conexion
        self.cursor = conexion.cursor()
    
    def listar(self) -> List[Dict]:
        """Lista todos los artículos"""
        try:
            query = """
                SELECT a.idarticulo, a.codigo, a.nombre, a.descripcion, 
                       a.idcategoria, c.nombre as categoria,
                       a.idpresentacion, p.nombre as presentacion,
                       a.imagen
                FROM articulo a
                INNER JOIN categoria c ON a.idcategoria = c.idcategoria
                INNER JOIN presentacion p ON a.idpresentacion = p.idpresentacion
                ORDER BY a.nombre
            """
            self.cursor.execute(query)
            columnas = [column[0] for column in self.cursor.description]
            resultados = []
            for row in self.cursor.fetchall():
                resultados.append(dict(zip(columnas, row)))
            logger.info(f"✅ {len(resultados)} artículos listados")
            return resultados
        except Exception as e:
            logger.error(f"❌ Error al listar artículos: {e}")
            return []
    
    def obtener_por_id(self, idarticulo: int) -> Optional[Dict]:
        """Obtiene un artículo por su ID"""
        try:
            query = """
                SELECT a.idarticulo, a.codigo, a.nombre, a.descripcion,
                       a.idcategoria, c.nombre as categoria,
                       a.idpresentacion, p.nombre as presentacion,
                       a.imagen
                FROM articulo a
                INNER JOIN categoria c ON a.idcategoria = c.idcategoria
                INNER JOIN presentacion p ON a.idpresentacion = p.idpresentacion
                WHERE a.idarticulo = ?
            """
            self.cursor.execute(query, (idarticulo,))
            row = self.cursor.fetchone()
            if row:
                columnas = [column[0] for column in self.cursor.description]
                return dict(zip(columnas, row))
            return None
        except Exception as e:
            logger.error(f"❌ Error al obtener artículo {idarticulo}: {e}")
            return None
    
    def buscar_por_codigo(self, codigo: str) -> Optional[Dict]:
        """Busca un artículo por su código"""
        try:
            self.cursor.execute(
                "SELECT idarticulo, codigo, nombre FROM articulo WHERE codigo = ?",
                (codigo,)
            )
            row = self.cursor.fetchone()
            if row:
                return {
                    'idarticulo': row[0],
                    'codigo': row[1],
                    'nombre': row[2]
                }
            return None
        except Exception as e:
            logger.error(f"❌ Error al buscar código {codigo}: {e}")
            return None
    
    def insertar(self, codigo: str, nombre: str, idcategoria: int, 
                 idpresentacion: int, descripcion: str = None, imagen=None) -> bool:
        """Inserta un nuevo artículo"""
        try:
            self.cursor.execute(
                """INSERT INTO articulo 
                   (codigo, nombre, idcategoria, idpresentacion, descripcion, imagen) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (codigo, nombre, idcategoria, idpresentacion, descripcion, imagen)
            )
            self.cursor.commit()
            logger.success(f"✅ Artículo '{nombre}' insertado")
            return True
        except Exception as e:
            logger.error(f"❌ Error al insertar artículo: {e}")
            return False
    
    def actualizar(self, idarticulo: int, codigo: str, nombre: str, 
                   idcategoria: int, idpresentacion: int, 
                   descripcion: str = None, imagen=None) -> bool:
        """Actualiza un artículo existente"""
        try:
            self.cursor.execute(
                """UPDATE articulo 
                   SET codigo = ?, nombre = ?, idcategoria = ?, 
                       idpresentacion = ?, descripcion = ?, imagen = ?
                   WHERE idarticulo = ?""",
                (codigo, nombre, idcategoria, idpresentacion, descripcion, imagen, idarticulo)
            )
            self.cursor.commit()
            logger.success(f"✅ Artículo ID {idarticulo} actualizado")
            return True
        except Exception as e:
            logger.error(f"❌ Error al actualizar artículo: {e}")
            return False
    
    def eliminar(self, idarticulo: int) -> bool:
        """Elimina un artículo"""
        try:
            self.cursor.execute("DELETE FROM articulo WHERE idarticulo = ?", (idarticulo,))
            self.cursor.commit()
            logger.success(f"✅ Artículo ID {idarticulo} eliminado")
            return True
        except Exception as e:
            logger.error(f"❌ Error al eliminar artículo: {e}")
            return False
