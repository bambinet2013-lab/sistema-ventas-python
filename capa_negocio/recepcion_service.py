"""
Servicio para gestión de recepciones de mercancía
"""
from loguru import logger
from capa_datos.recepcion_repo import RecepcionRepositorio
from capa_datos.compra_repo import CompraRepositorio
from capa_datos.articulo_repo import ArticuloRepositorio
from capa_negocio.inventario_service import InventarioService

class RecepcionService:
    def __init__(self):
        self.repo = RecepcionRepositorio()
        self.compra_repo = CompraRepositorio()
        self.articulo_repo = ArticuloRepositorio()
        self.inventario_service = InventarioService()
    
    def recibir_mercancia(self, idproveedor, idtrabajador, items, idcompra_original=None, observaciones=None):
        """
        Registra una recepción de mercancía
        items: lista de dict con idarticulo, cantidad_recibida, costo_unitario_usd, 
               opcional: iddetalle_compra_original, cantidad_pedida, lote, fecha_vencimiento
        """
        try:
            if not items:
                logger.warning("⚠️ No hay items en la recepción")
                return None
            
            # Obtener tasa del día
            from capa_negocio.tasa_service import TasaService
            tasa_service = TasaService()
            tasa_bcv = tasa_service.obtener_tasa_del_dia('USD')
            
            if tasa_bcv <= 0:
                logger.error("❌ Tasa BCV no disponible")
                return None
            
            # Crear recepción
            idrecepcion = self.repo.crear_recepcion(
                idproveedor, idtrabajador, idcompra_original, observaciones
            )
            
            if not idrecepcion:
                return None
            
            # Procesar cada item
            for item in items:
                # Agregar detalle de recepción
                self.repo.agregar_detalle(
                    idrecepcion=idrecepcion,
                    idarticulo=item['idarticulo'],
                    cantidad_recibida=item['cantidad_recibida'],
                    costo_unitario_usd=item['costo_unitario_usd'],
                    tasa_bcv=tasa_bcv,
                    iddetalle_compra_original=item.get('iddetalle_compra_original'),
                    cantidad_pedida=item.get('cantidad_pedida'),
                    lote=item.get('lote'),
                    fecha_vencimiento=item.get('fecha_vencimiento')
                )
                
                # Calcular costo en bolívares
                costo_bs = item['costo_unitario_usd'] * tasa_bcv
                
                # Actualizar inventario (entrada por recepción)
                self.inventario_service.registrar_movimiento(
                    idarticulo=item['idarticulo'],
                    tipo_movimiento='ENTRADA',
                    cantidad=item['cantidad_recibida'],
                    referencia=f"RECEPCIÓN #{idrecepcion}",
                    precio_compra=costo_bs,
                    precio_compra_usd=item['costo_unitario_usd'],
                    lote=item.get('lote'),
                    fecha_vencimiento=item.get('fecha_vencimiento')
                )
                
                # Actualizar costo promedio del artículo
                self._actualizar_costo_promedio(
                    item['idarticulo'], 
                    item['cantidad_recibida'], 
                    item['costo_unitario_usd'],
                    tasa_bcv
                )
            
            logger.info(f"✅ Recepción #{idrecepcion} procesada con {len(items)} items")
            return idrecepcion
            
        except Exception as e:
            logger.error(f"❌ Error procesando recepción: {e}")
            return None
    
    def _actualizar_costo_promedio(self, idarticulo, cantidad_nueva, precio_usd, tasa_bcv):
        """Actualiza el costo promedio ponderado en USD y Bs"""
        try:
            articulo = self.articulo_repo.obtener_por_id(idarticulo)
            if not articulo:
                return
            
            stock_actual = articulo['stock_actual']
            costo_usd_actual = articulo.get('costo_promedio_usd', 0) or 0
            
            # Calcular nuevo costo promedio en USD
            if stock_actual == 0:
                nuevo_costo_usd = precio_usd
            else:
                total_costo_usd_actual = stock_actual * costo_usd_actual
                total_costo_usd_nuevo = cantidad_nueva * precio_usd
                nuevo_stock = stock_actual + cantidad_nueva
                nuevo_costo_usd = (total_costo_usd_actual + total_costo_usd_nuevo) / nuevo_stock
            
            # Actualizar en BD (necesitas agregar campo costo_promedio_usd a articulo)
            self.articulo_repo.actualizar_costo_promedio_usd(idarticulo, nuevo_costo_usd)
            
        except Exception as e:
            logger.error(f"❌ Error actualizando costo promedio: {e}")
    
    def obtener_recepciones_pendientes(self, idcompra=None):
        """Obtiene recepciones pendientes"""
        return self.repo.buscar_recepciones_pendientes(idcompra)
