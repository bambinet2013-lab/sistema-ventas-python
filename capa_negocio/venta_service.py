from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger
from capa_negocio.base_service import BaseService

class VentaService(BaseService):
    """Servicio de ventas con validaciones y lógica de negocio"""
    
    def __init__(self, repositorio, cliente_service=None, 
                 trabajador_service=None, articulo_service=None,
                 lote_service=None):
        self.repositorio = repositorio
        self.cliente_service = cliente_service
        self.trabajador_service = trabajador_service
        self.articulo_service = articulo_service
        self.lote_service = lote_service
    
    def listar(self) -> List[Dict]:
        """Lista todas las ventas"""
        try:
            return self.repositorio.listar()
        except Exception as e:
            logger.error(f"❌ Error al listar ventas: {e}")
            return []
    
    def obtener_por_id(self, idventa: int) -> Optional[Dict]:
        """Obtiene una venta por ID"""
        if not self.validar_entero_positivo(idventa, "ID de venta"):
            return None
        return self.repositorio.obtener_por_id(idventa)
    
    def registrar(self, idtrabajador: int, idcliente: int,
                  tipo_comprobante: str, serie: str, numero_comprobante: str,
                  igv: float, detalle: List[Dict] = None) -> Optional[int]:
        """
        Registra una nueva venta con validaciones completas
        detalle: lista de dict con idarticulo, cantidad, precio_venta
        """
        
        # Validaciones básicas
        if not self.validar_entero_positivo(idtrabajador, "trabajador"):
            return None
        if not self.validar_entero_positivo(idcliente, "cliente"):
            return None
        if not self.validar_requerido(tipo_comprobante, "tipo de comprobante"):
            return None
        if not self.validar_requerido(serie, "serie"):
            return None
        if not self.validar_requerido(numero_comprobante, "número de comprobante"):
            return None
        if not self.validar_decimal_positivo(igv, "IGV", permitir_cero=True):
            return None
        
        # Validar que existan cliente y trabajador
        if self.cliente_service:
            cliente = self.cliente_service.obtener_por_id(idcliente)
            if not cliente:
                logger.warning(f"⚠️ El cliente {idcliente} no existe")
                return None
        
        if self.trabajador_service:
            trabajador = self.trabajador_service.obtener_por_id(idtrabajador)
            if not trabajador:
                logger.warning(f"⚠️ El trabajador {idtrabajador} no existe")
                return None
        
        # Validar detalle
        if not detalle or len(detalle) == 0:
            logger.warning("⚠️ La venta debe tener al menos un artículo")
            return None
        
        total = 0
        for item in detalle:
            # Validar artículo
            if not self.validar_entero_positivo(item.get('idarticulo'), "ID de artículo"):
                return None
            if not self.validar_entero_positivo(item.get('cantidad'), "cantidad"):
                return None
            if not self.validar_decimal_positivo(item.get('precio_venta'), "precio de venta"):
                return None
            
            # Verificar stock si hay servicio de lotes
            if self.lote_service and hasattr(self.lote_service, 'obtener_stock_articulo'):
                stock_disponible = self.lote_service.obtener_stock_articulo(item['idarticulo'])
                if stock_disponible < item['cantidad']:
                    logger.warning(f"⚠️ Stock insuficiente para artículo {item['idarticulo']}. Disponible: {stock_disponible}")
                    return None
            
            # Calcular subtotal
            subtotal = item['cantidad'] * item['precio_venta']
            total += subtotal
        
        logger.info(f"💰 Total de venta calculado: {total}")
        
        try:
            return self.repositorio.insertar(
                idtrabajador, idcliente, tipo_comprobante,
                serie, numero_comprobante, igv,
                fecha=datetime.now(), detalle=detalle
            )
        except Exception as e:
            logger.error(f"❌ Error al registrar venta: {e}")
            return None
    
    def anular(self, idventa: int) -> bool:
        """Anula una venta (solo si es del día actual)"""
        if not self.validar_entero_positivo(idventa, "ID de venta"):
            return False
        
        venta = self.obtener_por_id(idventa)
        if not venta:
            return False
        
        # Solo se pueden anular ventas del día
        if venta['fecha'].date() != datetime.now().date():
            logger.warning("⚠️ Solo se pueden anular ventas del día actual")
            return False
        
        if venta['estado'] == 'ANULADO':
            logger.warning("⚠️ La venta ya está anulada")
            return False
        
        return self.repositorio.anular(idventa)
