"""
Servicio para gestión de órdenes de compra
"""
from loguru import logger
from capa_datos.orden_compra_repo import OrdenCompraRepositorio
from capa_datos.conexion import ConexionDB
from capa_negocio.tasa_service import TasaService
from capa_datos.tasa_repo import TasaRepositorio

class OrdenCompraService:
    def __init__(self):
        """Inicializa el servicio de órdenes de compra"""
        self.db = ConexionDB()
        self.conn = self.db.conectar()
        self.repo = OrdenCompraRepositorio()
        
        # Inicializar servicio de tasas con su propia conexión
        try:
            self.db_tasa = ConexionDB()
            self.conn_tasa = self.db_tasa.conectar()
            if self.conn_tasa:
                tasa_repo = TasaRepositorio(self.conn_tasa)
                self.tasa_service = TasaService(tasa_repo)
                logger.info("✅ Servicio de tasas inicializado en OrdenCompraService")
            else:
                logger.error("❌ No se pudo conectar para servicio de tasas")
                self.tasa_service = None
        except Exception as e:
            logger.error(f"❌ Error inicializando servicio de tasas: {e}")
            self.tasa_service = None
    
    def registrar_orden(self, codigo_factura, idproveedor, idtrabajador, 
                        fecha_compra, monto_total_usd, fecha_estimada_llegada=None,
                        archivo_adjunto=None, estatus='POR_RECIBIR', observaciones=None):
        """Registra una nueva orden de compra"""
        try:
            # Obtener tasa BCV del día
            tasa_bcv = None
            monto_total_bs = None
            
            if self.tasa_service:
                tasa_bcv = self.tasa_service.obtener_tasa_del_dia('USD')
                if tasa_bcv and tasa_bcv > 0:
                    monto_total_bs = monto_total_usd * tasa_bcv
                    logger.info(f"💰 Tasa aplicada: {tasa_bcv} Bs/USD - Monto Bs: {monto_total_bs:,.2f}")
            else:
                logger.warning("⚠️ Servicio de tasas no disponible")
            
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
        try:
            return self.repo.buscar_por_codigo_factura(codigo_factura)
        except Exception as e:
            logger.error(f"❌ Error buscando orden por código: {e}")
            return None
    
    def listar_ordenes_pendientes(self):
        """Lista órdenes pendientes de recepción"""
        try:
            return self.repo.listar_por_estatus('POR_RECIBIR')
        except Exception as e:
            logger.error(f"❌ Error listando órdenes pendientes: {e}")
            return []
    
    def listar_todas_ordenes(self):
        """Lista todas las órdenes"""
        try:
            return self.repo.listar_todas()
        except Exception as e:
            logger.error(f"❌ Error listando órdenes: {e}")
            return []
    
    def actualizar_estatus(self, idorden, estatus):
        """Actualiza estatus de la orden"""
        try:
            return self.repo.actualizar_estatus(idorden, estatus)
        except Exception as e:
            logger.error(f"❌ Error actualizando estatus: {e}")
            return False
    
    def __del__(self):
        """Cierra conexiones al destruir el objeto"""
        try:
            if hasattr(self, 'db'):
                self.db.cerrar()
            if hasattr(self, 'db_tasa'):
                self.db_tasa.cerrar()
        except:
            pass
