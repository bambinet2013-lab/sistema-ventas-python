from typing import List, Dict, Optional
from datetime import datetime, date
from loguru import logger
from capa_negocio.base_service import BaseService

class UsuarioAdminService(BaseService):
    """Servicio para administración de usuarios (solo para admin)"""
    
    def __init__(self, repositorio, rol_service=None):
        self.repositorio = repositorio
        self.rol_service = rol_service
    
    def listar_usuarios(self) -> List[Dict]:
        """Lista todos los usuarios"""
        try:
            return self.repositorio.listar_usuarios()
        except Exception as e:
            logger.error(f"❌ Error al listar usuarios: {e}")
            return []
    
    def obtener_usuario(self, idtrabajador: int) -> Optional[Dict]:
        """Obtiene un usuario por ID"""
        if not self.validar_entero_positivo(idtrabajador, "ID de usuario"):
            return None
        return self.repositorio.obtener_usuario(idtrabajador)
    
    def crear_usuario(self, nombre: str, apellidos: str, sexo: str,
                      fecha_nacimiento, num_documento: str,
                      usuario: str, password: str,
                      email: str, idrol: int,
                      direccion: str = None, telefono: str = None) -> bool:
        """Crea un nuevo usuario con validaciones"""
        
        # Validaciones básicas
        if not self.validar_requerido(nombre, "nombre"):
            return False
        if not self.validar_requerido(apellidos, "apellidos"):
            return False
        if not self.validar_requerido(usuario, "usuario"):
            return False
        if not self.validar_requerido(password, "contraseña"):
            return False
        if not self.validar_requerido(email, "email"):
            return False
        if not self.validar_requerido(num_documento, "documento"):
            return False
        if not self.validar_entero_positivo(idrol, "rol"):
            return False
        
        # Validaciones específicas
        if len(password) < 6:
            logger.warning("⚠️ La contraseña debe tener al menos 6 caracteres")
            return False
        
        if not self.validar_email(email):
            return False
        
        if telefono and not self.validar_telefono(telefono):
            return False
        
        if sexo and sexo not in ['M', 'F', 'O']:
            logger.warning("⚠️ Sexo debe ser M, F u O")
            return False
        
        # Validar que no exista usuario con mismo username o email
        if self.repositorio.verificar_usuario_existe(usuario, email):
            logger.warning("⚠️ Ya existe un usuario con ese nombre de usuario o email")
            return False
        
        # Validar fecha de nacimiento (mayor de edad)
        if isinstance(fecha_nacimiento, str):
            fecha_nacimiento = datetime.strptime(fecha_nacimiento, '%Y-%m-%d').date()
        
        hoy = date.today()
        edad = hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))
        
        if edad < 18:
            logger.warning("⚠️ El usuario debe ser mayor de edad")
            return False
        
        # Verificar que el rol existe
        if self.rol_service:
            rol = self.rol_service.obtener_rol(idrol)
            if not rol:
                logger.warning(f"⚠️ El rol {idrol} no existe")
                return False
        
        try:
            return self.repositorio.crear_usuario(
                nombre.strip(), apellidos.strip(), sexo, fecha_nacimiento,
                num_documento, usuario.strip(), password, email.strip(),
                idrol, direccion, telefono
            )
        except Exception as e:
            logger.error(f"❌ Error al crear usuario: {e}")
            return False
    
    def actualizar_usuario(self, idtrabajador: int, nombre: str, apellidos: str,
                           sexo: str, fecha_nacimiento, num_documento: str,
                           usuario: str, email: str, idrol: int,
                           direccion: str = None, telefono: str = None,
                           nueva_password: str = None) -> bool:
        """Actualiza un usuario existente"""
        
        if not self.validar_entero_positivo(idtrabajador, "ID de usuario"):
            return False
        
        # Validaciones
        if not self.validar_requerido(nombre, "nombre"):
            return False
        if not self.validar_requerido(apellidos, "apellidos"):
            return False
        if not self.validar_requerido(usuario, "usuario"):
            return False
        if not self.validar_requerido(email, "email"):
            return False
        if not self.validar_entero_positivo(idrol, "rol"):
            return False
        
        if not self.validar_email(email):
            return False
        
        if telefono and not self.validar_telefono(telefono):
            return False
        
        if sexo and sexo not in ['M', 'F', 'O']:
            logger.warning("⚠️ Sexo debe ser M, F u O")
            return False
        
        if nueva_password and len(nueva_password) < 6:
            logger.warning("⚠️ La nueva contraseña debe tener al menos 6 caracteres")
            return False
        
        try:
            return self.repositorio.actualizar_usuario(
                idtrabajador, nombre.strip(), apellidos.strip(), sexo, fecha_nacimiento,
                num_documento, usuario.strip(), email.strip(), idrol,
                direccion, telefono, nueva_password
            )
        except Exception as e:
            logger.error(f"❌ Error al actualizar usuario: {e}")
            return False
    
    def eliminar_usuario(self, idtrabajador: int) -> bool:
        """Elimina un usuario (no puede eliminarse a sí mismo)"""
        # Esta validación se hará en el menú
        if not self.validar_entero_positivo(idtrabajador, "ID de usuario"):
            return False
        return self.repositorio.eliminar_usuario(idtrabajador)
