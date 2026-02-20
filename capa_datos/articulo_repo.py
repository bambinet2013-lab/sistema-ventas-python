"""
Repositorio para la gestión de artículos en la base de datos
"""
from loguru import logger

class ArticuloRepositorio:
    """Clase que maneja las operaciones de base de datos para artículos"""
    
    def __init__(self, conn):
        """
        Inicializa el repositorio con una conexión a la base de datos
        
        Args:
            conn: Conexión a la base de datos
        """
        self.conn = conn
        logger.info("✅ ArticuloRepositorio inicializado")
    
    def listar(self):
        """
        Lista todos los artículos activos
        
        Returns:
            list: Lista de artículos o lista vacía si hay error
        """
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT a.idarticulo, a.codigo, a.nombre, a.descripcion, a.imagen,
                   a.idcategoria, c.nombre as categoria,
                   a.idpresentacion, p.nombre as presentacion
            FROM articulo a
            LEFT JOIN categoria c ON a.idcategoria = c.idcategoria
            LEFT JOIN presentacion p ON a.idpresentacion = p.idpresentacion
            ORDER BY a.idarticulo DESC
            """
            cursor.execute(query)
            
            # Obtener los nombres de las columnas
            columns = [column[0] for column in cursor.description]
            
            # Convertir las filas a diccionarios
            rows = cursor.fetchall()
            result = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    row_dict[col] = row[i]
                result.append(row_dict)
            
            logger.info(f"✅ {len(result)} artículos listados")
            return result
            
        except Exception as e:
            logger.error(f"Error al listar artículos: {e}")
            return []
    
    def obtener_por_id(self, idarticulo):
        """
        Obtiene un artículo por su ID
        
        Args:
            idarticulo (int): ID del artículo
            
        Returns:
            dict: Datos del artículo o None si no existe
        """
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT a.idarticulo, a.codigo, a.nombre, a.descripcion, a.imagen,
                   a.idcategoria, c.nombre as categoria,
                   a.idpresentacion, p.nombre as presentacion
            FROM articulo a
            LEFT JOIN categoria c ON a.idcategoria = c.idcategoria
            LEFT JOIN presentacion p ON a.idpresentacion = p.idpresentacion
            WHERE a.idarticulo = ?
            """
            cursor.execute(query, (idarticulo,))
            
            columns = [column[0] for column in cursor.description]
            row = cursor.fetchone()
            
            if row:
                result = {}
                for i, col in enumerate(columns):
                    result[col] = row[i]
                return result
            return None
            
        except Exception as e:
            logger.error(f"Error al obtener artículo {idarticulo}: {e}")
            return None
    
    def buscar_por_codigo(self, codigo):
        """
        Busca un artículo por su código
        
        Args:
            codigo (str): Código del artículo
            
        Returns:
            dict: Datos del artículo o None si no existe
        """
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT idarticulo, codigo, nombre
            FROM articulo 
            WHERE codigo = ?
            """
            cursor.execute(query, (codigo,))
            
            columns = [column[0] for column in cursor.description]
            row = cursor.fetchone()
            
            if row:
                result = {}
                for i, col in enumerate(columns):
                    result[col] = row[i]
                return result
            return None
            
        except Exception as e:
            logger.error(f"Error al buscar artículo por código {codigo}: {e}")
            return None
    
    def crear(self, codigo, nombre, idcategoria, idpresentacion, descripcion=None, imagen=None):
        """
        Inserta un nuevo artículo
        
        Args:
            codigo (str): Código del artículo
            nombre (str): Nombre del artículo
            idcategoria (int): ID de la categoría
            idpresentacion (int): ID de la presentación
            descripcion (str, optional): Descripción
            imagen (bytes, optional): Imagen del artículo
            
        Returns:
            int or None: ID del artículo creado o None si hay error
        """
        try:
            cursor = self.conn.cursor()
            
            query = """
            INSERT INTO articulo 
            (codigo, nombre, idcategoria, idpresentacion, descripcion, imagen)
            OUTPUT INSERTED.idarticulo
            VALUES (?, ?, ?, ?, ?, ?)
            """
            
            cursor.execute(query, (codigo, nombre, idcategoria, idpresentacion, descripcion, imagen))
            
            row = cursor.fetchone()
            idarticulo = row[0] if row else None
            self.conn.commit()
            
            logger.info(f"✅ Artículo creado con ID: {idarticulo} - Código: {codigo}")
            return idarticulo
            
        except Exception as e:
            logger.error(f"❌ Error al crear artículo: {e}")
            self.conn.rollback()
            return None
    
    def actualizar(self, idarticulo, codigo, nombre, idcategoria, idpresentacion, descripcion=None, imagen=None):
        """
        Actualiza un artículo existente
        
        Args:
            idarticulo (int): ID del artículo
            codigo (str): Código del artículo
            nombre (str): Nombre del artículo
            idcategoria (int): ID de la categoría
            idpresentacion (int): ID de la presentación
            descripcion (str, optional): Descripción
            imagen (bytes, optional): Imagen del artículo
            
        Returns:
            bool: True si se actualizó correctamente, False en caso contrario
        """
        try:
            cursor = self.conn.cursor()
            
            if imagen is not None:
                query = """
                UPDATE articulo 
                SET codigo = ?, nombre = ?, idcategoria = ?, 
                    idpresentacion = ?, descripcion = ?, imagen = ?
                WHERE idarticulo = ?
                """
                cursor.execute(query, (codigo, nombre, idcategoria, idpresentacion, descripcion, imagen, idarticulo))
            else:
                query = """
                UPDATE articulo 
                SET codigo = ?, nombre = ?, idcategoria = ?, 
                    idpresentacion = ?, descripcion = ?
                WHERE idarticulo = ?
                """
                cursor.execute(query, (codigo, nombre, idcategoria, idpresentacion, descripcion, idarticulo))
            
            self.conn.commit()
            afectadas = cursor.rowcount
            
            if afectadas > 0:
                logger.info(f"✅ Artículo {idarticulo} actualizado correctamente")
                return True
            else:
                logger.warning(f"⚠️ No se encontró el artículo {idarticulo} para actualizar")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error al actualizar artículo {idarticulo}: {e}")
            self.conn.rollback()
            return False
    
    def eliminar(self, idarticulo):
        """
        Elimina un artículo (verifica si tiene movimientos asociados)
        
        Args:
            idarticulo (int): ID del artículo a eliminar
            
        Returns:
            bool: True si se eliminó correctamente, False en caso contrario
        """
        try:
            cursor = self.conn.cursor()
            
            # Verificar si el artículo tiene movimientos en kardex
            check_kardex = "SELECT COUNT(*) as total FROM kardex WHERE idarticulo = ?"
            cursor.execute(check_kardex, (idarticulo,))
            row = cursor.fetchone()
            total_kardex = row[0] if row else 0
            
            if total_kardex > 0:
                logger.warning(f"⚠️ Artículo {idarticulo} tiene movimientos en kardex. No se puede eliminar")
                return False
            
            # Verificar si el artículo tiene detalles de venta
            check_ventas = "SELECT COUNT(*) as total FROM detalle_venta WHERE idarticulo = ?"
            cursor.execute(check_ventas, (idarticulo,))
            row = cursor.fetchone()
            total_ventas = row[0] if row else 0
            
            if total_ventas > 0:
                logger.warning(f"⚠️ Artículo {idarticulo} tiene ventas asociadas. No se puede eliminar")
                return False
            
            # Verificar si el artículo tiene detalles de ingreso
            check_ingresos = "SELECT COUNT(*) as total FROM detalle_ingreso WHERE idarticulo = ?"
            cursor.execute(check_ingresos, (idarticulo,))
            row = cursor.fetchone()
            total_ingresos = row[0] if row else 0
            
            if total_ingresos > 0:
                logger.warning(f"⚠️ Artículo {idarticulo} tiene ingresos asociados. No se puede eliminar")
                return False
            
            # Si no tiene movimientos, eliminar
            query = "DELETE FROM articulo WHERE idarticulo = ?"
            cursor.execute(query, (idarticulo,))
            self.conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"✅ Artículo {idarticulo} eliminado correctamente")
                return True
            else:
                logger.warning(f"⚠️ No se encontró el artículo {idarticulo} para eliminar")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error al eliminar artículo {idarticulo}: {e}")
            self.conn.rollback()
            return False
    
    def buscar_por_nombre(self, termino):
        """
        Busca artículos por nombre (búsqueda parcial)
        
        Args:
            termino (str): Término de búsqueda
            
        Returns:
            list: Lista de artículos que coinciden
        """
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT idarticulo, codigo, nombre, descripcion
            FROM articulo 
            WHERE nombre LIKE ? OR codigo LIKE ?
            ORDER BY nombre
            LIMIT 20
            """
            busqueda = f"%{termino}%"
            cursor.execute(query, (busqueda, busqueda))
            
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            result = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    row_dict[col] = row[i]
                result.append(row_dict)
            
            return result
            
        except Exception as e:
            logger.error(f"Error al buscar artículos por nombre '{termino}': {e}")
            return []
    
    def contar_articulos(self):
        """
        Cuenta el número total de artículos
        
        Returns:
            int: Número de artículos o 0 si hay error
        """
        try:
            cursor = self.conn.cursor()
            query = "SELECT COUNT(*) as total FROM articulo"
            cursor.execute(query)
            row = cursor.fetchone()
            return row[0] if row else 0
        except Exception as e:
            logger.error(f"Error al contar artículos: {e}")
            return 0
    
    def articulos_con_stock_bajo(self, limite=5):
        """
        Obtiene artículos con stock bajo (requiere join con kardex)
        
        Args:
            limite (int): Límite de stock para considerar bajo
            
        Returns:
            list: Lista de artículos con stock bajo
        """
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT a.idarticulo, a.codigo, a.nombre, 
                   ISNULL((
                       SELECT TOP 1 k.stock_nuevo 
                       FROM kardex k 
                       WHERE k.idarticulo = a.idarticulo 
                       ORDER BY k.fecha_movimiento DESC
                   ), 0) as stock_actual
            FROM articulo a
            HAVING stock_actual < ?
            ORDER BY stock_actual ASC
            """
            cursor.execute(query, (limite,))
            
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            result = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    row_dict[col] = row[i]
                result.append(row_dict)
            
            return result
            
        except Exception as e:
            logger.error(f"Error al obtener artículos con stock bajo: {e}")
            return []
