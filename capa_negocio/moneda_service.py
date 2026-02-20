"""
Servicio para gestión de multimoneda y tasas de cambio
"""
from datetime import datetime
from loguru import logger
import requests

class MonedaService:
    """Servicio para manejar operaciones con múltiples monedas"""
    
    MONEDAS = {
        'VES': {'nombre': 'Bolívar', 'simbolo': 'Bs.', 'decimales': 2},
        'USD': {'nombre': 'Dólar', 'simbolo': '$', 'decimales': 2},
        'EUR': {'nombre': 'Euro', 'simbolo': '€', 'decimales': 2}
    }
    
    def __init__(self, conn):
        self.conn = conn
        logger.info("✅ MonedaService inicializado")
    
    def obtener_tasa_actual(self):
        """
        Obtiene la tasa de cambio actual (USD/VES)
        Prioridad: 1. BCV, 2. Última registrada, 3. Manual
        """
        try:
            # Intentar obtener tasa del BCV
            tasa_bcv = self._obtener_tasa_bcv()
            if tasa_bcv:
                self._guardar_tasa(tasa_bcv, 'BCV')
                return tasa_bcv
            
            # Si no, obtener última tasa registrada
            cursor = self.conn.cursor()
            query = """
            SELECT TOP 1 tasa 
            FROM tasa_cambio 
            WHERE activa = 1 
            ORDER BY fecha DESC
            """
            cursor.execute(query)
            row = cursor.fetchone()
            
            if row:
                return row[0]
            
            return 1.0  # Tasa por defecto
            
        except Exception as e:
            logger.error(f"Error obteniendo tasa: {e}")
            return 1.0
    
    def _obtener_tasa_bcv(self):
        """
        Consulta la tasa del BCV (simulado por ahora)
        En producción, conectar con API real del BCV
        """
        try:
            # Simulación - en producción conectar con API real
            # response = requests.get('https://api.bcv.org.ve/tasas', timeout=5)
            # return response.json()['usd']
            
            # Por ahora, retornar tasa simulada
            return 60.0  # Simular 60 Bs/USD
        except:
            return None
    
    def _guardar_tasa(self, tasa, fuente='MANUAL'):
        """Guarda una tasa en la base de datos"""
        try:
            cursor = self.conn.cursor()
            
            # Desactivar tasas anteriores
            cursor.execute("UPDATE tasa_cambio SET activa = 0 WHERE activa = 1")
            
            # Insertar nueva tasa
            query = """
            INSERT INTO tasa_cambio (fecha, tasa, fuente, activa)
            VALUES (GETDATE(), ?, ?, 1)
            """
            cursor.execute(query, (tasa, fuente))
            self.conn.commit()
            
            logger.info(f"✅ Tasa guardada: 1 USD = {tasa} VES ({fuente})")
            
        except Exception as e:
            logger.error(f"Error guardando tasa: {e}")
    
    def actualizar_tasa_manual(self, tasa):
        """Actualiza la tasa manualmente"""
        return self._guardar_tasa(tasa, 'MANUAL')
    
    def convertir(self, monto, moneda_origen, moneda_destino, tasa=None):
        """
        Convierte entre monedas
        
        Args:
            monto: Cantidad a convertir
            moneda_origen: VES, USD, EUR
            moneda_destino: VES, USD, EUR
            tasa: Tasa de cambio (si es None, usa la actual)
        
        Returns:
            float: Monto convertido
        """
        if moneda_origen == moneda_destino:
            return monto
        
        if tasa is None:
            tasa = self.obtener_tasa_actual()
        
        if moneda_origen == 'USD' and moneda_destino == 'VES':
            return monto * tasa
        elif moneda_origen == 'VES' and moneda_destino == 'USD':
            return monto / tasa
        else:
            logger.error(f"Conversión no soportada: {moneda_origen} → {moneda_destino}")
            return monto
    
    def formatear_monto(self, monto, moneda='VES'):
        """Formatea un monto según la moneda"""
        info = self.MONEDAS.get(moneda, self.MONEDAS['VES'])
        formato = f"{info['simbolo']} {monto:,.{info['decimales']}f}"
        return formato.replace(',', ' ').replace('.', ',')

class IGTFService:
    """Servicio para calcular el IGTF (Impuesto a Grandes Transacciones Financieras)"""
    
    TASA_IGTF = 0.03  # 3% para pagos en divisas
    
    @staticmethod
    def calcular_igtf(monto, moneda_pago, moneda_transaccion='VES'):
        """
        Calcula el IGTF según la moneda de pago
        
        Args:
            monto: Monto de la transacción
            moneda_pago: Moneda en que se paga (USD, VES, etc)
            moneda_transaccion: Moneda de la factura
            
        Returns:
            float: Monto del IGTF
        """
        if moneda_pago in ['USD', 'EUR']:
            return monto * IGTFService.TASA_IGTF
        return 0.0
