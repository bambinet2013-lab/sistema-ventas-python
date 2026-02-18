"""
Módulo de validación de documentos venezolanos
- RIF (Registro de Información Fiscal)
- Cédula de Identidad
"""
import re
from loguru import logger

class ValidacionVenezuela:
    """Clase para validar documentos venezolanos (RIF y Cédula)"""
    
    # Letras válidas para RIF según SENIAT
    LETRAS_RIF = {
        'V': 'Persona natural venezolana',
        'E': 'Persona natural extranjera',
        'J': 'Persona jurídica (empresa)',
        'G': 'Ente gubernamental',
        'P': 'Pasaporte (no residente)',
        'C': 'Consejo comunal / poder popular'
    }
    
    @classmethod
    def validar_cedula(cls, cedula: str) -> bool:
        """
        Valida una cédula de identidad venezolana
        Formato: 7-8 dígitos numéricos (puede incluir ceros a la izquierda)
        """
        if not cedula:
            logger.warning("⚠️ Cédula vacía")
            return False
        
        # Limpiar espacios
        cedula = cedula.strip()
        
        # Verificar que solo contenga números
        if not cedula.isdigit():
            logger.warning(f"⚠️ Cédula '{cedula}' contiene caracteres no numéricos")
            return False
        
        # La cédula venezolana tiene entre 7 y 8 dígitos
        # (algunas cédulas antiguas pueden tener menos, pero en sistema moderno usamos 7-8)
        if len(cedula) < 7 or len(cedula) > 8:
            logger.warning(f"⚠️ Cédula '{cedula}' debe tener 7 u 8 dígitos")
            return False
        
        return True
    
    @classmethod
    def validar_rif(cls, rif: str) -> bool:
        """
        Valida un RIF venezolano
        Formato: L-XXXXXXXX-X
        - Letra inicial: V, E, J, G, P, C
        - 8 dígitos numéricos
        - Dígito verificador (0-9)
        """
        if not rif:
            logger.warning("⚠️ RIF vacío")
            return False
        
        # Limpiar espacios y convertir a mayúsculas
        rif = rif.strip().upper()
        
        # Eliminar guiones para validar formato
        rif_sin_guiones = rif.replace('-', '')
        
        # Verificar longitud total (10 caracteres: letra + 8 dígitos + 1 dígito verificador)
        if len(rif_sin_guiones) != 10:
            logger.warning(f"⚠️ RIF '{rif}' debe tener 10 caracteres (letra + 8 dígitos + 1 dígito)")
            return False
        
        # Verificar que la letra inicial sea válida
        letra = rif_sin_guiones[0]
        if letra not in cls.LETRAS_RIF:
            logger.warning(f"⚠️ Letra '{letra}' no válida. Debe ser: {', '.join(cls.LETRAS_RIF.keys())}")
            return False
        
        # Verificar que los siguientes 8 caracteres sean dígitos
        if not rif_sin_guiones[1:9].isdigit():
            logger.warning(f"⚠️ RIF '{rif}' debe tener 8 dígitos después de la letra")
            return False
        
        # Verificar que el último carácter sea dígito (verificador)
        if not rif_sin_guiones[9].isdigit():
            logger.warning(f"⚠️ El dígito verificador debe ser un número")
            return False
        
        # Validar el dígito verificador usando el algoritmo oficial del SENIAT
        if not cls._validar_digito_verificador(rif_sin_guiones):
            logger.warning(f"⚠️ Dígito verificador incorrecto para RIF '{rif}'")
            return False
        
        return True
    
    @classmethod
    def _validar_digito_verificador(cls, rif_sin_guiones: str) -> bool:
        """
        Algoritmo oficial del SENIAT para validar el dígito verificador del RIF
        """
        letra = rif_sin_guiones[0]
        numeros = rif_sin_guiones[1:9]
        digito_ingresado = int(rif_sin_guiones[9])
        
        # Tabla de valores para cada letra
        tabla_letras = {
            'V': 4, 'E': 8, 'J': 12, 'P': 16, 'G': 20, 'C': 24
        }
        
        if letra not in tabla_letras:
            return False
        
        # Calcular suma ponderada
        suma = tabla_letras[letra]
        factores = [3, 2, 7, 6, 5, 4, 3, 2]
        
        for i, digito in enumerate(numeros):
            suma += int(digito) * factores[i]
        
        # Calcular dígito verificador
        resto = suma % 11
        digito_calculado = 11 - resto if resto > 1 else 0
        
        return digito_calculado == digito_ingresado
    
    @classmethod
    def formatear_rif(cls, rif: str) -> str:
        """
        Formatea un RIF al formato estándar L-XXXXXXXX-X
        """
        rif = rif.strip().upper().replace('-', '')
        if len(rif) == 10:
            return f"{rif[0]}-{rif[1:9]}-{rif[9]}"
        return rif
    
    @classmethod
    def obtener_tipo_contribuyente(cls, rif: str) -> str:
        """
        Devuelve el tipo de contribuyente según la letra del RIF
        """
        if not rif:
            return "Desconocido"
        
        letra = rif.strip().upper()[0]
        return cls.LETRAS_RIF.get(letra, "Tipo no válido")
