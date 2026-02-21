"""
Servicio para la gestión de artículos
"""
from loguru import logger
from capa_negocio.base_service import BaseService

class ArticuloService(BaseService):
    """Servicio que implementa la lógica de negocio para artículos"""
    
    def __init__(self, repositorio, categoria_service):
        """
        Inicializa el servicio de artículos
        
        Args:
            repositorio: Instancia de ArticuloRepositorio
            categoria_service: Servicio de categorías
        """
        super().__init__()
        self.repositorio = repositorio
        self.categoria_service = categoria_service
        logger.info("✅ ArticuloService inicializado")
    
    def listar(self):
        """
        Lista todos los artículos
        
        Returns:
            list: Lista de artículos o lista vacía si hay error
        """
        try:
            return self.repositorio.listar()
        except Exception as e:
            logger.error(f"Error al listar artículos: {e}")
            return []
    
    def obtener_por_id(self, idarticulo):
        """
        Obtiene un artículo por su ID
        
        Args:
            idarticulo (int): ID del artículo
            
        Returns:
            dict: Datos del artículo o None si no existe
        """
        try:
            if not self.validar_entero_positivo(idarticulo, "ID del artículo"):
                return None
            return self.repositorio.obtener_por_id(idarticulo)
        except Exception as e:
            logger.error(f"Error al obtener artículo {idarticulo}: {e}")
            return None
    
    def buscar_por_codigo(self, codigo):
        """
        Busca un artículo por su código
        
        Args:
            codigo (str): Código del artículo
            
        Returns:
            dict: Datos del artículo o None si no existe
        """
        try:
            return self.repositorio.buscar_por_codigo(codigo)
        except Exception as e:
            logger.error(f"Error al buscar artículo por código {codigo}: {e}")
            return None
    
    def crear(self, codigo, nombre, idcategoria, idpresentacion, descripcion=None, 
              precio_venta=0, precio_referencia=None):
        """
        Crea un nuevo artículo con precio de venta
        
        Args:
            codigo (str): Código del artículo
            nombre (str): Nombre del artículo
            idcategoria (int): ID de la categoría
            idpresentacion (int): ID de la presentación
            descripcion (str, optional): Descripción
            precio_venta (float): Precio de venta en USD
            precio_referencia (float, optional): Precio de referencia (costo)
            
        Returns:
            bool: True si se creó correctamente, False en caso contrario
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
            
            # Validar precio de venta (puede ser 0)
            if not isinstance(precio_venta, (int, float)) or precio_venta < 0:
                logger.error("El precio de venta debe ser un número positivo")
                return False
            
            # Validar precio de referencia (puede ser None)
            if precio_referencia is not None:
                if not isinstance(precio_referencia, (int, float)) or precio_referencia < 0:
                    logger.error("El precio de referencia debe ser un número positivo o None")
                    return False
            
            # Crear artículo
            resultado = self.repositorio.crear(
                codigo=codigo.strip(),
                nombre=nombre.strip(),
                idcategoria=idcategoria,
                idpresentacion=idpresentacion,
                descripcion=descripcion.strip() if descripcion else None,
                precio_venta=precio_venta,
                precio_referencia=precio_referencia
            )
            
            if resultado:
                logger.info(f"✅ Artículo creado: {nombre} - Precio: ${precio_venta}")
                return True
            else:
                logger.error("No se pudo crear el artículo")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error al crear artículo: {e}")
            return False
    
    def actualizar(self, idarticulo, codigo, nombre, idcategoria, idpresentacion, 
                   descripcion=None, precio_venta=None, precio_referencia=None):
        """
        Actualiza un artículo existente incluyendo precios
        
        Args:
            idarticulo (int): ID del artículo
            codigo (str): Código del artículo
            nombre (str): Nombre del artículo
            idcategoria (int): ID de la categoría
            idpresentacion (int): ID de la presentación
            descripcion (str, optional): Descripción
            precio_venta (float, optional): Precio de venta en USD
            precio_referencia (float, optional): Precio de referencia (costo)
            
        Returns:
            bool: True si se actualizó correctamente, False en caso contrario
        """
        try:
            # Validar que el artículo existe
            articulo = self.obtener_por_id(idarticulo)
            if not articulo:
                logger.error(f"Artículo {idarticulo} no encontrado")
                return False
            
            # Validaciones básicas
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
            
            # Validar precio_venta (FORZAR A FLOAT)
            if precio_venta is not None:
                try:
                    precio_venta = float(precio_venta)
                except (ValueError, TypeError):
                    logger.error("El precio de venta debe ser un número válido")
                    return False
                    
                if precio_venta < 0:
                    logger.error("El precio de venta no puede ser negativo")
                    return False
            else:
                # Si no viene, mantener el actual
                precio_venta = float(articulo.get('precio_venta', 0))
            
            # Validar precio_referencia (puede ser None)
            if precio_referencia is not None:
                try:
                    precio_referencia = float(precio_referencia)
                except (ValueError, TypeError):
                    logger.error("El precio de referencia debe ser un número válido")
                    return False
                    
                if precio_referencia < 0:
                    logger.error("El precio de referencia no puede ser negativo")
                    return False
            # Si es None, es válido (no se actualizará en BD)
            
            # Verificar si el código ya existe en otro artículo
            existente = self.repositorio.buscar_por_codigo(codigo)
            if existente and existente['idarticulo'] != idarticulo:
                logger.error(f"Ya existe otro artículo con el código {codigo}")
                return False
            
            # Actualizar artículo
            resultado = self.repositorio.actualizar(
                idarticulo=idarticulo,
                codigo=codigo.strip(),
                nombre=nombre.strip(),
                idcategoria=idcategoria,
                idpresentacion=idpresentacion,
                descripcion=descripcion.strip() if descripcion else None,
                precio_venta=precio_venta,
                precio_referencia=precio_referencia
            )
            
            if resultado:
                logger.info(f"✅ Artículo {idarticulo} actualizado - Precio: ${precio_venta}")
                return True
            else:
                logger.error(f"No se pudo actualizar el artículo {idarticulo}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error al actualizar artículo {idarticulo}: {e}")
            return False
    
    def eliminar(self, idarticulo):
        """
        Elimina un artículo (verifica si tiene movimientos asociados)
        
        Args:
            idarticulo (int): ID del artículo a eliminar
            
        Returns:
            bool: True si se eliminó correctamente, False en caso contrario
        """
        try:
            if not self.validar_entero_positivo(idarticulo, "ID del artículo"):
                return False
            
            # Verificar que el artículo existe
            articulo = self.obtener_por_id(idarticulo)
            if not articulo:
                logger.error(f"Artículo {idarticulo} no encontrado")
                return False
            
            resultado = self.repositorio.eliminar(idarticulo)
            
            if resultado:
                logger.info(f"✅ Artículo {idarticulo} eliminado correctamente")
                return True
            else:
                logger.error(f"No se pudo eliminar el artículo {idarticulo}")
                return False
                
        except Exception as e:
            logger.error(f"Error al eliminar artículo {idarticulo}: {e}")
            return False
    
    def buscar_por_codigo_barras(self, codigo):
        """
        Busca artículo por código de barras
        
        Args:
            codigo (str): Código de barras
            
        Returns:
            dict: Datos del artículo o None si no existe
        """
        try:
            return self.repositorio.buscar_por_codigo_barras(codigo)
        except Exception as e:
            logger.error(f"Error buscando por código de barras {codigo}: {e}")
            return None
    
    def buscar_por_plu(self, plu):
        """
        Busca artículo por código interno PLU
        
        Args:
            plu (str): Código PLU
            
        Returns:
            dict: Datos del artículo o None si no existe
        """
        try:
            return self.repositorio.buscar_por_plu(plu)
        except Exception as e:
            logger.error(f"Error buscando por PLU {plu}: {e}")
            return None
    
    def buscar_por_nombre(self, termino):
        """
        Busca artículos por nombre (búsqueda parcial)
        
        Args:
            termino (str): Término de búsqueda
            
        Returns:
            list: Lista de artículos que coinciden
        """
        try:
            return self.repositorio.buscar_por_nombre(termino)
        except Exception as e:
            logger.error(f"Error buscando por nombre {termino}: {e}")
            return []
