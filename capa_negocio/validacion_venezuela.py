from datetime import datetime
import re

class ValidacionVenezuela:
    """Clase con métodos de validación para documentos venezolanos"""
    
    @staticmethod
    def validar_cedula(cedula):
        """
        Valida una cédula venezolana (formato: V12345678 o E12345678)
        Retorna: (bool, mensaje_error)
        """
        if not cedula:
            return False, "La cédula no puede estar vacía"
        
        # Patrón para cédula venezolana: V/E + 8 dígitos
        patron = r'^[VE]\d{8}$'
        if not re.match(patron, cedula):
            return False, "Formato inválido. Debe ser V/E seguido de 8 dígitos (ej: V12345678)"
        
        return True, ""
    
    @staticmethod
    def validar_rif(rif):
        """
        Valida un RIF venezolano (formato: J123456789, G123456789, etc)
        Retorna: (bool, mensaje_error)
        """
        if not rif:
            return False, "El RIF no puede estar vacío"
        
        # Patrón para RIF: letra + 9 dígitos
        patron = r'^[JPGVE]\d{9}$'
        if not re.match(patron, rif):
            return False, "Formato inválido. Debe ser letra (J,P,G,V,E) seguida de 9 dígitos"
        
        return True, ""
    
    @staticmethod
    def validar_fecha(fecha_str):
        """
        Valida una fecha en formato DD/MM/YYYY
        Retorna: (bool, datetime or None, mensaje_error)
        """
        if not fecha_str or fecha_str.strip() == "":
            return True, None, ""  # Fecha vacía es válida (opcional)
        
        # Limpiar la fecha (quitar espacios)
        fecha_str = fecha_str.strip()
        
        # Patrón para DD/MM/YYYY
        patron = r'^(\d{1,2})/(\d{1,2})/(\d{4})$'
        match = re.match(patron, fecha_str)
        
        if not match:
            return False, None, "❌ Formato incorrecto. Use DD/MM/YYYY (ej: 15/05/1990)"
        
        dia, mes, año = map(int, match.groups())
        
        # Validar rangos básicos
        if mes < 1 or mes > 12:
            return False, None, "❌ Mes inválido (debe ser entre 01 y 12)"
        
        # Días por mes
        dias_por_mes = {
            1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30,
            7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31
        }
        
        if dia < 1 or dia > dias_por_mes[mes]:
            return False, None, f"❌ Día inválido para el mes {mes:02d} (máximo {dias_por_mes[mes]} días)"
        
        # Validación especial para febrero en años bisiestos
        if mes == 2 and dia == 29:
            if not ValidacionVenezuela._es_bisiesto(año):
                return False, None, f"❌ El año {año} no es bisiesto, febrero solo tiene 28 días"
        
        # Validar que no sea fecha futura
        try:
            fecha_obj = datetime(año, mes, dia)
            hoy = datetime.now()
            
            if fecha_obj > hoy:
                return False, None, "❌ La fecha no puede ser futura"
            
        except ValueError:
            return False, None, "❌ Fecha inválida (ej: 31/11/2023 no existe)"
        
        return True, fecha_obj, ""
    
    @staticmethod
    def _es_bisiesto(año):
        """Determina si un año es bisiesto"""
        return (año % 4 == 0 and año % 100 != 0) or (año % 400 == 0)
    
    @staticmethod
    def formatear_fecha_para_bd(fecha_obj):
        """Convierte un objeto datetime a string YYYY-MM-DD para BD"""
        if fecha_obj:
            return fecha_obj.strftime('%Y-%m-%d')
        return None
    
    @staticmethod
    def validar_telefono(telefono):
        """
        Valida un teléfono venezolano
        Acepta: 04141234567, 0414-1234567, +584141234567, etc
        """
        if not telefono:
            return True  # Teléfono opcional
        
        # Limpiar el teléfono (quitar +, -, espacios)
        telefono_limpio = re.sub(r'[\+\-\s]', '', telefono)
        
        # Verificar que sea solo números y tenga entre 10 y 12 dígitos
        if not telefono_limpio.isdigit():
            return False
        
        if len(telefono_limpio) < 10 or len(telefono_limpio) > 12:
            return False
        
        return True
    
    @staticmethod
    def validar_email(email):
        """
        Valida un email
        """
        if not email:
            return True  # Email opcional
        
        patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(patron, email) is not None
