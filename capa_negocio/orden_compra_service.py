"""
Servicio para gestión de órdenes de compra
"""
from loguru import logger
from capa_datos.orden_compra_repo import OrdenCompraRepositorio
from capa_datos.conexion import ConexionDB
from capa_negocio.tasa_service import TasaService

class OrdenCompraService:
    def __init__(self):
        self.db = ConexionDB()
        self.conn = self.db.conectar()
        self.repo = OrdenCompraRepositorio()
        self.tasa_service = TasaService()
    
    def registrar_orden(self, codigo_factura, idproveedor, idtrabajador, 
                        fecha_compra, monto_total_usd, fecha_estimada_llegada=None,
                        archivo_adjunto=None, estatus='POR_RECIBIR', observaciones=None):
        """Registra una nueva orden de compra"""
        try:
            # Obtener tasa BCV del día
            tasa_bcv = self.tasa_service.obtener_tasa_del_dia('USD')
            monto_total_bs = monto_total_usd * tasa_bcv if tasa_bcv else None
            
            idorden = self.repo.crear(
                codigo_factura, idproveedor, idtrabajador, fecha_compra,
                monto_total_usd, monto_total_bs, tasa_bcv,
                fecha_estimada_llegada, archivo_adjunto, estatus, observaciones
            )
            
            if idorden:
                logger.info(f"✅ Orden de compra #{idorden} - {codigo_factura} registrada")
                return idorden
            return None
            
        except Exception as e:
            logger.error(f"❌ Error registrando orden: {e}")
            return None
    
    def buscar_por_codigo_factura(self, codigo_factura):
        """Busca orden por código de factura"""
        return self.repo.buscar_por_codigo_factura(codigo_factura)
    
    def listar_ordenes_pendientes(self):
        """Lista órdenes pendientes de recepción"""
        return self.repo.listar_por_estatus('POR_RECIBIR')
    
    def actualizar_estatus(self, idorden, estatus):
        """Actualiza estatus de la orden"""
        return self.repo.actualizar_estatus(idorden, estatus)
    
    def __del__(self):
        try:
            if hasattr(self, 'db'):
                self.db.cerrar()
        except:
            pass
