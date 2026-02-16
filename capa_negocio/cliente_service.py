from typing import List, Dict, Optional
from datetime import datetime, date
from loguru import logger
from capa_negocio.base_service import BaseService

class ClienteService(BaseService):
    """Servicio de clientes con validaciones y lógica de negocio"""
    
    def __init__(self, repositorio):
        self.repositorio = repositorio
    
    def listar(self) -> List[Dict]:
        """Lista todos los clientes"""
        try:
            return self.repositorio.listar()
        except Exception as e:
            logger.error(f"❌ Error al listar clientes: {e}")
            return []
    
    def obtener_por_id(self, idcliente: int) -> Optional[Dict]:
        """Obtiene un cliente por ID"""
        if not self.validar_entero_positivo(idcliente, "ID de cliente"):
            return None
        return self.repositorio.obtener_por_id(idcliente)
    
    def buscar_por_documento(self, num_documento: str) -> Optional[Dict]:
        """Busca cliente por documento"""
        if not num_documento:
            return None
        return self.repositorio.buscar_por_documento(num_documento)
    
    def crear(self, nombre: str, apellidos: str, fecha_nacimiento,
              tipo_documento: str, num_documento: str,
              sexo: str = None, direccion: str = None,
              telefono: str = None, email: str = None) -> bool:
        """Crea un nuevo cliente con validaciones"""
        
        # Validaciones requeridas
        if not self.validar_requerido(nombre, "nombre"):
            return False
        if not self.validar_requerido(apellidos, "apellidos"):
            return False
        if not self.validar_requerido(tipo_documento, "tipo de documento"):
            return False
        if not self.validar_requerido(num_documento, "número de documento"):
            return False
        
        # Validaciones de longitud
        if not self.validar_longitud(nombre, "nombre", max_len=50):
            return False
        if not self.validar_longitud(apellidos, "apellidos", max_len=100):
            return False
        
        # Validar documento
        if not self.validar_documento(tipo_documento, num_documento):
            return False
        
        # Validar fecha (mayor de edad)
        if isinstance(fecha_nacimiento, str):
            fecha_nacimiento = datetime.strptime(fecha_nacimiento, '%Y-%m-%d').date()
        
        hoy = date.today()
        edad = hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))
        
        if edad < 18:
            logger.warning("⚠️ El cliente debe ser mayor de edad")
            return False
        
        # Validar email si se proporciona
        if email and not self.validar_email(email):
            return False
        
        # Validar teléfono si se proporciona
        if telefono and not self.validar_telefono(telefono):
            return False
        
        # Validar sexo
        if sexo and sexo not in ['M', 'F', 'O']:
            logger.warning("⚠️ Sexo debe ser M, F u O")
            return False
        
        try:
            return self.repositorio.insertar(
                nombre.strip(), apellidos.strip(), fecha_nacimiento,
                tipo_documento, num_documento, sexo, direccion, telefono, email
            )
        except Exception as e:
            logger.error(f"❌ Error al crear cliente: {e}")
            return False
    
    def actualizar(self, idcliente: int, nombre: str, apellidos: str, fecha_nacimiento,
                   tipo_documento: str, num_documento: str,
                   sexo: str = None, direccion: str = None,
                   telefono: str = None, email: str = None) -> bool:
        """Actualiza un cliente con validaciones"""
        
        if not self.validar_entero_positivo(idcliente, "ID de cliente"):
            return False
        
        # Mismas validaciones que en crear
        if not self.validar_requerido(nombre, "nombre"):
            return False
        if not self.validar_requerido(apellidos, "apellidos"):
            return False
        if not self.validar_requerido(tipo_documento, "tipo de documento"):
            return False
        if not self.validar_requerido(num_documento, "número de documento"):
            return False
        
        if not self.validar_documento(tipo_documento, num_documento):
            return False
        
        if email and not self.validar_email(email):
            return False
        
        if telefono and not self.validar_telefono(telefono):
            return False
        
        if sexo and sexo not in ['M', 'F', 'O']:
            logger.warning("⚠️ Sexo debe ser M, F u O")
            return False
        
        try:
            return self.repositorio.actualizar(
                idcliente, nombre.strip(), apellidos.strip(), fecha_nacimiento,
                tipo_documento, num_documento, sexo, direccion, telefono, email
            )
        except Exception as e:
            logger.error(f"❌ Error al actualizar cliente: {e}")
            return False
    
    def eliminar(self, idcliente: int) -> bool:
        """Elimina un cliente"""
        if not self.validar_entero_positivo(idcliente, "ID de cliente"):
            return False
        return self.repositorio.eliminar(idcliente)
