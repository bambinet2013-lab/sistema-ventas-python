from typing import List, Dict, Optional
from loguru import logger
from datetime import datetime

class InventarioService:
    """Servicio para gestión de inventario con alertas de stock"""
    
    # Colores ANSI para terminal
    COLOR_ROJO = '\033[91m'
    COLOR_VERDE = '\033[92m'
    COLOR_AMARILLO = '\033[93m'
    COLOR_RESET = '\033[0m'
    
    # Umbrales de stock
    STOCK_CRITICO = 2
    STOCK_BAJO = 5
    STOCK_NORMAL = 10
    
    def __init__(self, articulo_service, lote_service=None):
        self.articulo_service = articulo_service
        self.lote_service = lote_service
    
    def obtener_stock_articulo(self, idarticulo: int) -> int:
        """Obtiene el stock total de un artículo consultando directamente la BD"""
        try:
            from capa_datos.conexion import ConexionDB
            db = ConexionDB()
            conn = db.conectar()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT ISNULL(SUM(stock_actual), 0) FROM lote WHERE idarticulo = ?", (idarticulo,))
                stock = cursor.fetchone()[0]
                conn.close()
                return stock
            return 0
        except Exception as e:
            logger.error(f"❌ Error al obtener stock del artículo {idarticulo}: {e}")
            return 0
    
    def obtener_nivel_stock(self, cantidad: int) -> Dict:
        """
        Determina el nivel de stock y devuelve color y mensaje
        """
        if cantidad <= self.STOCK_CRITICO:
            return {
                'nivel': 'CRÍTICO',
                'color': self.COLOR_ROJO,
                'emoji': '🔴',
                'mensaje': f'¡URGENTE! Stock crítico: {cantidad} unidades'
            }
        elif cantidad <= self.STOCK_BAJO:
            return {
                'nivel': 'BAJO',
                'color': self.COLOR_AMARILLO,
                'emoji': '🟡',
                'mensaje': f'Stock bajo: {cantidad} unidades'
            }
        else:
            return {
                'nivel': 'NORMAL',
                'color': self.COLOR_VERDE,
                'emoji': '🟢',
                'mensaje': f'Stock normal: {cantidad} unidades'
            }
    
    def listar_con_stock(self) -> List[Dict]:
        """
        Lista todos los artículos con su nivel de stock y color
        Consulta el stock directamente desde la base de datos
        """
        try:
            # Obtener artículos del servicio
            articulos = self.articulo_service.listar()
            if not articulos:
                logger.info("📭 No hay artículos registrados")
                return []
            
            resultados = []
            
            # Obtener stock para cada artículo
            for art in articulos:
                stock = self.obtener_stock_articulo(art['idarticulo'])
                nivel = self.obtener_nivel_stock(stock)
                
                art_con_stock = art.copy()
                art_con_stock['stock_actual'] = stock
                art_con_stock['nivel_stock'] = nivel['nivel']
                art_con_stock['color'] = nivel['color']
                art_con_stock['emoji'] = nivel['emoji']
                
                resultados.append(art_con_stock)
            
            logger.info(f"✅ {len(resultados)} artículos listados con stock")
            return resultados
            
        except Exception as e:
            logger.error(f"❌ Error al listar con stock: {e}")
            return []
    
    def obtener_alertas_stock(self) -> List[str]:
        """
        Genera lista de alertas para artículos con stock bajo o crítico
        """
        alertas = []
        articulos = self.articulo_service.listar()
        
        for art in articulos:
            stock = self.obtener_stock_articulo(art['idarticulo'])
            if stock <= self.STOCK_BAJO:
                nivel = self.obtener_nivel_stock(stock)
                alerta = f"{nivel['color']}{nivel['emoji']} {art['nombre']}: {stock} unidades {nivel['mensaje']}{self.COLOR_RESET}"
                alertas.append(alerta)
        
        return alertas
    
    def mostrar_tabla_stock(self) -> str:
        """
        Genera una tabla formateada con colores para mostrar en consola
        """
        articulos = self.listar_con_stock()
        
        if not articulos:
            return "📭 No hay artículos registrados"
        
        # Cabecera
        tabla = "\n" + "="*90 + "\n"
        tabla += f"{'ID':<5} {'CÓDIGO':<15} {'NOMBRE':<30} {'STOCK':<10} {'ESTADO':<15}\n"
        tabla += "="*90 + "\n"
        
        # Filas con colores
        for art in articulos:
            stock_str = f"{art['stock_actual']} und"
            estado = f"{art['emoji']} {art['nivel_stock']}"
            
            # Aplicar color según nivel
            linea = f"{art['idarticulo']:<5} {art['codigo']:<15} {art['nombre']:<30} {stock_str:<10} {estado:<15}"
            tabla += f"{art['color']}{linea}{self.COLOR_RESET}\n"
        
        tabla += "="*90 + "\n"
        return tabla
    
    def mostrar_resumen_stock(self) -> str:
        """
        Muestra un resumen del estado del inventario
        """
        articulos = self.listar_con_stock()
        
        total = len(articulos)
        criticos = sum(1 for a in articulos if a['nivel_stock'] == 'CRÍTICO')
        bajos = sum(1 for a in articulos if a['nivel_stock'] == 'BAJO')
        normales = sum(1 for a in articulos if a['nivel_stock'] == 'NORMAL')
        
        resumen = "\n" + "="*60 + "\n"
        resumen += "📊 RESUMEN DE INVENTARIO\n"
        resumen += "="*60 + "\n"
        resumen += f"📦 Total artículos: {total}\n"
        resumen += f"{self.COLOR_VERDE}🟢 Stock normal: {normales}{self.COLOR_RESET}\n"
        resumen += f"{self.COLOR_AMARILLO}🟡 Stock bajo: {bajos}{self.COLOR_RESET}\n"
        resumen += f"{self.COLOR_ROJO}🔴 Stock crítico: {criticos}{self.COLOR_RESET}\n"
        resumen += "="*60 + "\n"
        
        return resumen
    
    def diagnosticar_stock(self) -> bool:
        """
        Método de diagnóstico para verificar el stock directamente desde la BD
        """
        import pyodbc
        try:
            conn_str = "DRIVER={ODBC Driver 18 for SQL Server};SERVER=localhost,1433;DATABASE=SistemaVentas;UID=sa;PWD=Santi07.;TrustServerCertificate=yes"
            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT a.idarticulo, a.codigo, a.nombre, ISNULL(SUM(l.stock_actual), 0) as stock
                FROM articulo a
                LEFT JOIN lote l ON a.idarticulo = l.idarticulo
                GROUP BY a.idarticulo, a.codigo, a.nombre
                ORDER BY a.idarticulo
            """)
            
            print("\n🔍 DIAGNÓSTICO DE STOCK (conexión directa):")
            for row in cursor.fetchall():
                print(f"  {row[0]} - {row[1]} - {row[2]}: {row[3]} unidades")
            
            conn.close()
            return True
        except Exception as e:
            print(f"❌ Error en diagnóstico: {e}")
            return False
