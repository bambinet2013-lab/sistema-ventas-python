"""
Servicio para gestión de compras
"""
from loguru import logger
from capa_datos.compra_repo import CompraRepositorio
from capa_datos.articulo_repo import ArticuloRepositorio
from capa_negocio.inventario_service import InventarioService

class CompraService:
    def __init__(self):
        self.repo = CompraRepositorio()
        self.repo_articulo = ArticuloRepositorio()
        self.inventario_service = InventarioService()
    
    def registrar_compra(self, idproveedor, idtrabajador, tipo_comprobante, 
                         serie, numero, items, observaciones=None):
        try:
            if not items:
                logger.warning("No hay items en la compra")
                return None
            
            subtotal = 0
            for item in items:
                item['subtotal'] = item['cantidad'] * item['precio_compra']
                subtotal += item['subtotal']
            
            iva = subtotal * 0.16
            total = subtotal + iva
            
            idcompra = self.repo.crear(
                idproveedor, idtrabajador, tipo_comprobante, serie, numero,
                subtotal, iva, total, observaciones
            )
            
            if not idcompra:
                return None
            
            for item in items:
                self.repo.agregar_detalle(
                    idcompra, 
                    item['idarticulo'], 
                    item['cantidad'], 
                    item['precio_compra'], 
                    item['subtotal']
                )
                
                self._actualizar_costo_promedio(
                    item['idarticulo'], 
                    item['cantidad'], 
                    item['precio_compra']
                )
                
                self.inventario_service.registrar_movimiento(
                    idarticulo=item['idarticulo'],
                    tipo_movimiento='ENTRADA',
                    cantidad=item['cantidad'],
                    referencia=f"COMPRA #{idcompra}",
                    precio_compra=item['precio_compra']
                )
            
            logger.info(f"Compra #{idcompra} registrada con {len(items)} items")
            return idcompra
            
        except Exception as e:
            logger.error(f"Error registrando compra: {e}")
            return None
    
    def _actualizar_costo_promedio(self, idarticulo, cantidad_nueva, precio_nuevo):
        try:
            articulo = self.repo_articulo.obtener_por_id(idarticulo)
            if not articulo:
                return
            
            stock_actual = articulo['stock_actual']
            costo_actual = articulo.get('precio_compra', 0) or 0
            
            if stock_actual == 0:
                nuevo_costo = precio_nuevo
            else:
                total_costo_actual = stock_actual * costo_actual
                total_costo_nuevo = cantidad_nueva * precio_nuevo
                nuevo_stock = stock_actual + cantidad_nueva
                nuevo_costo = (total_costo_actual + total_costo_nuevo) / nuevo_stock
            
            self.repo_articulo.actualizar_precio_compra(idarticulo, nuevo_costo)
            
        except Exception as e:
            logger.error(f"Error actualizando costo promedio: {e}")
    
    def listar_compras(self):
        return self.repo.listar()
    
    def buscar_compra(self, idcompra):
        return self.repo.buscar_por_id(idcompra)
    
    def anular_compra(self, idcompra):
        try:
            compra = self.repo.buscar_por_id(idcompra)
            if not compra or compra['estado'] == 'ANULADA':
                return False
            
            for detalle in compra['detalles']:
                self.inventario_service.registrar_movimiento(
                    idarticulo=detalle['idarticulo'],
                    tipo_movimiento='SALIDA',
                    cantidad=detalle['cantidad'],
                    referencia=f"ANULACIÓN COMPRA #{idcompra}"
                )
            
            return self.repo.anular(idcompra)
            
        except Exception as e:
            logger.error(f"Error anulando compra: {e}")
            return False
