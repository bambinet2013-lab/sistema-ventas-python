from typing import List, Dict, Optional, Set
from loguru import logger
from capa_negocio.base_service import BaseService

class PermisoDenegadoError(Exception):
    """Excepción para cuando un usuario no tiene permiso"""
    pass

class RolService(BaseService):
    """Servicio para gestión de roles y permisos"""
    
    def __init__(self, repositorio):
        self.repositorio = repositorio
        self.permisos_usuario_actual: Set[str] = set()
    
    def cargar_permisos_usuario(self, idrol: int):
        """Carga los permisos del rol del usuario actual"""
        if idrol:
            self.permisos_usuario_actual = set(self.repositorio.obtener_permisos_rol(idrol))
            logger.info(f"✅ Permisos cargados para rol {idrol}: {len(self.permisos_usuario_actual)} permisos")
        else:
            self.permisos_usuario_actual = set()
    
    def tiene_permiso(self, permiso: str) -> bool:
        """Verifica si el usuario actual tiene un permiso específico"""
        return permiso in self.permisos_usuario_actual
    
    def verificar_permiso(self, permiso: str):
        """Verifica permiso o lanza excepción"""
        if not self.tiene_permiso(permiso):
            logger.warning(f"⚠️ Permiso denegado: {permiso}")
            raise PermisoDenegadoError(f"No tiene permiso para: {permiso}")
    
    def listar_roles(self) -> List[Dict]:
        """Lista roles disponibles"""
        return self.repositorio.listar_roles()
    
    def listar_permisos_por_modulo(self) -> Dict[str, List[Dict]]:
        """Lista permisos agrupados por módulo"""
        todos = self.repositorio.listar_permisos()
        por_modulo = {}
        for permiso in todos:
            modulo = permiso['modulo']
            if modulo not in por_modulo:
                por_modulo[modulo] = []
            por_modulo[modulo].append(permiso)
        return por_modulo
    
    def obtener_permisos_rol(self, idrol: int) -> List[str]:
        """Obtiene permisos de un rol"""
        return self.repositorio.obtener_permisos_rol(idrol)
    
    def asignar_permisos_rol(self, idrol: int, permisos: List[int]) -> bool:
        """Asigna permisos a un rol (requiere permiso de administrador)"""
        self.verificar_permiso('usuarios_asignar_roles')
        return self.repositorio.asignar_permisos_rol(idrol, permisos)
    
    def asignar_rol_trabajador(self, idtrabajador: int, idrol: int) -> bool:
        """Asigna rol a trabajador (requiere permiso de administrador)"""
        self.verificar_permiso('usuarios_editar')
        return self.repositorio.asignar_rol_trabajador(idtrabajador, idrol)
    
    def crear_rol(self, nombre: str, descripcion: str = None, nivel: int = 1) -> Optional[int]:
        """Crea un nuevo rol (requiere permiso de administrador)"""
        self.verificar_permiso('usuarios_crear')
        return self.repositorio.crear_rol(nombre, descripcion, nivel)
    
    def get_permisos_usuario(self) -> Set[str]:
        """Retorna los permisos del usuario actual"""
        return self.permisos_usuario_actual
