from functools import wraps
from loguru import logger
from capa_negocio.rol_service import PermisoDenegadoError

def requiere_permiso(permiso: str):
    """Decorador para verificar permisos en métodos de menú"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                # Verificar si el usuario tiene el permiso
                if hasattr(self, 'rol_service') and self.rol_service:
                    self.rol_service.verificar_permiso(permiso)
                return func(self, *args, **kwargs)
            except PermisoDenegadoError as e:
                logger.warning(f"⛔ Acceso denegado: {e}")
                print(f"\n⛔ No tiene permisos para realizar esta operación.")
                print(f"   Permiso requerido: {permiso}")
                if hasattr(self, 'pausa'):
                    self.pausa()
                return None
        return wrapper
    return decorator
