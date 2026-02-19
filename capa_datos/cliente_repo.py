"""
Repositorio para la gestión de clientes en la base de datos
"""
from loguru import logger

class ClienteRepositorio:
    """Clase que maneja las operaciones de base de datos para clientes"""
    
    def __init__(self, conn):
        """
        Inicializa el repositorio con una conexión a la base de datos
        
        Args:
            conn: Conexión a la base de datos
        """
        self.conn = conn
    
    def _row_to_dict(self, row, description):
        """
        Convierte una fila de pyodbc a diccionario
        """
        if not row:
            return None
        return {desc[0]: value for desc, value in zip(description, row)}
    
    def _rows_to_dicts(self, rows, description):
        """
        Convierte múltiples filas de pyodbc a lista de diccionarios
        """
        if not rows:
            return []
        return [self._row_to_dict(row, description) for row in rows]
    
    def listar(self):
        """
        Lista todos los clientes activos
        
        Returns:
            list: Lista de clientes o lista vacía si hay error
        """
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT idcliente, nombre, apellidos, fecha_nacimiento, 
                   tipo_documento, num_documento, sexo, direccion, telefono, email
            FROM cliente 
            ORDER BY idcliente DESC
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            description = cursor.description
            return self._rows_to_dicts(rows, description)
        except Exception as e:
            logger.error(f"Error al listar clientes: {e}")
            return []
    
    def obtener_por_id(self, idcliente):
        """
        Obtiene un cliente por su ID
        
        Args:
            idcliente (int): ID del cliente
            
        Returns:
            dict: Datos del cliente o None si no existe
        """
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT idcliente, nombre, apellidos, fecha_nacimiento, 
                   tipo_documento, num_documento, sexo, direccion, telefono, email
            FROM cliente 
            WHERE idcliente = ?
            """
            cursor.execute(query, (idcliente,))
            row = cursor.fetchone()
            description = cursor.description
            return self._row_to_dict(row, description)
        except Exception as e:
            logger.error(f"Error al obtener cliente {idcliente}: {e}")
            return None
    
    def buscar_por_documento(self, tipo_documento, num_documento):
        """
        Busca un cliente por tipo y número de documento
        
        Args:
            tipo_documento (str): Tipo de documento (V, E, J, G, C)
            num_documento (str): Número de documento
            
        Returns:
            dict: Datos del cliente o None si no existe
        """
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT idcliente, nombre, apellidos, fecha_nacimiento, 
                   tipo_documento, num_documento
            FROM cliente 
            WHERE tipo_documento = ? AND num_documento = ?
            """
            cursor.execute(query, (tipo_documento, num_documento))
            row = cursor.fetchone()
            description = cursor.description
            return self._row_to_dict(row, description)
        except Exception as e:
            logger.error(f"Error al buscar cliente por documento {tipo_documento}-{num_documento}: {e}")
            return None
    
    def crear(self, nombre, apellidos, fecha_nacimiento, tipo_documento, 
              num_documento, sexo=None, direccion=None, telefono=None, email=None):
        """
        Inserta un nuevo cliente (fecha_nacimiento puede ser NULL)
        """
        try:
            cursor = self.conn.cursor()
            
            query = """
            INSERT INTO cliente 
            (nombre, apellidos, fecha_nacimiento, tipo_documento, num_documento, 
             sexo, direccion, telefono, email)
            OUTPUT INSERTED.idcliente
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            cursor.execute(query, (
                nombre, apellidos, fecha_nacimiento, tipo_documento, num_documento,
                sexo, direccion, telefono, email
            ))
            
            row = cursor.fetchone()
            idcliente = row[0] if row else None
            self.conn.commit()
            
            if idcliente:
                logger.info(f"✅ Cliente creado con ID: {idcliente}")
                return idcliente
            return None
                
        except Exception as e:
            logger.error(f"❌ Error al crear cliente: {e}")
            self.conn.rollback()
            return None
    
    def actualizar(self, idcliente, nombre, apellidos, fecha_nacimiento, tipo_documento,
                   num_documento, sexo=None, direccion=None, telefono=None, email=None):
        """
        Actualiza un cliente existente
        
        Returns:
            bool: True si se actualizó correctamente, False en caso contrario
        """
        try:
            cursor = self.conn.cursor()
            query = """
            UPDATE cliente 
            SET nombre = ?, apellidos = ?, fecha_nacimiento = ?,
                tipo_documento = ?, num_documento = ?, sexo = ?,
                direccion = ?, telefono = ?, email = ?
            WHERE idcliente = ?
            """
            cursor.execute(query, (
                nombre, apellidos, fecha_nacimiento, tipo_documento, num_documento,
                sexo, direccion, telefono, email, idcliente
            ))
            self.conn.commit()
            afectadas = cursor.rowcount
            if afectadas > 0:
                logger.info(f"✅ Cliente {idcliente} actualizado correctamente")
                return True
            else:
                logger.warning(f"⚠️ No se encontró el cliente {idcliente} para actualizar")
                return False
        except Exception as e:
            logger.error(f"❌ Error al actualizar cliente {idcliente}: {e}")
            self.conn.rollback()
            return False
    
    def eliminar(self, idcliente):
        """
        Elimina un cliente (físicamente de la BD)
        
        Returns:
            bool: True si se eliminó correctamente, False en caso contrario
        """
        try:
            cursor = self.conn.cursor()
            
            # Verificar si el cliente tiene ventas asociadas
            check_query = "SELECT COUNT(*) as total FROM venta WHERE idcliente = ?"
            cursor.execute(check_query, (idcliente,))
            row = cursor.fetchone()
            total = row[0] if row else 0
            
            if total > 0:
                logger.warning(f"⚠️ Cliente {idcliente} tiene ventas asociadas. No se puede eliminar")
                return False
            
            # Eliminación física
            query = "DELETE FROM cliente WHERE idcliente = ?"
            cursor.execute(query, (idcliente,))
            self.conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"✅ Cliente {idcliente} eliminado correctamente")
                return True
            else:
                logger.warning(f"⚠️ No se encontró el cliente {idcliente} para eliminar")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error al eliminar cliente {idcliente}: {e}")
            self.conn.rollback()
            return False
    
    def buscar_por_nombre(self, termino):
        """
        Busca clientes por nombre o apellido (búsqueda parcial)
        """
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT idcliente, nombre, apellidos, fecha_nacimiento, 
                   tipo_documento, num_documento, telefono, email
            FROM cliente 
            WHERE nombre LIKE ? OR apellidos LIKE ?
            ORDER BY nombre, apellidos
            """
            busqueda = f"%{termino}%"
            cursor.execute(query, (busqueda, busqueda))
            rows = cursor.fetchall()
            description = cursor.description
            return self._rows_to_dicts(rows, description)
        except Exception as e:
            logger.error(f"Error al buscar clientes por nombre '{termino}': {e}")
            return []
    
    def contar_clientes(self):
        """
        Cuenta el número total de clientes
        """
        try:
            cursor = self.conn.cursor()
            query = "SELECT COUNT(*) as total FROM cliente"
            cursor.execute(query)
            row = cursor.fetchone()
            return row[0] if row else 0
        except Exception as e:
            logger.error(f"Error al contar clientes: {e}")
            return 0
    
    def clientes_recientes(self, limite=10):
        """
        Obtiene los clientes más recientes
        """
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT TOP (?) idcliente, nombre, apellidos, fecha_nacimiento, 
                   tipo_documento, num_documento, telefono, email
            FROM cliente 
            ORDER BY idcliente DESC
            """
            cursor.execute(query, (limite,))
            rows = cursor.fetchall()
            description = cursor.description
            return self._rows_to_dicts(rows, description)
        except Exception as e:
            logger.error(f"Error al obtener clientes recientes: {e}")
            return []
