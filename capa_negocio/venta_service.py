"""
Servicio para la gestión de ventas
"""
from loguru import logger
from capa_negocio.base_service import BaseService

class VentaService(BaseService):
    """Servicio que implementa la lógica de negocio para ventas"""
    
    def __init__(self, repositorio, cliente_service, trabajador_service, inventario_service):
        """
        Inicializa el servicio de ventas
        
        Args:
            repositorio: Instancia de VentaRepositorio
            cliente_service: Servicio de clientes
            trabajador_service: Servicio de trabajadores
            inventario_service: Servicio de inventario
        """
        super().__init__()
        self.repositorio = repositorio
        self.cliente_service = cliente_service
        self.trabajador_service = trabajador_service
        self.inventario_service = inventario_service
        logger.info("✅ VentaService inicializado")
        logger.info(f"   - inventario_service tipo: {type(inventario_service).__name__}")
    
    def listar(self):
        """Lista todas las ventas"""
        try:
            return self.repositorio.listar()
        except Exception as e:
            logger.error(f"Error al listar ventas: {e}")
            return []
    
    def obtener_por_id(self, idventa):
        """Obtiene una venta por su ID con todos los detalles"""
        try:
            if not self.validar_entero_positivo(idventa, "ID de venta"):
                return None
            
            venta = self.repositorio.obtener_por_id(idventa)
            if not venta:
                logger.warning(f"Venta {idventa} no encontrada")
                return None
            
            detalles = self.repositorio.obtener_detalles(idventa)
            venta['detalle'] = detalles
            return venta
            
        except Exception as e:
            logger.error(f"Error al obtener venta {idventa}: {e}")
            return None
    
    def registrar(self, idtrabajador, idcliente, tipo_comprobante, 
                  serie, numero_comprobante, igv, detalle):
        """
        Registra una nueva venta (idcliente puede ser None para consumidor final)
        """
        try:
            # Validar trabajador
            if not self.validar_entero_positivo(idtrabajador, "ID del trabajador"):
                logger.error("ID del trabajador inválido")
                return None
            
            # Validar cliente (puede ser None para consumidor final)
            if idcliente is not None:
                if not self.validar_entero_positivo(idcliente, "ID del cliente"):
                    return None
                
                cliente = self.cliente_service.obtener_por_id(idcliente)
                if not cliente:
                    logger.error(f"Cliente {idcliente} no encontrado")
                    return None
            
            # Validar tipo de comprobante
            tipos_validos = ['FACTURA', 'BOLETA', 'TICKET']
            if tipo_comprobante not in tipos_validos:
                logger.error(f"Tipo de comprobante inválido: {tipo_comprobante}")
                return None
            
            # Validar serie y número
            if not serie or not serie.strip():
                logger.error("La serie del comprobante es obligatoria")
                return None
            
            if not numero_comprobante or not numero_comprobante.strip():
                logger.error("El número del comprobante es obligatorio")
                return None
            
            # Validar IGV
            if not self.validar_decimal_positivo(igv, "IGV"):
                return None
            
            # Validar detalle
            if not detalle or len(detalle) == 0:
                logger.error("La venta debe tener al menos un producto")
                return None
            
            # VALIDAR STOCK USANDO INVENTARIO_SERVICE (CORREGIDO)
            logger.info("🔍 Verificando stock disponible...")
            for item in detalle:
                # Validar campos del item
                if 'idarticulo' not in item:
                    logger.error("Item de venta sin ID de artículo")
                    return None
                
                if 'cantidad' not in item:
                    logger.error("Item de venta sin cantidad")
                    return None
                
                if 'precio_venta' not in item:
                    logger.error("Item de venta sin precio")
                    return None
                
                if not self.validar_entero_positivo(item['cantidad'], "Cantidad"):
                    return None
                
                if not self.validar_decimal_positivo(item['precio_venta'], "Precio"):
                    return None
                
                # USAR INVENTARIO_SERVICE (NO articulo_service)
                stock_actual = self.inventario_service.obtener_stock_articulo(item['idarticulo'])
                logger.info(f"   Artículo {item['idarticulo']}: Stock {stock_actual}, Solicitado {item['cantidad']}")
                
                if item['cantidad'] > stock_actual:
                    logger.error(f"Stock insuficiente. Disponible: {stock_actual}, Solicitado: {item['cantidad']}")
                    return None
            
            # Validar trabajador existe
            trabajador = self.trabajador_service.obtener_por_id(idtrabajador)
            if not trabajador:
                logger.error(f"Trabajador {idtrabajador} no encontrado")
                return None
            
            # Registrar venta
            logger.info("📝 Registrando venta en base de datos...")
            idventa = self.repositorio.crear(
                idtrabajador=idtrabajador,
                idcliente=idcliente,
                tipo_comprobante=tipo_comprobante,
                serie=serie,
                numero_comprobante=numero_comprobante,
                igv=igv,
                estado='REGISTRADO'
            )
            
            if not idventa:
                logger.error("No se pudo crear la venta")
                return None
            
            logger.info(f"✅ Venta #{idventa} creada")
            
            # Registrar detalle y descontar stock
            for item in detalle:
                detalle_id = self.repositorio.agregar_detalle(
                    idventa=idventa,
                    idarticulo=item['idarticulo'],
                    cantidad=item['cantidad'],
                    precio_venta=item['precio_venta']
                )
                
                if detalle_id:
                    logger.info(f"   ✅ Detalle: {item['cantidad']} x {item['precio_venta']}")
                    
                    # Descontar stock usando inventario_service
                    self.inventario_service.descontar_stock(
                        idarticulo=item['idarticulo'],
                        cantidad=item['cantidad'],
                        idventa=idventa
                    )
                else:
                    logger.error(f"Error agregando detalle para artículo {item['idarticulo']}")
            
            # Calcular total
            total = sum(item['cantidad'] * item['precio_venta'] for item in detalle)
            iva_total = total * (igv / 100)
            total_con_iva = total + iva_total
            
            tipo_cliente = "CONSUMIDOR FINAL" if idcliente is None else "CLIENTE IDENTIFICADO"
            logger.info(f"✅ Venta {idventa} completada - {tipo_cliente} - Total: Bs.{total_con_iva:.2f}")
            
            return idventa
            
        except Exception as e:
            logger.error(f"❌ Error al registrar venta: {e}")
            return None
    
    def anular(self, idventa):
        """Anula una venta"""
        try:
            if not self.validar_entero_positivo(idventa, "ID de venta"):
                return False
            
            venta = self.obtener_por_id(idventa)
            if not venta:
                logger.error(f"Venta {idventa} no encontrada")
                return False
            
            if venta.get('estado') == 'ANULADO':
                logger.warning(f"La venta {idventa} ya está anulada")
                return False
            
            resultado = self.repositorio.anular(idventa)
            
            if resultado:
                logger.info(f"✅ Venta {idventa} anulada correctamente")
                
                # Reponer stock
                if venta.get('detalle'):
                    for item in venta['detalle']:
                        self.inventario_service.reponer_stock(
                            idarticulo=item['idarticulo'],
                            cantidad=item['cantidad'],
                            idingreso=None
                        )
            else:
                logger.error(f"❌ No se pudo anular la venta {idventa}")
            
            return resultado
            
        except Exception as e:
            logger.error(f"Error al anular venta {idventa}: {e}")
            return False
    
    def ventas_por_cliente(self, idcliente):
        """Obtiene ventas de un cliente"""
        try:
            if not self.validar_entero_positivo(idcliente, "ID del cliente"):
                return []
            return self.repositorio.ventas_por_cliente(idcliente)
        except Exception as e:
            logger.error(f"Error al obtener ventas del cliente {idcliente}: {e}")
            return []
    
    def ventas_por_fecha(self, fecha_inicio, fecha_fin):
        """Obtiene ventas por rango de fechas"""
        try:
            return self.repositorio.ventas_por_fecha(fecha_inicio, fecha_fin)
        except Exception as e:
            logger.error(f"Error al obtener ventas por fecha: {e}")
            return []
    
    def total_ventas_dia(self, fecha=None):
        """Calcula el total de ventas del día"""
        try:
            from datetime import datetime
            if fecha is None:
                fecha = datetime.now().date()
            ventas = self.repositorio.ventas_por_fecha(fecha, fecha)
            return sum(v.get('total', 0) for v in ventas)
        except Exception as e:
            logger.error(f"Error al calcular total de ventas del día: {e}")
            return 0.0
