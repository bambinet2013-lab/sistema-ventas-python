"""
Servicio para generación de reportes contables
"""
from datetime import datetime, timedelta
from loguru import logger
import csv
import os

class ReporteContableService:
    """Genera reportes contables para ventas y movimientos"""
    
    def __init__(self, venta_service, inventario_service):
        self.venta_service = venta_service
        self.inventario_service = inventario_service
        logger.info("✅ ReporteContableService inicializado")
    
    def obtener_ventas_por_periodo(self, fecha_inicio, fecha_fin):
        """
        Obtiene todas las ventas en un período
        """
        ventas = self.venta_service.ventas_por_fecha(fecha_inicio, fecha_fin)
        
        print("\n" + "="*60)
        print("🔍 DEPURACIÓN DE VENTAS")
        print("="*60)
        print(f"Total ventas encontradas: {len(ventas)}")
        
        # Calcular totales por moneda
        total_bs = 0.0
        total_usd = 0.0
        total_eur = 0.0
        igtf_total = 0.0
        
        for idx, v in enumerate(ventas):
            print(f"\n--- VENTA #{idx+1} (ID: {v.get('idventa')}) ---")
            
            # Mostrar todos los campos de la venta
            for key, value in v.items():
                print(f"   {key}: {value} (tipo: {type(value)})")
            
            # Determinar moneda
            moneda = v.get('moneda', 'NO ESPECIFICADA')
            print(f"   → Moneda detectada: {moneda}")
            
            # Obtener montos
            monto_bs = v.get('monto_bs')
            monto_divisa = v.get('monto_divisa')
            
            print(f"   → monto_bs: {monto_bs}")
            print(f"   → monto_divisa: {monto_divisa}")
            
            # Sumar según moneda
            if moneda == 'VES' and monto_bs is not None:
                total_bs += float(monto_bs)
                print(f"   ✓ Sumando a Bs.: +{float(monto_bs)}")
            elif moneda == 'USD' and monto_divisa is not None:
                total_usd += float(monto_divisa)
                print(f"   ✓ Sumando a USD: +{float(monto_divisa)}")
            elif moneda == 'EUR' and monto_divisa is not None:
                total_eur += float(monto_divisa)
                print(f"   ✓ Sumando a EUR: +{float(monto_divisa)}")
            else:
                print(f"   ✗ No se pudo sumar - moneda: {moneda}, monto_bs: {monto_bs}, monto_divisa: {monto_divisa}")
        
        print("\n" + "="*60)
        print("📊 TOTALES CALCULADOS:")
        print(f"   Bs.: {total_bs}")
        print(f"   USD: {total_usd}")
        print(f"   EUR: {total_eur}")
        print(f"   IGTF: {igtf_total}")
        print("="*60)
        
        return {
            'fecha_inicio': str(fecha_inicio),
            'fecha_fin': str(fecha_fin),
            'total_ventas': len(ventas),
            'total_bs': total_bs,
            'total_usd': total_usd,
            'total_eur': total_eur,
            'igtf_total': igtf_total,
            'ventas': ventas,
            'detalle': self._agrupar_por_dia(ventas)
        }
    
    def _agrupar_por_dia(self, ventas):
        """Agrupa ventas por día para reportes detallados"""
        dias = {}
        for v in ventas:
            # Obtener fecha
            if hasattr(v['fecha'], 'strftime'):
                fecha = v['fecha'].strftime('%Y-%m-%d')
            else:
                fecha = str(v['fecha'])[:10]
            
            if fecha not in dias:
                dias[fecha] = {
                    'ventas': 0,
                    'bs': 0.0,
                    'usd': 0.0,
                    'eur': 0.0
                }
            
            dias[fecha]['ventas'] += 1
            
            # Sumar según moneda
            moneda = v.get('moneda', 'VES')
            monto_bs = v.get('monto_bs')
            monto_divisa = v.get('monto_divisa')
            
            if moneda == 'VES' and monto_bs is not None:
                dias[fecha]['bs'] += float(monto_bs)
            elif moneda == 'USD' and monto_divisa is not None:
                dias[fecha]['usd'] += float(monto_divisa)
            elif moneda == 'EUR' and monto_divisa is not None:
                dias[fecha]['eur'] += float(monto_divisa)
        
        return dias
    
    def reporte_diario(self, fecha=None):
        """Reporte de ventas del día"""
        if fecha is None:
            fecha = datetime.now().date()
        return self.obtener_ventas_por_periodo(fecha, fecha)
    
    def reporte_semanal(self, fecha=None):
        """Reporte de la última semana"""
        if fecha is None:
            fecha = datetime.now().date()
        fecha_inicio = fecha - timedelta(days=7)
        return self.obtener_ventas_por_periodo(fecha_inicio, fecha)
    
    def reporte_mensual(self, fecha=None):
        """Reporte del último mes"""
        if fecha is None:
            fecha = datetime.now().date()
        fecha_inicio = fecha - timedelta(days=30)
        return self.obtener_ventas_por_periodo(fecha_inicio, fecha)
    
    def reporte_trimestral(self, fecha=None):
        """Reporte del último trimestre"""
        if fecha is None:
            fecha = datetime.now().date()
        fecha_inicio = fecha - timedelta(days=90)
        return self.obtener_ventas_por_periodo(fecha_inicio, fecha)
    
    def reporte_anual(self, fecha=None):
        """Reporte del último año"""
        if fecha is None:
            fecha = datetime.now().date()
        fecha_inicio = fecha - timedelta(days=365)
        return self.obtener_ventas_por_periodo(fecha_inicio, fecha)
    
    def exportar_a_csv(self, datos_reporte, nombre_archivo=None):
        """
        Exporta reporte a CSV para usar en Excel/contabilidad
        """
        if nombre_archivo is None:
            fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_archivo = f"reporte_ventas_{fecha}.csv"
        
        # Asegurar directorio de reportes
        os.makedirs("reportes", exist_ok=True)
        ruta_completa = os.path.join("reportes", nombre_archivo)
        
        with open(ruta_completa, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Encabezados contables
            writer.writerow(['REPORTE CONTABLE DE VENTAS'])
            writer.writerow([f'Período: {datos_reporte["fecha_inicio"]} al {datos_reporte["fecha_fin"]}'])
            writer.writerow([])
            
            # Totales
            writer.writerow(['RESUMEN GENERAL'])
            writer.writerow(['Total Ventas', datos_reporte['total_ventas']])
            writer.writerow(['Total Bs.', f"{datos_reporte['total_bs']:.2f}"])
            writer.writerow(['Total USD', f"{datos_reporte['total_usd']:.2f}"])
            writer.writerow(['Total EUR', f"{datos_reporte['total_eur']:.2f}"])
            writer.writerow(['IGTF Total', f"{datos_reporte['igtf_total']:.2f}"])
            writer.writerow([])
            
            # Detalle por día
            writer.writerow(['DETALLE POR DÍA'])
            writer.writerow(['Fecha', 'Ventas', 'Bs.', 'USD', 'EUR'])
            
            for fecha, datos in sorted(datos_reporte['detalle'].items()):
                writer.writerow([
                    fecha,
                    datos['ventas'],
                    f"{datos['bs']:.2f}",
                    f"{datos['usd']:.2f}",
                    f"{datos['eur']:.2f}"
                ])
        
        logger.info(f"✅ Reporte exportado: {ruta_completa}")
        return ruta_completa
