from typing import List, Dict, Optional
from datetime import date
from loguru import logger
from capa_negocio.base_service import BaseService

class TrabajadorService(BaseService):
    """Servicio de trabajadores con autenticación y roles"""
    
    def __init__(self, repositorio):
        self.repositorio = repositorio
        self.usuario_actual = None
        self.rol_service = None  # Se asignará desde el menú principal
    
    def listar(self) -> List[Dict]:
        """Lista todos los trabajadores"""
        try:
            return self.repositorio.listar()
        except Exception as e:
            logger.error(f"❌ Error al listar trabajadores: {e}")
            return []
    
    def obtener_por_id(self, idtrabajador: int) -> Optional[Dict]:
        """Obtiene un trabajador por ID"""
        if not self.validar_entero_positivo(idtrabajador, "ID de trabajador"):
            return None
        return self.repositorio.obtener_por_id(idtrabajador)
    
    def login(self, usuario: str, password: str) -> bool:
        """Autentica un trabajador y carga sus permisos"""
        if not usuario or not password:
            logger.warning("⚠️ Usuario y contraseña requeridos")
            return False
        
        trabajador = self.repositorio.autenticar(usuario, password)
        if trabajador:
            # Obtener rol del trabajador
            trabajador_completo = self.repositorio.obtener_por_id(trabajador['idtrabajador'])
            trabajador['idrol'] = trabajador_completo.get('idrol')
            
            self.usuario_actual = trabajador
            logger.success(f"✅ Bienvenido {trabajador['nombre']} {trabajador['apellidos']}")
            
            # Cargar permisos si hay servicio de roles disponible
            if self.rol_service and trabajador['idrol']:
                self.rol_service.cargar_permisos_usuario(trabajador['idrol'])
                permisos = len(self.rol_service.get_permisos_usuario())
                logger.info(f"🔑 Permisos cargados: {permisos} permisos")
            
            return True
        else:
            logger.warning("❌ Usuario o contraseña incorrectos")
            return False
    
    def logout(self):
        """Cierra sesión del trabajador actual"""
        if self.usuario_actual:
            logger.info(f"👋 Hasta luego {self.usuario_actual['nombre']}")
            self.usuario_actual = None
            if self.rol_service:
                self.rol_service.permisos_usuario_actual = set()
    
    def get_usuario_actual(self) -> Optional[Dict]:
        """Retorna el trabajador autenticado"""
        return self.usuario_actual
    
    def crear(self, nombre: str, apellidos: str, sexo: str,
              fecha_nacimiento, num_documento: str,
              usuario: str, password: str,
              direccion: str = None, telefono: str = None,
              email: str = None) -> bool:
        """Crea un nuevo trabajador con validaciones"""
        
        # Validaciones
        if not self.validar_requerido(nombre, "nombre"):
            return False
        if not self.validar_requerido(apellidos, "apellidos"):
            return False
        if not self.validar_requerido(sexo, "sexo"):
            return False
        if not self.validar_requerido(num_documento, "documento"):
            return False
        if not self.validar_requerido(usuario, "usuario"):
            return False
        if not self.validar_requerido(password, "contraseña"):
            return False
        
        # Validaciones específicas
        if sexo not in ['M', 'F', 'O']:
            logger.warning("⚠️ Sexo debe ser M, F u O")
            return False
        
        if len(password) < 6:
            logger.warning("⚠️ La contraseña debe tener al menos 6 caracteres")
            return False
        
        if email and not self.validar_email(email):
            return False
        
        if telefono and not self.validar_telefono(telefono):
            return False
        
        # Validar mayoría de edad
        if isinstance(fecha_nacimiento, str):
            fecha_nacimiento = date.fromisoformat(fecha_nacimiento)
        
        hoy = date.today()
        edad = hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))
        
        if edad < 18:
            logger.warning("⚠️ El trabajador debe ser mayor de edad")
            return False
        
        try:
            return self.repositorio.insertar(
                nombre.strip(), apellidos.strip(), sexo, fecha_nacimiento,
                num_documento, usuario, password, direccion, telefono, email
            )
        except Exception as e:
            logger.error(f"❌ Error al crear trabajador: {e}")
            return False
    
    def actualizar(self, idtrabajador: int, nombre: str, apellidos: str, sexo: str,
                   fecha_nacimiento, num_documento: str, usuario: str,
                   password: str = None, direccion: str = None,
                   telefono: str = None, email: str = None) -> bool:
        """Actualiza un trabajador existente"""
        
        if not self.validar_entero_positivo(idtrabajador, "ID de trabajador"):
            return False
        
        # Validaciones
        if not self.validar_requerido(nombre, "nombre"):
            return False
        if not self.validar_requerido(apellidos, "apellidos"):
            return False
        if not self.validar_requerido(sexo, "sexo"):
            return False
        if not self.validar_requerido(num_documento, "documento"):
            return False
        if not self.validar_requerido(usuario, "usuario"):
            return False
        
        if sexo not in ['M', 'F', 'O']:
            logger.warning("⚠️ Sexo debe ser M, F u O")
            return False
        
        if password and len(password) < 6:
            logger.warning("⚠️ La contraseña debe tener al menos 6 caracteres")
            return False
        
        if email and not self.validar_email(email):
            return False
        
        if telefono and not self.validar_telefono(telefono):
            return False
        
        try:
            return self.repositorio.actualizar(
                idtrabajador, nombre.strip(), apellidos.strip(), sexo, fecha_nacimiento,
                num_documento, usuario, password, direccion, telefono, email
            )
        except Exception as e:
            logger.error(f"❌ Error al actualizar trabajador: {e}")
            return False
    
    def eliminar(self, idtrabajador: int) -> bool:
        """Elimina un trabajador"""
        if not self.validar_entero_positivo(idtrabajador, "ID de trabajador"):
            return False
    def buscar_por_email(self, email):
        """Busca un trabajador por su email"""
        try:
            self.cursor.execute("SELECT idtrabajador, nombre, email FROM trabajador WHERE email = ?", (email,))
            return self.cursor.fetchone()
        except:
            return None
    
    def actualizar_password(self, email, nueva_password):
        """Actualiza la contraseña de un trabajador"""
        try:
            password_hash = hashlib.sha256(nueva_password.encode()).hexdigest()
            self.cursor.execute("UPDATE trabajador SET password_hash = ? WHERE email = ?", 
                               (password_hash, email))
            self.cursor.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Error al actualizar password: {e}")
            return False
        return self.repositorio.eliminar(idtrabajador)
