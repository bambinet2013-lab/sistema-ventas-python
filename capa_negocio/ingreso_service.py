from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger
from capa_negocio.base_service import BaseService

class IngresoService(BaseService):
    """Servicio para gestión de ingresos de mercancía"""
    
    def __init__(self, repositorio, articulo_service=None, proveedor_service=None, trabajador_service=None):
        self.repositorio = repositorio
        self.articulo_service = articulo_service
        self.proveedor_service = proveedor_service
        self.trabajador_service = trabajador_service
    
    def listar_ingresos(self) -> List[Dict]:
        """Lista todos los ingresos"""
        try:
            return self.repositorio.listar()
        except Exception as e:
            logger.error(f"❌ Error al listar ingresos: {e}")
            return []
    
    def obtener_ingreso(self, idingreso: int) -> Optional[Dict]:
        """Obtiene un ingreso por ID con su detalle"""
        if not self.validar_entero_positivo(idingreso, "ID de ingreso"):
            return None
        try:
            return self.repositorio.obtener_por_id(idingreso)
        except Exception as e:
            logger.error(f"❌ Error al obtener ingreso {idingreso}: {e}")
            return None
    
    def registrar_ingreso(self, idtrabajador: int, idproveedor: int,
                          tipo_comprobante: str, serie: str, numero_comprobante: str,
                          igv: float, detalle: List[Dict] = None,
                          fecha: datetime = None) -> Optional[int]:
        """
        Registra un nuevo ingreso con su detalle
        detalle: lista de dict con idarticulo, cantidad, precio_compra
        """
        
        # Validaciones básicas
        if not self.validar_entero_positivo(idtrabajador, "trabajador"):
            logger.warning("⚠️ ID de trabajador inválido")
            return None
        if not self.validar_entero_positivo(idproveedor, "proveedor"):
            logger.warning("⚠️ ID de proveedor inválido")
            return None
        if not self.validar_requerido(tipo_comprobante, "tipo de comprobante"):
            logger.warning("⚠️ Tipo de comprobante requerido")
            return None
        if not self.validar_requerido(serie, "serie"):
            logger.warning("⚠️ Serie requerida")
            return None
        if not self.validar_requerido(numero_comprobante, "número de comprobante"):
            logger.warning("⚠️ Número de comprobante requerido")
            return None
        if not self.validar_decimal_positivo(igv, "IGV", permitir_cero=True):
            logger.warning("⚠️ IGV inválido")
            return None
        
        # Validar que existan proveedor y trabajador
        if self.proveedor_service:
            proveedor = self.proveedor_service.obtener_por_id(idproveedor)
            if not proveedor:
                logger.warning(f"⚠️ El proveedor {idproveedor} no existe")
                return None
        
        if self.trabajador_service:
            trabajador = self.trabajador_service.obtener_por_id(idtrabajador)
            if not trabajador:
                logger.warning(f"⚠️ El trabajador {idtrabajador} no existe")
                return None
        
        # Validar detalle
        if not detalle or len(detalle) == 0:
            logger.warning("⚠️ El ingreso debe tener al menos un artículo")
            return None
        
        total = 0
        for item in detalle:
            # Validar artículo
            if not self.validar_entero_positivo(item.get('idarticulo'), "ID de artículo"):
                logger.warning(f"⚠️ ID de artículo inválido: {item.get('idarticulo')}")
                return None
            if not self.validar_entero_positivo(item.get('cantidad'), "cantidad"):
                logger.warning(f"⚠️ Cantidad inválida: {item.get('cantidad')}")
                return None
            if not self.validar_decimal_positivo(item.get('precio_compra'), "precio de compra"):
                logger.warning(f"⚠️ Precio de compra inválido: {item.get('precio_compra')}")
                return None
            
            # Verificar que el artículo existe
            if self.articulo_service:
                articulo = self.articulo_service.obtener_por_id(item['idarticulo'])
                if not articulo:
                    logger.warning(f"⚠️ El artículo {item['idarticulo']} no existe")
                    return None
            
            # Calcular subtotal
            subtotal = item['cantidad'] * item['precio_compra']
            total += subtotal
            logger.info(f"   - Artículo ID {item['idarticulo']}: {item['cantidad']} und @ Bs.{item['precio_compra']:.2f} = Bs.{subtotal:.2f}")
        
        logger.info(f"💰 Total del ingreso: Bs.{total:.2f}")
        
        try:
            # Registrar el ingreso
            if not fecha:
                fecha = datetime.now()
            
            idingreso = self.repositorio.insertar(
                idtrabajador, idproveedor, tipo_comprobante,
                serie, numero_comprobante, igv,
                fecha=fecha, detalle=detalle
            )
            
            if idingreso:
                logger.success(f"✅ Ingreso #{idingreso} registrado con {len(detalle)} productos")
                logger.info(f"📦 Stock actualizado automáticamente")
                return idingreso
            else:
                logger.error("❌ No se pudo insertar el ingreso en la base de datos")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error al registrar ingreso: {e}")
            return None
    
    def anular_ingreso(self, idingreso: int) -> bool:
        """Anula un ingreso"""
        if not self.validar_entero_positivo(idingreso, "ID de ingreso"):
            return False
        try:
            return self.repositorio.anular(idingreso)
        except Exception as e:
            logger.error(f"❌ Error al anular ingreso {idingreso}: {e}")
            return False
