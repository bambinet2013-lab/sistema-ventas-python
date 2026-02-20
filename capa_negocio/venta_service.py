"""
Servicio para la gestión de ventas - VERSIÓN CON MULTIMONEDA Y TASAS DE CAMBIO
"""
from loguru import logger
from capa_negocio.base_service import BaseService
from capa_negocio.moneda_service import IGTFService
from capa_negocio.tasa_service import TasaService

class VentaService(BaseService):
    """Servicio que implementa la lógica de negocio para ventas con soporte multimoneda"""
    
    def __init__(self, repositorio, cliente_service, trabajador_service, inventario_service, tasa_repo=None):
        """
        Inicializa el servicio de ventas
        
        Args:
            repositorio: Instancia de VentaRepositorio
            cliente_service: Servicio de clientes
            trabajador_service: Servicio de trabajadores
            inventario_service: Servicio de inventario
            tasa_repo: Repositorio de tasas (opcional, para multimoneda)
        """
        super().__init__()
        self.repositorio = repositorio
        self.cliente_service = cliente_service
        self.trabajador_service = trabajador_service
        self.inventario_service = inventario_service
        
        # Inicializar servicio de tasas si se proporciona el repositorio
        if tasa_repo:
            self.tasa_service = TasaService(tasa_repo)
            logger.info("✅ Servicio de tasas inicializado")
        else:
            self.tasa_service = None
            logger.warning("⚠️ Servicio de tasas no disponible - solo moneda VES")
        
        logger.info("✅ VentaService inicializado")
    
    def listar(self):
        """
        Lista todas las ventas
        
        Returns:
            list: Lista de ventas o lista vacía si hay error
        """
        try:
            return self.repositorio.listar()
        except Exception as e:
            logger.error(f"Error al listar ventas: {e}")
            return []
    
    def obtener_por_id(self, idventa):
        """
        Obtiene una venta por su ID con todos los detalles
        
        Args:
            idventa (int): ID de la venta
            
        Returns:
            dict: Datos de la venta o None si no existe
        """
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
                  serie, numero_comprobante, igv, detalle,
                  moneda='VES', moneda_pago=None, tasa_cambio=None):
        """
        Registra una nueva venta con soporte multimoneda
        
        Args:
            idtrabajador (int): ID del trabajador que realiza la venta
            idcliente (int or None): ID del cliente (puede ser None para consumidor final)
            tipo_comprobante (str): FACTURA, BOLETA, TICKET
            serie (str): Serie del comprobante
            numero_comprobante (str): Número del comprobante
            igv (float): Porcentaje de IGV
            detalle (list): Lista de items de la venta
            moneda (str): Moneda de la factura (VES, USD, EUR)
            moneda_pago (str): Moneda con que paga el cliente (si es diferente)
            tasa_cambio (float): Tasa de cambio (si viene, se usa; si no, se pide)
            
        Returns:
            int or None: ID de la venta creada o None si hay error
        """
        try:
            # Validar campos obligatorios
            if not self.validar_entero_positivo(idtrabajador, "ID del trabajador"):
                logger.error("ID del trabajador inválido")
                return None
            
            # Para consumidor final, idcliente puede ser None
            if idcliente is not None:
                if not self.validar_entero_positivo(idcliente, "ID del cliente"):
                    return None
                
                # Verificar que el cliente existe
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
            
            # ===== GESTIÓN DE TASA DE CAMBIO =====
            tasa_final = tasa_cambio
            usuario_nombre = None
            
            # Obtener nombre del usuario para registro
            usuario_actual = self.trabajador_service.get_usuario_actual()
            if usuario_actual:
                usuario_nombre = f"{usuario_actual['nombre']} {usuario_actual['apellidos']}"
            
            # Si la venta es en USD o el pago es en USD, necesitamos la tasa
            if moneda in ['USD', 'EUR'] or moneda_pago in ['USD', 'EUR']:
                # Si no nos pasaron la tasa, la pedimos al usuario
                if tasa_final is None:
                    if self.tasa_service is None:
                        logger.error("No hay servicio de tasas disponible")
                        return None
                    
                    # Determinar qué moneda preguntar
                    moneda_tasa = moneda if moneda != 'VES' else moneda_pago
                    
                    tasa_final = self.tasa_service.obtener_tasa_para_venta(
                        moneda=moneda_tasa,
                        usuario=usuario_nombre
                    )
                    
                    if tasa_final is None:
                        logger.info("Venta cancelada por el usuario")
                        return None
                
                logger.info(f"💱 Tasa de cambio aplicada: 1 USD = {tasa_final:.2f} VES")
            else:
                tasa_final = 1.0  # Tasa por defecto para VES
            
            # ===== CÁLCULO DE MONTOS =====
            # Calcular subtotal y total
            subtotal = sum(item['cantidad'] * item['precio_venta'] for item in detalle)
            iva_total = subtotal * (igv / 100)
            total = subtotal + iva_total
            
            # Calcular montos por moneda
            monto_bs = None
            monto_divisa = None
            
            if moneda == 'VES':
                monto_bs = total
                if moneda_pago == 'USD':
                    monto_divisa = total / tasa_final
                    logger.info(f"   Pago en USD: ${monto_divisa:.2f} (tasa {tasa_final:.2f})")
            else:  # USD u otra divisa
                monto_divisa = total
                monto_bs = total * tasa_final
                logger.info(f"   Equivalente en Bs.: Bs. {monto_bs:.2f} (tasa {tasa_final:.2f})")
            
            # Calcular IGTF si aplica (3% para pagos en divisas)
            igtf = IGTFService.calcular_igtf(
                monto=total,
                moneda_pago=moneda_pago or moneda,
                moneda_transaccion=moneda
            )
            if igtf > 0:
                logger.info(f"💰 IGTF (3%): {igtf:.2f}")
            
            # ===== VALIDAR STOCK =====
            logger.info("🔍 Verificando stock disponible...")
            for idx, item in enumerate(detalle, 1):
                # Validar que cada item tenga los campos requeridos
                if 'idarticulo' not in item:
                    logger.error(f"Item {idx} de venta sin ID de artículo")
                    return None
                
                if 'cantidad' not in item:
                    logger.error(f"Item {idx} de venta sin cantidad")
                    return None
                
                if 'precio_venta' not in item:
                    logger.error(f"Item {idx} de venta sin precio")
                    return None
                
                # Validar que cantidad sea entero positivo
                if not self.validar_entero_positivo(item['cantidad'], f"Cantidad del item {idx}"):
                    return None
                
                # Validar que precio sea positivo
                if not self.validar_decimal_positivo(item['precio_venta'], f"Precio del item {idx}"):
                    return None
                
                # Verificar stock usando inventario_service
                try:
                    stock_actual = self.inventario_service.obtener_stock_articulo(item['idarticulo'])
                    logger.info(f"   Artículo ID {item['idarticulo']}: Stock disponible {stock_actual}, Solicitado {item['cantidad']}")
                    
                    if item['cantidad'] > stock_actual:
                        logger.error(f"❌ Stock insuficiente para artículo ID {item['idarticulo']}. "
                                   f"Disponible: {stock_actual}, Solicitado: {item['cantidad']}")
                        return None
                except AttributeError as e:
                    logger.error(f"ERROR: inventario_service no tiene el método obtener_stock_articulo")
                    logger.error(f"   - Tipo de inventario_service: {type(self.inventario_service).__name__}")
                    return None
            
            # Validar que el trabajador existe
            trabajador = self.trabajador_service.obtener_por_id(idtrabajador)
            if not trabajador:
                logger.error(f"Trabajador ID {idtrabajador} no encontrado")
                return None
            
            # ===== REGISTRAR VENTA =====
            logger.info("📝 Registrando venta en base de datos...")
            idventa = self.repositorio.crear(
                idtrabajador=idtrabajador,
                idcliente=idcliente,
                tipo_comprobante=tipo_comprobante,
                serie=serie,
                numero_comprobante=numero_comprobante,
                igv=igv,
                estado='REGISTRADO',
                moneda=moneda,
                tasa_cambio=tasa_final,
                monto_bs=monto_bs,
                monto_divisa=monto_divisa
            )
            
            if not idventa:
                logger.error("No se pudo crear la venta en la base de datos")
                return None
            
            logger.info(f"✅ Venta #{idventa} creada en BD")
            
            # ===== REGISTRAR DETALLE Y DESCONTAR STOCK =====
            for item in detalle:
                # Agregar detalle a la venta
                detalle_id = self.repositorio.agregar_detalle(
                    idventa=idventa,
                    idarticulo=item['idarticulo'],
                    cantidad=item['cantidad'],
                    precio_venta=item['precio_venta']
                )
                
                if not detalle_id:
                    logger.error(f"Error al agregar detalle para artículo {item['idarticulo']}")
                    continue
                
                logger.info(f"   ✅ Detalle agregado: {item['cantidad']} x {item['precio_venta']:.2f}")
                
                # Actualizar stock usando inventario_service
                self.inventario_service.descontar_stock(
                    idarticulo=item['idarticulo'],
                    cantidad=item['cantidad'],
                    idventa=idventa,
                    precio_unitario=item['precio_venta']
                )
            
            # ===== RESUMEN FINAL =====
            tipo_cliente = "CONSUMIDOR FINAL" if idcliente is None else "CLIENTE IDENTIFICADO"
            
            logger.info(f"✅ Venta {idventa} registrada correctamente")
            logger.info(f"   Cliente: {tipo_cliente}")
            logger.info(f"   Moneda factura: {moneda}")
            
            if moneda == 'VES':
                logger.info(f"   Total: Bs. {total:.2f}")
                if moneda_pago == 'USD':
                    logger.info(f"   Pagado en USD: ${monto_divisa:.2f}")
            else:
                if moneda == 'USD':
                    logger.info(f"   Total: ${total:.2f} USD")
                elif moneda == 'EUR':
                    logger.info(f"   Total: €{total:.2f} EUR")
                logger.info(f"   Equivalente: Bs. {monto_bs:.2f}")
            
            if igtf > 0:
                logger.info(f"   IGTF (3%): {igtf:.2f}")
            
            return idventa
            
        except Exception as e:
            logger.error(f"❌ Error al registrar venta: {e}")
            return None
    
    def anular(self, idventa):
        """
        Anula una venta (cambia estado a ANULADO) y repone stock
        
        Args:
            idventa (int): ID de la venta a anular
            
        Returns:
            bool: True si se anuló correctamente, False en caso contrario
        """
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
            
            # Anular venta
            resultado = self.repositorio.anular(idventa)
            
            if resultado:
                logger.info(f"✅ Venta {idventa} anulada correctamente")
                
                # Reponer stock
                if venta.get('detalle'):
                    logger.info("   Reponiendo stock...")
                    for item in venta['detalle']:
                        self.inventario_service.reponer_stock(
                            idarticulo=item['idarticulo'],
                            cantidad=item['cantidad'],
                            idingreso=None,
                            precio_compra=item['precio_venta']
                        )
            else:
                logger.error(f"❌ No se pudo anular la venta {idventa}")
            
            return resultado
            
        except Exception as e:
            logger.error(f"Error al anular venta {idventa}: {e}")
            return False
    
    def ventas_por_cliente(self, idcliente):
        """
        Obtiene todas las ventas de un cliente específico
        
        Args:
            idcliente (int): ID del cliente
            
        Returns:
            list: Lista de ventas del cliente
        """
        try:
            if not self.validar_entero_positivo(idcliente, "ID del cliente"):
                return []
            return self.repositorio.ventas_por_cliente(idcliente)
        except Exception as e:
            logger.error(f"Error al obtener ventas del cliente {idcliente}: {e}")
            return []
    
    def ventas_por_fecha(self, fecha_inicio, fecha_fin):
        """
        Obtiene ventas en un rango de fechas
        
        Args:
            fecha_inicio: Fecha inicial
            fecha_fin: Fecha final
            
        Returns:
            list: Lista de ventas en el rango
        """
        try:
            return self.repositorio.ventas_por_fecha(fecha_inicio, fecha_fin)
        except Exception as e:
            logger.error(f"Error al obtener ventas por fecha: {e}")
            return []
    
    def total_ventas_dia(self, fecha=None):
        """
        Calcula el total de ventas de un día específico
        
        Args:
            fecha: Fecha (si es None, usa la fecha actual)
            
        Returns:
            float: Total de ventas del día
        """
        try:
            from datetime import datetime
            if fecha is None:
                fecha = datetime.now().date()
            ventas = self.repositorio.ventas_por_fecha(fecha, fecha)
            return sum(v.get('total', 0) for v in ventas)
        except Exception as e:
            logger.error(f"Error al calcular total de ventas del día: {e}")
            return 0.0
    
    def ventas_del_dia(self):
        """
        Obtiene las ventas del día actual
        
        Returns:
            list: Lista de ventas del día
        """
        try:
            from datetime import datetime
            hoy = datetime.now().date()
            return self.ventas_por_fecha(hoy, hoy)
        except Exception as e:
            logger.error(f"Error al obtener ventas del día: {e}")
            return []
    
    def resumen_ventas(self, fecha_inicio, fecha_fin):
        """
        Genera un resumen de ventas en un período
        
        Args:
            fecha_inicio: Fecha inicial
            fecha_fin: Fecha final
            
        Returns:
            dict: Resumen con totales y estadísticas
        """
        try:
            ventas = self.ventas_por_fecha(fecha_inicio, fecha_fin)
            
            total_ventas = len(ventas)
            total_ingresos = sum(v.get('total', 0) for v in ventas)
            promedio_por_venta = total_ingresos / total_ventas if total_ventas > 0 else 0
            
            # Contar por tipo de comprobante
            por_tipo = {}
            # Resumen por moneda
            por_moneda = {'VES': 0, 'USD': 0, 'EUR': 0}
            
            for v in ventas:
                tipo = v.get('tipo_comprobante', 'OTRO')
                por_tipo[tipo] = por_tipo.get(tipo, 0) + 1
                
                moneda = v.get('moneda', 'VES')
                if moneda in por_moneda:
                    por_moneda[moneda] += v.get('total', 0)
            
            return {
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin,
                'total_ventas': total_ventas,
                'total_ingresos': total_ingresos,
                'promedio_por_venta': promedio_por_venta,
                'por_tipo': por_tipo,
                'por_moneda': por_moneda,
                'ventas': ventas
            }
            
        except Exception as e:
            logger.error(f"Error al generar resumen de ventas: {e}")
            return {}
