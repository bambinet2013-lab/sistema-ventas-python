from typing import List, Dict, Optional
from loguru import logger

class ClienteRepositorio:
    """Repositorio para operaciones CRUD de clientes"""
    
    def __init__(self, conexion):
        self.conexion = conexion
        self.cursor = conexion.cursor()
    
    def listar(self) -> List[Dict]:
        """Lista todos los clientes"""
        try:
            self.cursor.execute("""
                SELECT idcliente, nombre, apellidos, sexo, 
                       fecha_nacimiento, tipo_documento, num_documento,
                       direccion, telefono, email
                FROM cliente ORDER BY apellidos, nombre
            """)
            columnas = [column[0] for column in self.cursor.description]
            resultados = []
            for row in self.cursor.fetchall():
                resultados.append(dict(zip(columnas, row)))
            logger.info(f"✅ {len(resultados)} clientes listados")
            return resultados
        except Exception as e:
            logger.error(f"❌ Error al listar clientes: {e}")
            return []
    
    def obtener_por_id(self, idcliente: int) -> Optional[Dict]:
        """Obtiene un cliente por su ID"""
        try:
            self.cursor.execute(
                "SELECT * FROM cliente WHERE idcliente = ?",
                (idcliente,)
            )
            row = self.cursor.fetchone()
            if row:
                columnas = [column[0] for column in self.cursor.description]
                return dict(zip(columnas, row))
            return None
        except Exception as e:
            logger.error(f"❌ Error al obtener cliente {idcliente}: {e}")
            return None
    
    def buscar_por_documento(self, num_documento: str) -> Optional[Dict]:
        """Busca un cliente por número de documento"""
        try:
            self.cursor.execute(
                "SELECT idcliente, nombre, apellidos FROM cliente WHERE num_documento = ?",
                (num_documento,)
            )
            row = self.cursor.fetchone()
            if row:
                return {
                    'idcliente': row[0],
                    'nombre': row[1],
                    'apellidos': row[2]
                }
            return None
        except Exception as e:
            logger.error(f"❌ Error al buscar documento {num_documento}: {e}")
            return None
    
    def insertar(self, nombre: str, apellidos: str, fecha_nacimiento, 
                 tipo_documento: str, num_documento: str,
                 sexo: str = None, direccion: str = None, 
                 telefono: str = None, email: str = None) -> bool:
        """Inserta un nuevo cliente"""
        try:
            self.cursor.execute(
                """INSERT INTO cliente 
                   (nombre, apellidos, sexo, fecha_nacimiento, tipo_documento, 
                    num_documento, direccion, telefono, email) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (nombre, apellidos, sexo, fecha_nacimiento, tipo_documento,
                 num_documento, direccion, telefono, email)
            )
            self.cursor.commit()
            logger.success(f"✅ Cliente '{nombre} {apellidos}' insertado")
            return True
        except Exception as e:
            logger.error(f"❌ Error al insertar cliente: {e}")
            return False
    
    def actualizar(self, idcliente: int, nombre: str, apellidos: str, 
                   fecha_nacimiento, tipo_documento: str, num_documento: str,
                   sexo: str = None, direccion: str = None, 
                   telefono: str = None, email: str = None) -> bool:
        """Actualiza un cliente existente"""
        try:
            self.cursor.execute(
                """UPDATE cliente 
                   SET nombre = ?, apellidos = ?, sexo = ?, fecha_nacimiento = ?,
                       tipo_documento = ?, num_documento = ?, direccion = ?,
                       telefono = ?, email = ?
                   WHERE idcliente = ?""",
                (nombre, apellidos, sexo, fecha_nacimiento, tipo_documento,
                 num_documento, direccion, telefono, email, idcliente)
            )
            self.cursor.commit()
            logger.success(f"✅ Cliente ID {idcliente} actualizado")
            return True
        except Exception as e:
            logger.error(f"❌ Error al actualizar cliente: {e}")
            return False
    
    def eliminar(self, idcliente: int) -> bool:
        """Elimina un cliente"""
        try:
            self.cursor.execute("DELETE FROM cliente WHERE idcliente = ?", (idcliente,))
            self.cursor.commit()
            logger.success(f"✅ Cliente ID {idcliente} eliminado")
            return True
        except Exception as e:
            logger.error(f"❌ Error al eliminar cliente: {e}")
            return False
