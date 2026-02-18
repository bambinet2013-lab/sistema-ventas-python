from typing import List, Dict, Optional
from loguru import logger
from capa_negocio.base_service import BaseService
from capa_negocio.validacion_venezuela import ValidacionVenezuela

class ProveedorService(BaseService):
    """Servicio para gestión de proveedores con validación venezolana"""
    
    def __init__(self, repositorio):
        self.repositorio = repositorio
    
    def listar(self) -> List[Dict]:
        """Lista todos los proveedores"""
        try:
            return self.repositorio.listar()
        except Exception as e:
            logger.error(f"❌ Error al listar proveedores: {e}")
            return []
    
    def obtener_por_id(self, idproveedor: int) -> Optional[Dict]:
        """Obtiene un proveedor por ID"""
        if not self.validar_entero_positivo(idproveedor, "ID de proveedor"):
            return None
        return self.repositorio.obtener_por_id(idproveedor)
    
    def _validar_documento_venezolano(self, tipo_doc: str, num_doc: str) -> bool:
        """
        Valida documentos venezolanos para proveedores
        - Personas naturales: V (venezolano), E (extranjero) → cédula
        - Personas jurídicas: J (empresa), G (gobierno), C (consejo comunal) → RIF
        - Pasaporte: PASAPORTE
        """
        tipo_doc = tipo_doc.upper()
        
        # Validar según el tipo de documento
        if tipo_doc in ['V', 'E']:
            # Cédula venezolana o extranjera
            if not ValidacionVenezuela.validar_cedula(num_doc):
                logger.warning(f"⚠️ Cédula '{num_doc}' inválida para tipo {tipo_doc}")
                return False
        
        elif tipo_doc in ['J', 'G', 'C']:
            # RIF de empresa, gobierno o consejo comunal
            rif_completo = f"{tipo_doc}-{num_doc}"
            if not ValidacionVenezuela.validar_rif(rif_completo):
                logger.warning(f"⚠️ RIF '{rif_completo}' inválido")
                return False
        
        elif tipo_doc == 'PASAPORTE':
            # Pasaporte (validación básica)
            if len(num_doc) < 6 or len(num_doc) > 12:
                logger.warning("⚠️ Pasaporte debe tener entre 6 y 12 caracteres")
                return False
        
        else:
            logger.warning(f"⚠️ Tipo de documento '{tipo_doc}' no válido")
            return False
        
        return True
    
    def crear(self, razon_social: str, sector_comercial: str,
              tipo_documento: str, num_documento: str,
              direccion: str = None, telefono: str = None,
              email: str = None, url: str = None) -> bool:
        """Crea un nuevo proveedor con validaciones"""
        
        # Validaciones básicas
        if not self.validar_requerido(razon_social, "razón social"):
            return False
        if not self.validar_requerido(sector_comercial, "sector comercial"):
            return False
        if not self.validar_requerido(tipo_documento, "tipo de documento"):
            return False
        if not self.validar_requerido(num_documento, "número de documento"):
            return False
        
        # Validación de longitud
        if not self.validar_longitud(razon_social, "razón social", max_len=150):
            return False
        
        # Validación de email si se proporciona
        if email and not self.validar_email(email):
            return False
        
        # Validación de teléfono si se proporciona
        if telefono and not self.validar_telefono(telefono):
            return False
        
        # Validación de documento venezolano
        if not self._validar_documento_venezolano(tipo_documento, num_documento):
            return False
        
        try:
            return self.repositorio.insertar(
                razon_social.strip(), sector_comercial.strip(),
                tipo_documento, num_documento.strip(),
                direccion, telefono, email, url
            )
        except Exception as e:
            logger.error(f"❌ Error al crear proveedor: {e}")
            return False
    
    def actualizar(self, idproveedor: int, razon_social: str, sector_comercial: str,
                   tipo_documento: str, num_documento: str,
                   direccion: str = None, telefono: str = None,
                   email: str = None, url: str = None) -> bool:
        """Actualiza un proveedor existente"""
        
        if not self.validar_entero_positivo(idproveedor, "ID de proveedor"):
            return False
        
        # Validaciones básicas
        if not self.validar_requerido(razon_social, "razón social"):
            return False
        if not self.validar_requerido(sector_comercial, "sector comercial"):
            return False
        if not self.validar_requerido(tipo_documento, "tipo de documento"):
            return False
        if not self.validar_requerido(num_documento, "número de documento"):
            return False
        
        # Validación de documento venezolano
        if not self._validar_documento_venezolano(tipo_documento, num_documento):
            return False
        
        if email and not self.validar_email(email):
            return False
        
        if telefono and not self.validar_telefono(telefono):
            return False
        
        try:
            return self.repositorio.actualizar(
                idproveedor, razon_social.strip(), sector_comercial.strip(),
                tipo_documento, num_documento.strip(),
                direccion, telefono, email, url
            )
        except Exception as e:
            logger.error(f"❌ Error al actualizar proveedor: {e}")
            return False
    
    def eliminar(self, idproveedor: int) -> bool:
        """Elimina un proveedor"""
        if not self.validar_entero_positivo(idproveedor, "ID de proveedor"):
            return False
        return self.repositorio.eliminar(idproveedor)
