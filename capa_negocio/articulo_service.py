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
    
    def crear(self, codigo, nombre, idcategoria, idpresentacion, descripcion=None):
        """
        Crea un nuevo artículo
        """
        try:
            # Validaciones
            if not codigo or not codigo.strip():
                logger.error("El código del artículo es obligatorio")
                return False
            
            if not nombre or not nombre.strip():
                logger.error("El nombre del artículo es obligatorio")
                return False
            
            if not self.validar_entero_positivo(idcategoria, "ID de categoría"):
                return False
            
            if not self.validar_entero_positivo(idpresentacion, "ID de presentación"):
                return False
            
            # Verificar si ya existe un artículo con el mismo código
            existente = self.repositorio.buscar_por_codigo(codigo)
            if existente:
                logger.error(f"Ya existe un artículo con el código {codigo}")
                return False
            
            # Crear artículo - LLAMADA CORRECTA
            resultado = self.repositorio.crear(  # <--- DEBE SER 'crear', no 'insertar'
                codigo=codigo.strip(),
                nombre=nombre.strip(),
                idcategoria=idcategoria,
                idpresentacion=idpresentacion,
                descripcion=descripcion.strip() if descripcion else None
            )
            
            if resultado:
                logger.info(f"✅ Artículo creado: {nombre}")
                return True
            else:
                logger.error("No se pudo crear el artículo")
                return False
                
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
