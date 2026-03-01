"""
Servicio para la gestión de inventario y stock - VERSIÓN CORREGIDA
"""
from loguru import logger
from capa_negocio.base_service import BaseService

class InventarioService(BaseService):
    """Servicio que implementa la lógica de negocio para inventario"""
    
    COLOR_ROJO = '\033[91m'
    COLOR_AMARILLO = '\033[93m'
    COLOR_VERDE = '\033[92m'
    COLOR_RESET = '\033[0m'
    
    def __init__(self, articulo_service):
        """Inicializa el servicio de inventario"""
        self.articulo_service = articulo_service
        from capa_datos.inventario_repo import InventarioRepositorio
        self.repo = InventarioRepositorio()
        logger.info("✅ InventarioService inicializado")
    
    def obtener_stock_articulo(self, idarticulo):
        """
        Obtiene el stock actual de un artículo desde la tabla kardex
        """
        try:
            if not self.validar_entero_positivo(idarticulo, "ID del artículo"):
                return 0
            
            # Obtener conexión
            conn = self.articulo_service.repositorio.conn
            cursor = conn.cursor()
            
            # Consultar el último stock registrado en kardex
            query = """
            SELECT TOP 1 stock_nuevo 
            FROM kardex 
            WHERE idarticulo = ? 
            ORDER BY fecha_movimiento DESC
            """
            cursor.execute(query, (idarticulo,))
            row = cursor.fetchone()
            
            if row and row[0] is not None:
                stock = row[0]
                logger.info(f"Stock del artículo {idarticulo} desde kardex: {stock} unidades")
                return stock
            else:
                # Si no hay movimientos, stock inicial = 0
                logger.warning(f"No hay registros en kardex para artículo {idarticulo}")
                return 0
            
        except Exception as e:
            logger.error(f"Error al obtener stock del artículo {idarticulo}: {e}")
            return 0

    def registrar_movimiento(self, idarticulo, tipo_movimiento, cantidad, 
                            referencia, precio_compra=None, lote=None, 
                            fecha_vencimiento=None):
        """
        Registra un movimiento en el kardex
        
        Args:
            idarticulo: ID del artículo
            tipo_movimiento: 'ENTRADA' o 'SALIDA'
            cantidad: Cantidad del movimiento
            referencia: Referencia del movimiento (ej: "RECEPCIÓN #123")
            precio_compra: Precio de compra (opcional)
            lote: Número de lote (opcional)
            fecha_vencimiento: Fecha de vencimiento (opcional)
            
        Returns:
            bool: True si se registró correctamente
        """
        try:
            if not self.validar_entero_positivo(idarticulo, "ID del artículo"):
                return False
            
            if cantidad <= 0:
                logger.warning(f"⚠️ Cantidad inválida: {cantidad}")
                return False
            
            # Validar tipo de movimiento
            if tipo_movimiento not in ['ENTRADA', 'SALIDA']:
                logger.warning(f"⚠️ Tipo de movimiento inválido: {tipo_movimiento}")
                return False
            
            # Crear repositorio si no existe
            from capa_datos.inventario_repo import InventarioRepositorio
            repo = InventarioRepositorio()
            
            # Registrar en el repositorio
            resultado = repo.registrar_movimiento(
                idarticulo=idarticulo,
                tipo_movimiento=tipo_movimiento,
                cantidad=cantidad,
                referencia=referencia,
                precio_compra=precio_compra,
                lote=lote,
                fecha_vencimiento=fecha_vencimiento
            )
            
            if resultado:
                logger.info(f"✅ Movimiento registrado: {tipo_movimiento} {cantidad} unidades - Artículo {idarticulo}")
                return True
            else:
                logger.error(f"❌ Error registrando movimiento en repositorio")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error en registrar_movimiento: {e}")
            return False
    
    def _insertar_stock_inicial(self, idarticulo):
        """
        Inserta un registro de stock inicial para un artículo
        Usa 'INGRESO' como tipo_movimiento para cumplir con la restricción CHECK
        """
        try:
            conn = self.articulo_service.repositorio.conn
            cursor = conn.cursor()
            
            # CORREGIDO: Usar 'INGRESO' en lugar de 'INICIAL' para cumplir con la restricción
            query = """
            INSERT INTO kardex 
            (idarticulo, tipo_movimiento, documento_referencia, cantidad, 
             precio_unitario, valor_total, stock_anterior, stock_nuevo, fecha_movimiento)
            VALUES (?, 'INGRESO', 'INVENTARIO INICIAL', 0, 0, 0, 0, 0, GETDATE())
            """
            cursor.execute(query, (idarticulo,))
            conn.commit()
            logger.info(f"📝 Stock inicial creado para artículo {idarticulo} (tipo: INGRESO)")
        except Exception as e:
            logger.error(f"Error al insertar stock inicial: {e}")
    
    def descontar_stock(self, idarticulo, cantidad, idventa=None, precio_unitario=None):
        """
        Descuenta stock de un artículo por una venta (ACTUALIZA KARDEX)
        
        Args:
            idarticulo (int): ID del artículo
            cantidad (int): Cantidad a descontar
            idventa (int, optional): ID de la venta asociada
            precio_unitario (float, optional): Precio de venta unitario
            
        Returns:
            bool: True si se descontó correctamente, False en caso contrario
        """
        try:
            # Validaciones
            if not self.validar_entero_positivo(idarticulo, "ID del artículo"):
                return False
            
            if not self.validar_entero_positivo(cantidad, "Cantidad a descontar"):
                return False
            
            # Obtener stock actual
            stock_actual = self.obtener_stock_articulo(idarticulo)
            
            if stock_actual < cantidad:
                logger.error(f"Stock insuficiente. Disponible: {stock_actual}, Solicitado: {cantidad}")
                return False
            
            # Calcular nuevo stock
            stock_nuevo = stock_actual - cantidad
            
            # Calcular valor total
            valor_total = cantidad * precio_unitario if precio_unitario else 0
            
            # Insertar en kardex
            conn = self.articulo_service.repositorio.conn
            cursor = conn.cursor()
            
            documento = f"VENTA-{idventa}" if idventa else "VENTA-DIRECTA"
            
            query = """
            INSERT INTO kardex 
            (idarticulo, tipo_movimiento, documento_referencia, cantidad, 
             precio_unitario, valor_total, stock_anterior, stock_nuevo, fecha_movimiento)
            VALUES (?, 'VENTA', ?, ?, ?, ?, ?, ?, GETDATE())
            """
            
            cursor.execute(query, (idarticulo, documento, cantidad, precio_unitario, valor_total, stock_actual, stock_nuevo))
            conn.commit()
            
            logger.info(f"✅ Descontando {cantidad} unidades del artículo {idarticulo}")
            logger.info(f"   Stock: {stock_actual} → {stock_nuevo}")
            if precio_unitario:
                logger.info(f"   Precio unitario: Bs. {precio_unitario:.2f}")
                logger.info(f"   Valor total: Bs. {valor_total:.2f}")
            if idventa:
                logger.info(f"   Venta asociada: #{idventa}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error al descontar stock del artículo {idarticulo}: {e}")
            return False
    
    def reponer_stock(self, idarticulo, cantidad, idingreso=None, precio_compra=None):
        """
        Repone stock de un artículo por un ingreso (ACTUALIZA KARDEX)
        
        Args:
            idarticulo (int): ID del artículo
            cantidad (int): Cantidad a reponer
            idingreso (int, optional): ID del ingreso asociado
            precio_compra (float, optional): Precio de compra unitario
            
        Returns:
            bool: True si se repuso correctamente, False en caso contrario
        """
        try:
            # Validaciones
            if not self.validar_entero_positivo(idarticulo, "ID del artículo"):
                return False
            
            if not self.validar_entero_positivo(cantidad, "Cantidad a reponer"):
                return False
            
            # Obtener stock actual
            stock_actual = self.obtener_stock_articulo(idarticulo)
            stock_nuevo = stock_actual + cantidad
            
            # Calcular valor total
            valor_total = cantidad * precio_compra if precio_compra else 0
            
            # Insertar en kardex
            conn = self.articulo_service.repositorio.conn
            cursor = conn.cursor()
            
            documento = f"INGRESO-{idingreso}" if idingreso else "INGRESO-MANUAL"
            
            query = """
            INSERT INTO kardex 
            (idarticulo, tipo_movimiento, documento_referencia, cantidad, 
             precio_unitario, valor_total, stock_anterior, stock_nuevo, fecha_movimiento)
            VALUES (?, 'INGRESO', ?, ?, ?, ?, ?, ?, GETDATE())
            """
            
            cursor.execute(query, (idarticulo, documento, cantidad, precio_compra, valor_total, stock_actual, stock_nuevo))
            conn.commit()
            
            logger.info(f"✅ Reponiendo {cantidad} unidades del artículo {idarticulo}")
            logger.info(f"   Stock: {stock_actual} → {stock_nuevo}")
            if precio_compra:
                logger.info(f"   Precio compra: Bs. {precio_compra:.2f}")
                logger.info(f"   Valor total: Bs. {valor_total:.2f}")
            if idingreso:
                logger.info(f"   Ingreso asociado: #{idingreso}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error al reponer stock del artículo {idarticulo}: {e}")
            return False
    
    def obtener_nivel_stock(self, stock_actual):
        """
        Determina el nivel de stock (CRÍTICO, BAJO, NORMAL)
        
        Args:
            stock_actual (int): Stock actual del artículo
            
        Returns:
            dict: Nivel de stock con color y mensaje
        """
        if stock_actual < 3:
            return {
                'nivel': 'CRÍTICO',
                'color': self.COLOR_ROJO,
                'emoji': '🔴',
                'mensaje': '¡URGENTE! Reponer stock inmediatamente'
            }
        elif stock_actual < 6:
            return {
                'nivel': 'BAJO',
                'color': self.COLOR_AMARILLO,
                'emoji': '🟡',
                'mensaje': 'Stock bajo, considerar reposición'
            }
        else:
            return {
                'nivel': 'NORMAL',
                'color': self.COLOR_VERDE,
                'emoji': '🟢',
                'mensaje': 'Stock normal'
            }
    
    def listar_con_stock(self):
        """
        Lista todos los artículos con su stock actual desde kardex
        """
        try:
            if not self.articulo_service:
                logger.error("❌ ArticuloService no disponible")
                return []
            
            # Obtener artículos usando el método correcto
            articulos = self.articulo_service.listar_articulos()
            
            if not articulos:
                logger.info("📭 No hay artículos registrados")
                return []
            
            # Enriquecer con stock actual (sin perder otros campos)
            for art in articulos:
                try:
                    stock = self.obtener_stock_articulo(art['idarticulo'])
                    art['stock_actual'] = stock
                    
                    # DEBUG - Verificar que letra_fiscal se mantiene
                    if 'letra_fiscal' in art:
                        logger.debug(f"Artículo {art['idarticulo']} tiene letra: {art['letra_fiscal']}")
                    
                except Exception as e:
                    logger.error(f"Error obteniendo stock para artículo {art['idarticulo']}: {e}")
                    art['stock_actual'] = 0
            
            logger.info(f"✅ {len(articulos)} artículos listados con stock")
            return articulos
            
        except Exception as e:
            logger.error(f"❌ Error al listar artículos con stock: {e}")
            return []
    
    def mostrar_tabla_stock(self):
        """
        Genera una tabla formateada del stock actual
        
        Returns:
            str: Tabla formateada para mostrar en consola
        """
        articulos = self.listar_con_stock()
        
        if not articulos:
            return "📭 No hay artículos registrados"
        
        lineas = []
        lineas.append(f"{'ID':<5} {'CÓDIGO':<15} {'NOMBRE':<30} {'STOCK':<10} {'ESTADO':<15}")
        lineas.append("-" * 75)
        
        for art in articulos:
            linea = f"{art['idarticulo']:<5} {art['codigo']:<15} {art['nombre']:<30} {art['stock_actual']:<10} {art['emoji']} {art['nivel_stock']}"
            lineas.append(f"{art['color']}{linea}{self.COLOR_RESET}")
        
        return "\n".join(lineas)
    
    def mostrar_resumen_stock(self):
        """
        Muestra un resumen del inventario
        
        Returns:
            str: Resumen formateado
        """
        articulos = self.listar_con_stock()
        
        if not articulos:
            return "📭 No hay artículos registrados"
        
        total_articulos = len(articulos)
        criticos = sum(1 for a in articulos if a['nivel_stock'] == 'CRÍTICO')
        bajos = sum(1 for a in articulos if a['nivel_stock'] == 'BAJO')
        normales = sum(1 for a in articulos if a['nivel_stock'] == 'NORMAL')
        stock_total = sum(a['stock_actual'] for a in articulos)
        
        resumen = []
        resumen.append("📊 RESUMEN DE INVENTARIO")
        resumen.append("=" * 40)
        resumen.append(f"Total artículos: {total_articulos}")
        resumen.append(f"Stock total: {stock_total} unidades")
        resumen.append("")
        resumen.append(f"{self.COLOR_ROJO}🔴 Críticos: {criticos}{self.COLOR_RESET}")
        resumen.append(f"{self.COLOR_AMARILLO}🟡 Bajos: {bajos}{self.COLOR_RESET}")
        resumen.append(f"{self.COLOR_VERDE}🟢 Normales: {normales}{self.COLOR_RESET}")
        
        if criticos > 0:
            resumen.append("")
            resumen.append(f"{self.COLOR_ROJO}⚠️ Artículos críticos:{self.COLOR_RESET}")
            for art in articulos:
                if art['nivel_stock'] == 'CRÍTICO':
                    resumen.append(f"   - {art['nombre']} (Stock: {art['stock_actual']})")
        
        return "\n".join(resumen)
    
    def obtener_alertas_stock(self):
        """
        Obtiene alertas de stock bajo y crítico
        
        Returns:
            list: Lista de alertas formateadas
        """
        articulos = self.listar_con_stock()
        alertas = []
        
        for art in articulos:
            if art['nivel_stock'] == 'CRÍTICO':
                alertas.append(f"{self.COLOR_ROJO}🔴 {art['nombre']} - Stock CRÍTICO ({art['stock_actual']} und){self.COLOR_RESET}")
            elif art['nivel_stock'] == 'BAJO':
                alertas.append(f"{self.COLOR_AMARILLO}🟡 {art['nombre']} - Stock BAJO ({art['stock_actual']} und){self.COLOR_RESET}")
        
        return alertas
    
    def verificar_stock_para_venta(self, items):
        """
        Verifica si hay stock suficiente para una venta
        
        Args:
            items (list): Lista de items con idarticulo y cantidad
            
        Returns:
            tuple: (bool, list) - (aprobado, lista de errores)
        """
        errores = []
        for item in items:
            stock = self.obtener_stock_articulo(item['idarticulo'])
            if item['cantidad'] > stock:
                errores.append(f"Artículo {item['idarticulo']}: requiere {item['cantidad']}, disponible {stock}")
        
        return len(errores) == 0, errores
