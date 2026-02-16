
from typing import List, Dict, Optional
from loguru import logger
from capa_negocio.base_service import BaseService

class CategoriaService(BaseService):
    """Servicio de categorías con validaciones y lógica de negocio"""
    
    def __init__(self, repositorio):
        self.repositorio = repositorio
        self.nombre_campo = "Categoría"
    
    def listar(self) -> List[Dict]:
        """Lista todas las categorías"""
        try:
            return self.repositorio.listar()
        except Exception as e:
            logger.error(f"❌ Error al listar categorías: {e}")
            return []
    
    def obtener_por_id(self, idcategoria: int) -> Optional[Dict]:
        """Obtiene una categoría por ID con validación"""
        if not self.validar_entero_positivo(idcategoria, "ID de categoría"):
            return None
        
        try:
            return self.repositorio.obtener_por_id(idcategoria)
        except Exception as e:
            logger.error(f"❌ Error al obtener categoría {idcategoria}: {e}")
            return None
    
    def crear(self, nombre: str, descripcion: str = None) -> bool:
        """Crea una nueva categoría con validaciones"""
        # Validaciones
        if not self.validar_requerido(nombre, "nombre"):
            return False
        
        if not self.validar_longitud(nombre, "nombre", max_len=50):
            return False
        
        if descripcion and not self.validar_longitud(descripcion, "descripción", max_len=256):
            return False
        
        try:
            return self.repositorio.insertar(nombre.strip(), descripcion)
        except Exception as e:
            logger.error(f"❌ Error al crear categoría: {e}")
            return False
    
    def actualizar(self, idcategoria: int, nombre: str, descripcion: str = None) -> bool:
        """Actualiza una categoría con validaciones"""
        if not self.validar_entero_positivo(idcategoria, "ID de categoría"):
            return False
        
        if not self.validar_requerido(nombre, "nombre"):
            return False
        
        if not self.validar_longitud(nombre, "nombre", max_len=50):
            return False
        
        if descripcion and not self.validar_longitud(descripcion, "descripción", max_len=256):
            return False
        
        try:
            return self.repositorio.actualizar(idcategoria, nombre.strip(), descripcion)
        except Exception as e:
            logger.error(f"❌ Error al actualizar categoría: {e}")
            return False
    
    def eliminar(self, idcategoria: int) -> bool:
        """Elimina una categoría con validación"""
        if not self.validar_entero_positivo(idcategoria, "ID de categoría"):
            return False
        
        try:
            return self.repositorio.eliminar(idcategoria)
        except Exception as e:
            logger.error(f"❌ Error al eliminar categoría: {e}")
            return False



