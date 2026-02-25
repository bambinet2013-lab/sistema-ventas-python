"""
Servicio para gestión de artículos
"""
from loguru import logger
from typing import List, Dict, Optional
from capa_negocio.base_service import BaseService
from capa_datos.articulo_repo import ArticuloRepositorio
from capa_datos.categoria_repo import CategoriaRepositorio

class ArticuloService(BaseService):
    def __init__(self, repositorio: ArticuloRepositorio, categoria_service=None):
        """
        Inicializa el servicio de artículos
        
        Args:
            repositorio: Repositorio de artículos
            categoria_service: Servicio de categorías (opcional)
        """
        super().__init__()
        self.repositorio = repositorio
        self.categoria_service = categoria_service
        
    def listar_articulos(self) -> List[Dict]:
        """
        Lista todos los artículos
        
        Returns:
            List[Dict]: Lista de artículos
        """
        try:
            articulos = self.repositorio.listar()
            logger.info(f"✅ {len(articulos)} artículos listados")
            return articulos
        except Exception as e:
            logger.error(f"❌ Error listando artículos: {e}")
            return []
    
    def buscar_por_id(self, idarticulo: int) -> Optional[Dict]:
        """
        Busca un artículo por su ID
        
        Args:
            idarticulo: ID del artículo
            
        Returns:
            Optional[Dict]: Artículo encontrado o None
        """
        try:
            if not self.validar_entero_positivo(idarticulo, "ID del artículo"):
                return None
                
            articulo = self.repositorio.obtener_por_id(idarticulo)
            if articulo:
                logger.info(f"✅ Artículo ID {idarticulo} encontrado: {articulo['nombre']}")
            else:
                logger.warning(f"⚠️ Artículo ID {idarticulo} no encontrado")
            return articulo
        except Exception as e:
            logger.error(f"❌ Error buscando artículo {idarticulo}: {e}")
            return None
    
    def buscar_por_codigo(self, codigo: str) -> Optional[Dict]:
        """
        Busca un artículo por su código de barras o PLU
        
        Args:
            codigo: Código de barras o PLU
            
        Returns:
            Optional[Dict]: Artículo encontrado o None
        """
        try:
            if not codigo:
                logger.warning("⚠️ Código vacío")
                return None
                
            articulo = self.repositorio.buscar_por_codigo(codigo)
            if articulo:
                logger.info(f"✅ Artículo encontrado: {articulo['nombre']} (código: {codigo})")
            else:
                logger.debug(f"Artículo con código {codigo} no encontrado")
            return articulo
        except Exception as e:
            logger.error(f"❌ Error buscando por código {codigo}: {e}")
            return None
    
    def crear_articulo(self, codigo_barras: str, nombre: str, idcategoria: int,
                       precio_venta: float, stock_minimo: int = 5,
                       precio_compra: float = 0, igtf: bool = False) -> Optional[int]:
        """
        Crea un nuevo artículo
        
        Args:
            codigo_barras: Código de barras o PLU
            nombre: Nombre del artículo
            idcategoria: ID de la categoría
            precio_venta: Precio de venta en USD
            stock_minimo: Stock mínimo para alertas
            precio_compra: Precio de compra (opcional)
            igtf: Aplica IGTF (True/False)
            
        Returns:
            Optional[int]: ID del artículo creado o None
        """
        try:
            # Validaciones
            if not codigo_barras:
                logger.warning("⚠️ Código de barras obligatorio")
                return None
                
            if not nombre:
                logger.warning("⚠️ Nombre obligatorio")
                return None
                
            if not self.validar_entero_positivo(idcategoria, "ID de categoría"):
                return None
                
            if precio_venta <= 0:
                logger.warning(f"⚠️ Precio de venta inválido: {precio_venta}")
                return None
            
            # Verificar si ya existe el código
            existente = self.repositorio.buscar_por_codigo(codigo_barras)
            if existente:
                logger.warning(f"⚠️ Ya existe un artículo con código {codigo_barras}")
                return None
            
            # Crear artículo
            idarticulo = self.repositorio.crear(
                codigo_barras=codigo_barras,
                nombre=nombre,
                idcategoria=idcategoria,
                precio_venta=precio_venta,
                stock_minimo=stock_minimo,
                precio_compra=precio_compra,
                igtf=igtf
            )
            
            if idarticulo:
                logger.info(f"✅ Artículo creado: {nombre} (ID: {idarticulo})")
                
                # Registrar en auditoría
                self.registrar_auditoria(
                    accion='CREAR',
                    tabla='articulo',
                    registro_id=idarticulo,
                    datos_nuevos=f"Código: {codigo_barras}, Nombre: {nombre}, Precio: ${precio_venta:.2f}"
                )
                
            return idarticulo
            
        except Exception as e:
            logger.error(f"❌ Error creando artículo: {e}")
            return None
    
    def actualizar_articulo(self, idarticulo: int, codigo_barras: str, nombre: str,
                            idcategoria: int, precio_venta: float, stock_minimo: int = 5,
                            precio_compra: float = 0, igtf: bool = False) -> bool:
        """
        Actualiza un artículo existente
        
        Args:
            idarticulo: ID del artículo a actualizar
            codigo_barras: Nuevo código de barras
            nombre: Nuevo nombre
            idcategoria: Nueva categoría
            precio_venta: Nuevo precio de venta
            stock_minimo: Nuevo stock mínimo
            precio_compra: Nuevo precio de compra
            igtf: Nuevo estado de IGTF
            
        Returns:
            bool: True si se actualizó correctamente
        """
        try:
            # Validaciones
            if not self.validar_entero_positivo(idarticulo, "ID del artículo"):
                return False
                
            if not codigo_barras:
                logger.warning("⚠️ Código de barras obligatorio")
                return False
                
            if not nombre:
                logger.warning("⚠️ Nombre obligatorio")
                return False
                
            if not self.validar_entero_positivo(idcategoria, "ID de categoría"):
                return False
                
            if precio_venta <= 0:
                logger.warning(f"⚠️ Precio de venta inválido: {precio_venta}")
                return False
            
            # Obtener datos anteriores para auditoría
            datos_anteriores = self.repositorio.obtener_por_id(idarticulo)
            
            # Actualizar artículo
            resultado = self.repositorio.actualizar(
                idarticulo=idarticulo,
                codigo_barras=codigo_barras,
                nombre=nombre,
                idcategoria=idcategoria,
                precio_venta=precio_venta,
                stock_minimo=stock_minimo,
                precio_compra=precio_compra,
                igtf=igtf
            )
            
            if resultado:
                logger.info(f"✅ Artículo {idarticulo} actualizado")
                
                # Registrar en auditoría
                self.registrar_auditoria(
                    accion='ACTUALIZAR',
                    tabla='articulo',
                    registro_id=idarticulo,
                    datos_anteriores=str(datos_anteriores) if datos_anteriores else None,
                    datos_nuevos=f"Código: {codigo_barras}, Nombre: {nombre}, Precio: ${precio_venta:.2f}"
                )
                
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Error actualizando artículo {idarticulo}: {e}")
            return False
    
    def eliminar_articulo(self, idarticulo: int) -> bool:
        """
        Elimina un artículo (marca como inactivo)
        
        Args:
            idarticulo: ID del artículo a eliminar
            
        Returns:
            bool: True si se eliminó correctamente
        """
        try:
            if not self.validar_entero_positivo(idarticulo, "ID del artículo"):
                return False
            
            # Obtener datos para auditoría
            datos_anteriores = self.repositorio.obtener_por_id(idarticulo)
            
            resultado = self.repositorio.eliminar(idarticulo)
            
            if resultado:
                logger.info(f"✅ Artículo {idarticulo} eliminado")
                
                # Registrar en auditoría
                self.registrar_auditoria(
                    accion='ELIMINAR',
                    tabla='articulo',
                    registro_id=idarticulo,
                    datos_anteriores=str(datos_anteriores) if datos_anteriores else None
                )
                
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Error eliminando artículo {idarticulo}: {e}")
            return False
    
    def actualizar_precio(self, idarticulo: int, nuevo_precio: float) -> bool:
        """
        Actualiza el precio de venta de un artículo
        
        Args:
            idarticulo (int): ID del artículo a actualizar
            nuevo_precio (float): Nuevo precio en USD
            
        Returns:
            bool: True si se actualizó correctamente, False en caso contrario
        """
        try:
            # Validar ID
            if not idarticulo or idarticulo <= 0:
                logger.warning(f"⚠️ ID de artículo inválido: {idarticulo}")
                return False
            
            # Validar precio
            if nuevo_precio <= 0:
                logger.warning(f"⚠️ Precio inválido: {nuevo_precio}")
                return False
            
            # Obtener datos anteriores para auditoría
            datos_anteriores = self.repositorio.obtener_por_id(idarticulo)
            
            # Llamar al repositorio para actualizar
            resultado = self.repositorio.actualizar_precio(idarticulo, nuevo_precio)
            
            if resultado:
                logger.info(f"✅ Precio actualizado para artículo {idarticulo}: ${nuevo_precio:.2f}")
                
                # Registrar en auditoría si existe el método
                if hasattr(self, 'registrar_auditoria'):
                    self.registrar_auditoria(
                        accion='ACTUALIZAR_PRECIO',
                        tabla='articulo',
                        registro_id=idarticulo,
                        datos_anteriores=f"Precio anterior: ${datos_anteriores.get('precio_venta', 0):.2f}" if datos_anteriores else None,
                        datos_nuevos=f"Precio nuevo: ${nuevo_precio:.2f}"
                    )
                
                return True
            else:
                logger.error(f"❌ Error actualizando precio del artículo {idarticulo} en repositorio")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error en actualizar_precio: {e}")
            return False
    
    def obtener_categorias(self) -> List[Dict]:
        """
        Obtiene la lista de categorías
        
        Returns:
            List[Dict]: Lista de categorías
        """
        try:
            if self.categoria_service:
                return self.categoria_service.listar_categorias()
            else:
                logger.warning("⚠️ Servicio de categorías no disponible")
                return []
        except Exception as e:
            logger.error(f"❌ Error obteniendo categorías: {e}")
            return []
    
    def __del__(self):
        """Cierra conexiones al destruir el objeto"""
        try:
            if hasattr(self, 'repositorio') and self.repositorio:
                if hasattr(self.repositorio, 'cerrar_conexion'):
                    self.repositorio.cerrar_conexion()
        except:
            pass
