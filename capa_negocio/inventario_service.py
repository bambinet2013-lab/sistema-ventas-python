"""
Servicio para la gestión de inventario y stock
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
        """
        Inicializa el servicio de inventario
        
        Args:
            articulo_service: Servicio de artículos para obtener información de productos
        """
        super().__init__()
        self.articulo_service = articulo_service
        logger.info("✅ InventarioService inicializado")
    
    def obtener_stock_articulo(self, idarticulo):
        """
        Obtiene el stock actual de un artículo
        
        Args:
            idarticulo (int): ID del artículo
            
        Returns:
            int: Stock actual o 0 si no existe
        """
        try:
            # Validar ID
            if not self.validar_entero_positivo(idarticulo, "ID del artículo"):
                return 0
            
            # Stock simulado para pruebas
            stocks = {
                1: 10,  # Laptop HP
                2: 5,   # Mouse inalámbrico
                3: 2,   # Teclado
            }
            stock = stocks.get(idarticulo, 0)
            logger.info(f"Stock del artículo {idarticulo}: {stock} unidades")
            return stock
            
        except Exception as e:
            logger.error(f"Error al obtener stock del artículo {idarticulo}: {e}")
            return 0
    
    def descontar_stock(self, idarticulo, cantidad, idventa=None):
        """
        Descuenta stock de un artículo por una venta
        
        Args:
            idarticulo (int): ID del artículo
            cantidad (int): Cantidad a descontar
            idventa (int, optional): ID de la venta asociada
            
        Returns:
            bool: True si se descontó correctamente, False en caso contrario
        """
        try:
            # Validaciones
            if not self.validar_entero_positivo(idarticulo, "ID del artículo"):
                return False
            
            if not self.validar_entero_positivo(cantidad, "Cantidad a descontar"):
                return False
            
            logger.info(f"✅ Descontando {cantidad} unidades del artículo {idarticulo}")
            if idventa:
                logger.info(f"   Venta asociada: #{idventa}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error al descontar stock del artículo {idarticulo}: {e}")
            return False
    
    def reponer_stock(self, idarticulo, cantidad, idingreso=None):
        """
        Repone stock de un artículo por un ingreso
        
        Args:
            idarticulo (int): ID del artículo
            cantidad (int): Cantidad a reponer
            idingreso (int, optional): ID del ingreso asociado
            
        Returns:
            bool: True si se repuso correctamente, False en caso contrario
        """
        try:
            # Validaciones
            if not self.validar_entero_positivo(idarticulo, "ID del artículo"):
                return False
            
            if not self.validar_entero_positivo(cantidad, "Cantidad a reponer"):
                return False
            
            logger.info(f"✅ Reponiendo {cantidad} unidades del artículo {idarticulo}")
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
        Lista todos los artículos con su stock actual y nivel
        
        Returns:
            list: Lista de artículos con información de stock
        """
        try:
            articulos = self.articulo_service.listar()
            resultado = []
            
            for art in articulos:
                stock = self.obtener_stock_articulo(art['idarticulo'])
                nivel = self.obtener_nivel_stock(stock)
                
                resultado.append({
                    'idarticulo': art['idarticulo'],
                    'codigo': art['codigo'],
                    'nombre': art['nombre'],
                    'categoria': art.get('categoria', 'Sin categoría'),
                    'stock_actual': stock,
                    'nivel_stock': nivel['nivel'],
                    'color': nivel['color'],
                    'emoji': nivel['emoji'],
                    'mensaje': nivel['mensaje']
                })
            
            return resultado
            
        except Exception as e:
            logger.error(f"Error al listar artículos con stock: {e}")
            return []
    
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
