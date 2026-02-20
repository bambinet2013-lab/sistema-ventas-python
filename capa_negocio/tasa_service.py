"""
Servicio para gestión de tasas de cambio - VERSIÓN MANUAL (ESCALABLE)
"""
from datetime import datetime, date
from loguru import logger
from capa_negocio.base_service import BaseService

class TasaService(BaseService):
    """Servicio para manejar tasas de cambio (dólar, euro)"""
    
    MONEDAS_SOPORTADAS = ['USD', 'EUR']
    
    # Colores para la consola
    COLOR_AMARILLO = '\033[93m'
    COLOR_VERDE = '\033[92m'
    COLOR_ROJO = '\033[91m'
    COLOR_RESET = '\033[0m'
    
    def __init__(self, repositorio_tasa):
        """
        Inicializa el servicio de tasas
        
        Args:
            repositorio_tasa: Repositorio para acceso a BD
        """
        super().__init__()
        self.repo = repositorio_tasa
        self.modo_automatico = False  # Por ahora manual
        logger.info("✅ TasaService inicializado en modo MANUAL")
    
    def obtener_tasa_del_dia(self, moneda='USD'):
        """
        Obtiene la última tasa registrada para una moneda
        
        Args:
            moneda: USD, EUR
            
        Returns:
            float: Tasa de cambio o None si no existe
        """
        try:
            tasa = self.repo.obtener_ultima_tasa(moneda)
            if tasa:
                logger.info(f"💱 Tasa {moneda}: {tasa:.2f} (de BD)")
                return tasa
            else:
                logger.warning(f"No hay tasa registrada para {moneda}")
                return None
        except Exception as e:
            logger.error(f"Error obteniendo tasa: {e}")
            return None
    
    def registrar_tasa_manual(self, moneda, tasa, usuario):
        """
        Registra una tasa ingresada manualmente por el usuario
        
        Args:
            moneda: USD, EUR
            tasa: Valor de la tasa
            usuario: Nombre del usuario que registra
            
        Returns:
            bool: True si se registró correctamente
        """
        try:
            if not self.validar_decimal_positivo(tasa, "Tasa"):
                return False
            
            if moneda not in self.MONEDAS_SOPORTADAS:
                logger.error(f"Moneda no soportada: {moneda}")
                return False
            
            # Fuente manual tiene ID 1
            idfuente = 1
            
            resultado = self.repo.insertar_tasa(
                idfuente=idfuente,
                moneda_origen=moneda,
                tasa=tasa,
                usuario=usuario,
                observaciones="Ingreso manual"
            )
            
            if resultado:
                logger.info(f"✅ Tasa {moneda} registrada: {tasa:.2f} por {usuario}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error registrando tasa manual: {e}")
            return False
    
    def obtener_tasa_para_venta(self, moneda='USD', usuario=None):
        """
        Obtiene la tasa actual, solicitando al usuario si es necesario
        
        Args:
            moneda: USD, EUR
            usuario: Usuario actual (para registro)
            
        Returns:
            float: Tasa a usar o None si se cancela
        """
        # Modo MANUAL: preguntar siempre
        print(f"\n{self.COLOR_AMARILLO}💱 CONFIGURACIÓN DE TASA DE CAMBIO{self.COLOR_RESET}")
        print("=" * 50)
        
        # Intentar obtener última tasa como referencia
        tasa_anterior = self.obtener_tasa_del_dia(moneda)
        if tasa_anterior:
            print(f"📊 Última tasa registrada: 1 {moneda} = {tasa_anterior:.2f} VES")
            print(f"   Fecha: {date.today().strftime('%d/%m/%Y')}")
        else:
            print(f"📊 No hay tasa previa registrada para {moneda}")
        
        print("\nIngrese la tasa de cambio del día de HOY:")
        
        while True:
            try:
                tasa_input = input(f"💵 1 {moneda} = Bs. ").strip()
                if not tasa_input:
                    print(f"{self.COLOR_ROJO}❌ Operación cancelada{self.COLOR_RESET}")
                    return None
                
                tasa = float(tasa_input.replace(',', '.'))
                if tasa <= 0:
                    print(f"{self.COLOR_ROJO}❌ La tasa debe ser positiva{self.COLOR_RESET}")
                    continue
                
                # Confirmar
                print(f"\n✅ Tasa ingresada: 1 {moneda} = {tasa:.2f} VES")
                confirmar = input(f"{self.COLOR_AMARILLO}¿Confirmar? (s/N): {self.COLOR_RESET}").lower()
                
                if confirmar == 's':
                    # Registrar en BD
                    if usuario:
                        self.registrar_tasa_manual(moneda, tasa, usuario)
                    return tasa
                else:
                    print("Por favor, ingrese la tasa correcta:")
                    
            except ValueError:
                print(f"{self.COLOR_ROJO}❌ Ingrese un número válido (ej: 60.50){self.COLOR_RESET}")
    
    def mostrar_historial(self, moneda='USD', dias=7):
        """
        Muestra el historial reciente de tasas
        
        Args:
            moneda: USD, EUR
            dias: Número de días a mostrar
        """
        historial = self.repo.obtener_historial(moneda, dias)
        
        if not historial:
            print(f"📭 No hay historial para {moneda}")
            return
        
        print(f"\n📊 HISTORIAL DE TASAS {moneda} (últimos {dias} días)")
        print("-" * 60)
        print(f"{'FECHA':<12} {'TASA':<10} {'FUENTE':<15} {'USUARIO':<15}")
        print("-" * 60)
        
        for h in historial:
            fecha = h['fecha'].strftime('%d/%m/%Y') if hasattr(h['fecha'], 'strftime') else h['fecha']
            print(f"{fecha:<12} {h['tasa']:<10.2f} {h['fuente']:<15} {h['usuario_registro'] or '':<15}")
    
    # ========== MÉTODOS PARA FUTURAS MEJORAS AUTOMÁTICAS ==========
    
    def activar_modo_automatico(self):
        """Activa el modo automático (para futuro)"""
        self.modo_automatico = True
        logger.info("🤖 Modo automático activado")
    
    def consultar_api_bcv(self):
        """
        MÉTODO PARA FUTURO: Consulta API del BCV
        """
        # Aquí irá la lógica para consultar APIs
        pass
