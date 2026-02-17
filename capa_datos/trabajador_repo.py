from typing import List, Dict, Optional
from loguru import logger
import hashlib

class TrabajadorRepositorio:
    """Repositorio para operaciones CRUD de trabajadores"""
    
    def __init__(self, conexion):
        self.conexion = conexion
        self.cursor = conexion.cursor()
    
    def _hash_password(self, password: str) -> str:
        """Genera hash de contraseña"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def listar(self) -> List[Dict]:
        """Lista todos los trabajadores"""
        try:
            self.cursor.execute("""
                SELECT idtrabajador, nombre, apellidos, sexo,
                       fecha_nacimiento, num_documento, direccion,
                       telefono, email, usuario, idrol
                FROM trabajador ORDER BY apellidos, nombre
            """)
            columnas = [column[0] for column in self.cursor.description]
            resultados = []
            for row in self.cursor.fetchall():
                resultados.append(dict(zip(columnas, row)))
            logger.info(f"✅ {len(resultados)} trabajadores listados")
            return resultados
        except Exception as e:
            logger.error(f"❌ Error al listar trabajadores: {e}")
            return []
    
    def obtener_por_id(self, idtrabajador: int) -> Optional[Dict]:
        """Obtiene un trabajador por su ID"""
        try:
            self.cursor.execute(
                "SELECT * FROM trabajador WHERE idtrabajador = ?",
                (idtrabajador,)
            )
            row = self.cursor.fetchone()
            if row:
                columnas = [column[0] for column in self.cursor.description]
                return dict(zip(columnas, row))
            return None
        except Exception as e:
            logger.error(f"❌ Error al obtener trabajador {idtrabajador}: {e}")
            return None
    
    def autenticar(self, usuario: str, password: str) -> Optional[Dict]:
        """Autentica un trabajador por usuario y contraseña"""
        try:
            password_hash = self._hash_password(password)
            self.cursor.execute("""
                SELECT idtrabajador, nombre, apellidos, usuario, email, idrol
                FROM trabajador 
                WHERE usuario = ? AND password_hash = ?
            """, (usuario, password_hash))
            row = self.cursor.fetchone()
            if row:
                return {
                    'idtrabajador': row[0],
                    'nombre': row[1],
                    'apellidos': row[2],
                    'usuario': row[3],
                    'email': row[4],
                    'idrol': row[5]
                }
            return None
        except Exception as e:
            logger.error(f"❌ Error en autenticación: {e}")
            return None
    
    def buscar_por_email(self, email: str) -> Optional[Dict]:
        """Busca un trabajador por su email"""
        try:
            self.cursor.execute("""
                SELECT idtrabajador, nombre, apellidos, usuario, email, idrol
                FROM trabajador 
                WHERE email = ?
            """, (email,))
            row = self.cursor.fetchone()
            if row:
                return {
                    'idtrabajador': row[0],
                    'nombre': row[1],
                    'apellidos': row[2],
                    'usuario': row[3],
                    'email': row[4],
                    'idrol': row[5]
                }
            return None
        except Exception as e:
            logger.error(f"❌ Error al buscar por email: {e}")
            return None
    
    def autenticar_por_email(self, email: str, password: str) -> Optional[Dict]:
        """Autentica un trabajador por email y contraseña"""
        try:
            password_hash = self._hash_password(password)
            self.cursor.execute("""
                SELECT idtrabajador, nombre, apellidos, usuario, email, idrol
                FROM trabajador 
                WHERE email = ? AND password_hash = ?
            """, (email, password_hash))
            row = self.cursor.fetchone()
            if row:
                return {
                    'idtrabajador': row[0],
                    'nombre': row[1],
                    'apellidos': row[2],
                    'usuario': row[3],
                    'email': row[4],
                    'idrol': row[5]
                }
            return None
        except Exception as e:
            logger.error(f"❌ Error en autenticación por email: {e}")
            return None
    
    def insertar(self, nombre: str, apellidos: str, sexo: str,
                 fecha_nacimiento, num_documento: str,
                 usuario: str, password: str,
                 direccion: str = None, telefono: str = None,
                 email: str = None) -> bool:
        """Inserta un nuevo trabajador"""
        try:
            password_hash = self._hash_password(password)
            self.cursor.execute("""
                INSERT INTO trabajador 
                (nombre, apellidos, sexo, fecha_nacimiento, num_documento,
                 direccion, telefono, email, usuario, password_hash) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (nombre, apellidos, sexo, fecha_nacimiento, num_documento,
                 direccion, telefono, email, usuario, password_hash))
            self.cursor.commit()
            logger.success(f"✅ Trabajador '{nombre} {apellidos}' insertado")
            return True
        except Exception as e:
            logger.error(f"❌ Error al insertar trabajador: {e}")
            return False
    
    def actualizar(self, idtrabajador: int, nombre: str, apellidos: str, sexo: str,
                   fecha_nacimiento, num_documento: str, usuario: str,
                   password: str = None, direccion: str = None,
                   telefono: str = None, email: str = None) -> bool:
        """Actualiza un trabajador existente"""
        try:
            if password:
                password_hash = self._hash_password(password)
                self.cursor.execute("""
                    UPDATE trabajador 
                    SET nombre = ?, apellidos = ?, sexo = ?, fecha_nacimiento = ?,
                        num_documento = ?, direccion = ?, telefono = ?,
                        email = ?, usuario = ?, password_hash = ?
                    WHERE idtrabajador = ?
                """, (nombre, apellidos, sexo, fecha_nacimiento, num_documento,
                     direccion, telefono, email, usuario, password_hash, idtrabajador))
            else:
                self.cursor.execute("""
                    UPDATE trabajador 
                    SET nombre = ?, apellidos = ?, sexo = ?, fecha_nacimiento = ?,
                        num_documento = ?, direccion = ?, telefono = ?,
                        email = ?, usuario = ?
                    WHERE idtrabajador = ?
                """, (nombre, apellidos, sexo, fecha_nacimiento, num_documento,
                     direccion, telefono, email, usuario, idtrabajador))
            self.cursor.commit()
            logger.success(f"✅ Trabajador ID {idtrabajador} actualizado")
            return True
        except Exception as e:
            logger.error(f"❌ Error al actualizar trabajador: {e}")
            return False
    
    def eliminar(self, idtrabajador: int) -> bool:
        """Elimina un trabajador"""
        try:
            self.cursor.execute("DELETE FROM trabajador WHERE idtrabajador = ?", (idtrabajador,))
            self.cursor.commit()
            logger.success(f"✅ Trabajador ID {idtrabajador} eliminado")
            return True
        except Exception as e:
            logger.error(f"❌ Error al eliminar trabajador: {e}")
            return False
