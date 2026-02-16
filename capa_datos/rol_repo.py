from typing import List, Dict, Optional
from loguru import logger

class RolRepositorio:
    """Repositorio para gestión de roles y permisos"""
    
    def __init__(self, conexion):
        self.conexion = conexion
        self.cursor = conexion.cursor()
    
    def listar_roles(self) -> List[Dict]:
        """Lista todos los roles"""
        try:
            self.cursor.execute("""
                SELECT idrol, nombre, descripcion, nivel, activo
                FROM rol
                ORDER BY nivel DESC
            """)
            columnas = [column[0] for column in self.cursor.description]
            return [dict(zip(columnas, row)) for row in self.cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ Error al listar roles: {e}")
            return []
    
    def obtener_rol(self, idrol: int) -> Optional[Dict]:
        """Obtiene un rol por su ID"""
        try:
            self.cursor.execute("""
                SELECT idrol, nombre, descripcion, nivel, activo
                FROM rol WHERE idrol = ?
            """, (idrol,))
            row = self.cursor.fetchone()
            if row:
                columnas = [column[0] for column in self.cursor.description]
                return dict(zip(columnas, row))
            return None
        except Exception as e:
            logger.error(f"❌ Error al obtener rol {idrol}: {e}")
            return None
    
    def listar_permisos(self, modulo: str = None) -> List[Dict]:
        """Lista todos los permisos, opcionalmente filtrados por módulo"""
        try:
            query = "SELECT idpermiso, nombre, descripcion, modulo FROM permiso"
            params = []
            if modulo:
                query += " WHERE modulo = ?"
                params.append(modulo)
            query += " ORDER BY modulo, nombre"
            
            self.cursor.execute(query, params)
            columnas = [column[0] for column in self.cursor.description]
            return [dict(zip(columnas, row)) for row in self.cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ Error al listar permisos: {e}")
            return []
    
    def obtener_permisos_rol(self, idrol: int) -> List[str]:
        """Obtiene los nombres de permisos de un rol"""
        try:
            self.cursor.execute("""
                SELECT p.nombre
                FROM permiso p
                INNER JOIN rol_permiso rp ON p.idpermiso = rp.idpermiso
                WHERE rp.idrol = ?
            """, (idrol,))
            return [row[0] for row in self.cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ Error al obtener permisos del rol {idrol}: {e}")
            return []
    
    def asignar_permisos_rol(self, idrol: int, permisos: List[int]) -> bool:
        """Asigna permisos a un rol (reemplaza los existentes)"""
        try:
            self.cursor.execute("BEGIN TRANSACTION")
            
            # Eliminar permisos actuales
            self.cursor.execute("DELETE FROM rol_permiso WHERE idrol = ?", (idrol,))
            
            # Insertar nuevos permisos
            for idpermiso in permisos:
                self.cursor.execute("""
                    INSERT INTO rol_permiso (idrol, idpermiso)
                    VALUES (?, ?)
                """, (idrol, idpermiso))
            
            self.cursor.execute("COMMIT TRANSACTION")
            logger.success(f"✅ Permisos asignados al rol {idrol}")
            return True
        except Exception as e:
            self.cursor.execute("ROLLBACK TRANSACTION")
            logger.error(f"❌ Error al asignar permisos: {e}")
            return False
    
    def asignar_rol_trabajador(self, idtrabajador: int, idrol: int) -> bool:
        """Asigna un rol a un trabajador"""
        try:
            self.cursor.execute("""
                UPDATE trabajador SET idrol = ? WHERE idtrabajador = ?
            """, (idrol, idtrabajador))
            self.cursor.commit()
            logger.success(f"✅ Rol {idrol} asignado al trabajador {idtrabajador}")
            return True
        except Exception as e:
            logger.error(f"❌ Error al asignar rol: {e}")
            return False
    
    def crear_rol(self, nombre: str, descripcion: str = None, nivel: int = 1) -> Optional[int]:
        """Crea un nuevo rol"""
        try:
            self.cursor.execute("""
                INSERT INTO rol (nombre, descripcion, nivel, activo)
                OUTPUT INSERTED.idrol
                VALUES (?, ?, ?, 1)
            """, (nombre, descripcion, nivel))
            idrol = self.cursor.fetchone()[0]
            self.cursor.commit()
            logger.success(f"✅ Rol '{nombre}' creado")
            return idrol
        except Exception as e:
            logger.error(f"❌ Error al crear rol: {e}")
            return None
