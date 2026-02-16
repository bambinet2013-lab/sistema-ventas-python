from typing import List, Dict, Optional
from loguru import logger
from capa_negocio.base_service import BaseService

class ArticuloService(BaseService):
    """Servicio de artículos con validaciones"""
    
    def __init__(self, repositorio, categoria_service=None, presentacion_service=None):
        self.repositorio = repositorio
        self.categoria_service = categoria_service
        self.presentacion_service = presentacion_service
    
    def listar(self) -> List[Dict]:
        """Lista todos los artículos"""
        try:
            return self.repositorio.listar()
        except Exception as e:
            logger.error(f"❌ Error al listar artículos: {e}")
            return []
    
    def obtener_por_id(self, idarticulo: int) -> Optional[Dict]:
        """Obtiene un artículo por ID"""
        if not self.validar_entero_positivo(idarticulo, "ID de artículo"):
            return None
        return self.repositorio.obtener_por_id(idarticulo)
    
    def buscar_por_codigo(self, codigo: str) -> Optional[Dict]:
        """Busca un artículo por código"""
        if not codigo:
            return None
        return self.repositorio.buscar_por_codigo(codigo)
    
    def crear(self, codigo: str, nombre: str, idcategoria: int,
              idpresentacion: int, descripcion: str = None, imagen=None) -> bool:
        """Crea un nuevo artículo con validaciones"""
        
        # Validaciones
        if not self.validar_requerido(codigo, "código"):
            return False
        if not self.validar_requerido(nombre, "nombre"):
            return False
        if not self.validar_entero_positivo(idcategoria, "categoría"):
            return False
        if not self.validar_entero_positivo(idpresentacion, "presentación"):
            return False
        
        if not self.validar_longitud(codigo, "código", max_len=50):
            return False
        if not self.validar_longitud(nombre, "nombre", max_len=100):
            return False
        if descripcion and not self.validar_longitud(descripcion, "descripción", max_len=256):
            return False
        
        # Validar que existan categoría y presentación
        if self.categoria_service:
            categoria = self.categoria_service.obtener_por_id(idcategoria)
            if not categoria:
                logger.warning(f"⚠️ La categoría {idcategoria} no existe")
                return False
        
        if self.presentacion_service:
            presentacion = self.presentacion_service.obtener_por_id(idpresentacion)
            if not presentacion:
                logger.warning(f"⚠️ La presentación {idpresentacion} no existe")
                return False
        
        try:
            return self.repositorio.insertar(
                codigo.strip(), nombre.strip(),
                idcategoria, idpresentacion,
                descripcion, imagen
            )
        except Exception as e:
            logger.error(f"❌ Error al crear artículo: {e}")
            return False
    
    def actualizar(self, idarticulo: int, codigo: str, nombre: str,
                   idcategoria: int, idpresentacion: int,
                   descripcion: str = None, imagen=None) -> bool:
        """Actualiza un artículo con validaciones"""
        
        if not self.validar_entero_positivo(idarticulo, "ID de artículo"):
            return False
        
        # Validaciones
        if not self.validar_requerido(codigo, "código"):
            return False
        if not self.validar_requerido(nombre, "nombre"):
            return False
        if not self.validar_entero_positivo(idcategoria, "categoría"):
            return False
        if not self.validar_entero_positivo(idpresentacion, "presentación"):
            return False
        
        try:
            return self.repositorio.actualizar(
                idarticulo, codigo.strip(), nombre.strip(),
                idcategoria, idpresentacion, descripcion, imagen
            )
        except Exception as e:
            logger.error(f"❌ Error al actualizar artículo: {e}")
            return False
    
    def eliminar(self, idarticulo: int) -> bool:
        """Elimina un artículo"""
        if not self.validar_entero_positivo(idarticulo, "ID de artículo"):
            return False
        return self.repositorio.eliminar(idarticulo)
