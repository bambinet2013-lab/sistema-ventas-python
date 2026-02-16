from typing import List, Dict, Optional
from loguru import logger
import hashlib

class UsuarioAdminRepositorio:
    """Repositorio para administración de usuarios (solo para admin)"""
    
    def __init__(self, conexion):
        self.conexion = conexion
        self.cursor = conexion.cursor()
    
    def listar_usuarios(self) -> List[Dict]:
        """Lista todos los usuarios con su información de rol"""
        try:
            self.cursor.execute("""
                SELECT t.idtrabajador, t.nombre, t.apellidos, t.usuario, 
                       t.email, t.telefono, t.idrol, r.nombre as rol_nombre
                FROM trabajador t
                LEFT JOIN rol r ON t.idrol = r.idrol
                ORDER BY t.idtrabajador
            """)
            columnas = [column[0] for column in self.cursor.description]
            return [dict(zip(columnas, row)) for row in self.cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ Error al listar usuarios: {e}")
            return []
    
    def obtener_usuario(self, idtrabajador: int) -> Optional[Dict]:
        """Obtiene un usuario por su ID"""
        try:
            self.cursor.execute("""
                SELECT t.*, r.nombre as rol_nombre
                FROM trabajador t
                LEFT JOIN rol r ON t.idrol = r.idrol
                WHERE t.idtrabajador = ?
            """, (idtrabajador,))
            row = self.cursor.fetchone()
            if row:
                columnas = [column[0] for column in self.cursor.description]
                return dict(zip(columnas, row))
            return None
        except Exception as e:
            logger.error(f"❌ Error al obtener usuario: {e}")
            return None
    
    def _hash_password(self, password: str) -> str:
        """Genera hash SHA256 de la contraseña"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def crear_usuario(self, nombre: str, apellidos: str, sexo: str,
                      fecha_nacimiento, num_documento: str,
                      usuario: str, password: str,
                      email: str, idrol: int,
                      direccion: str = None, telefono: str = None) -> bool:
        """Crea un nuevo usuario"""
        try:
            password_hash = self._hash_password(password)
            self.cursor.execute("""
                INSERT INTO trabajador 
                (nombre, apellidos, sexo, fecha_nacimiento, num_documento,
                 usuario, password_hash, email, idrol, direccion, telefono)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (nombre, apellidos, sexo, fecha_nacimiento, num_documento,
                  usuario, password_hash, email, idrol, direccion, telefono))
            self.cursor.commit()
            logger.success(f"✅ Usuario '{usuario}' creado")
            return True
        except Exception as e:
            logger.error(f"❌ Error al crear usuario: {e}")
            return False
    
    def actualizar_usuario(self, idtrabajador: int, nombre: str, apellidos: str,
                           sexo: str, fecha_nacimiento, num_documento: str,
                           usuario: str, email: str, idrol: int,
                           direccion: str = None, telefono: str = None,
                           nueva_password: str = None) -> bool:
        """Actualiza un usuario existente"""
        try:
            if nueva_password:
                password_hash = self._hash_password(nueva_password)
                self.cursor.execute("""
                    UPDATE trabajador 
                    SET nombre = ?, apellidos = ?, sexo = ?, fecha_nacimiento = ?,
                        num_documento = ?, usuario = ?, email = ?, idrol = ?,
                        direccion = ?, telefono = ?, password_hash = ?
                    WHERE idtrabajador = ?
                """, (nombre, apellidos, sexo, fecha_nacimiento, num_documento,
                      usuario, email, idrol, direccion, telefono, 
                      password_hash, idtrabajador))
            else:
                self.cursor.execute("""
                    UPDATE trabajador 
                    SET nombre = ?, apellidos = ?, sexo = ?, fecha_nacimiento = ?,
                        num_documento = ?, usuario = ?, email = ?, idrol = ?,
                        direccion = ?, telefono = ?
                    WHERE idtrabajador = ?
                """, (nombre, apellidos, sexo, fecha_nacimiento, num_documento,
                      usuario, email, idrol, direccion, telefono, idtrabajador))
            self.cursor.commit()
            logger.success(f"✅ Usuario ID {idtrabajador} actualizado")
            return True
        except Exception as e:
            logger.error(f"❌ Error al actualizar usuario: {e}")
            return False
    
    def eliminar_usuario(self, idtrabajador: int) -> bool:
        """Elimina un usuario"""
        try:
            self.cursor.execute("DELETE FROM trabajador WHERE idtrabajador = ?", (idtrabajador,))
            self.cursor.commit()
            logger.success(f"✅ Usuario ID {idtrabajador} eliminado")
            return True
        except Exception as e:
            logger.error(f"❌ Error al eliminar usuario: {e}")
            return False
    
    def verificar_usuario_existe(self, usuario: str, email: str) -> bool:
        """Verifica si ya existe un usuario con ese nombre o email"""
        try:
            self.cursor.execute("""
                SELECT COUNT(*) FROM trabajador 
                WHERE usuario = ? OR email = ?
            """, (usuario, email))
            count = self.cursor.fetchone()[0]
            return count > 0
        except Exception as e:
            logger.error(f"❌ Error al verificar usuario: {e}")
            return True  # Por seguridad, asumir que existe si hay error
