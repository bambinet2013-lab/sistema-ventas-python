from typing import Optional, List, Dict, Any
from datetime import datetime
import re
from loguru import logger

class BaseService:
    """Clase base para servicios con validaciones comunes"""
    
    @staticmethod
    def validar_requerido(valor: Any, nombre_campo: str) -> bool:
        """Valida que un campo requerido no esté vacío"""
        if valor is None or (isinstance(valor, str) and not valor.strip()):
            logger.warning(f"⚠️ El campo {nombre_campo} es requerido")
            return False
        return True
    
    @staticmethod
    def validar_longitud(texto: str, nombre_campo: str, min_len: int = None, max_len: int = None) -> bool:
        """Valida la longitud de un texto"""
        if texto is None:
            return False
        
        if min_len is not None and len(texto) < min_len:
            logger.warning(f"⚠️ El campo {nombre_campo} debe tener al menos {min_len} caracteres")
            return False
        
        if max_len is not None and len(texto) > max_len:
            logger.warning(f"⚠️ El campo {nombre_campo} no debe exceder {max_len} caracteres")
            return False
        
        return True
    
    @staticmethod
    def validar_email(email: str) -> bool:
        """Valida formato de email"""
        if not email:
            return True  # Email puede ser opcional
        
        patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(patron, email):
            logger.warning(f"⚠️ El email {email} no tiene formato válido")
            return False
        return True
    
    @staticmethod
    def validar_telefono(telefono: str) -> bool:
        """Valida formato de teléfono (solo números, longitud entre 7-15)"""
        if not telefono:
            return True  # Teléfono puede ser opcional
        
        if not telefono.isdigit():
            logger.warning("⚠️ El teléfono debe contener solo números")
            return False
        
        if len(telefono) < 7 or len(telefono) > 15:
            logger.warning("⚠️ El teléfono debe tener entre 7 y 15 dígitos")
            return False
        
        return True
    
    @staticmethod
    def validar_documento(tipo: str, numero: str) -> bool:
        """Valida documento según tipo (DNI, RUC, etc.)"""
        if tipo.upper() == 'DNI':
            if len(numero) != 8 or not numero.isdigit():
                logger.warning("⚠️ DNI debe tener 8 dígitos")
                return False
        elif tipo.upper() == 'RUC':
            if len(numero) != 11 or not numero.isdigit():
                logger.warning("⚠️ RUC debe tener 11 dígitos")
                return False
        elif tipo.upper() == 'PASAPORTE':
            if len(numero) < 6 or len(numero) > 12:
                logger.warning("⚠️ Pasaporte debe tener entre 6 y 12 caracteres")
                return False
        return True
    
    @staticmethod
    def validar_fecha(fecha: datetime, nombre_campo: str, min_fecha: datetime = None, max_fecha: datetime = None) -> bool:
        """Valida que una fecha sea válida y esté en rango"""
        if not isinstance(fecha, datetime):
            logger.warning(f"⚠️ {nombre_campo} debe ser una fecha válida")
            return False
        
        if min_fecha and fecha < min_fecha:
            logger.warning(f"⚠️ {nombre_campo} no puede ser anterior a {min_fecha.strftime('%d/%m/%Y')}")
            return False
        
        if max_fecha and fecha > max_fecha:
            logger.warning(f"⚠️ {nombre_campo} no puede ser posterior a {max_fecha.strftime('%d/%m/%Y')}")
            return False
        
        return True
    
    @staticmethod
    def validar_entero_positivo(valor: int, nombre_campo: str, permitir_cero: bool = False) -> bool:
        """Valida que un número entero sea positivo"""
        if not isinstance(valor, int):
            logger.warning(f"⚠️ {nombre_campo} debe ser un número entero")
            return False
        
        if permitir_cero:
            if valor < 0:
                logger.warning(f"⚠️ {nombre_campo} no puede ser negativo")
                return False
        else:
            if valor <= 0:
                logger.warning(f"⚠️ {nombre_campo} debe ser mayor que cero")
                return False
        
        return True
    
    @staticmethod
    def validar_decimal_positivo(valor: float, nombre_campo: str, permitir_cero: bool = False) -> bool:
        """Valida que un número decimal sea positivo"""
        if not isinstance(valor, (int, float)):
            logger.warning(f"⚠️ {nombre_campo} debe ser un número")
            return False
        
        if permitir_cero:
            if valor < 0:
                logger.warning(f"⚠️ {nombre_campo} no puede ser negativo")
                return False
        else:
            if valor <= 0:
                logger.warning(f"⚠️ {nombre_campo} debe ser mayor que cero")
                return False
        
        return True

