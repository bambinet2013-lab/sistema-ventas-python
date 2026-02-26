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
        Lista todos los artículos con sus precios
        """
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT a.idarticulo, a.codigo, a.nombre, a.descripcion, a.imagen,
                   a.idcategoria, c.nombre as categoria,
                   a.idpresentacion, p.nombre as presentacion,
                   a.precio_venta, a.precio_referencia
            FROM articulo a
            LEFT JOIN categoria c ON a.idcategoria = c.idcategoria
            LEFT JOIN presentacion p ON a.idpresentacion = p.idpresentacion
            ORDER BY a.idarticulo DESC
            """
            cursor.execute(query)
            
            columns = [column[0] for column in cursor.description]
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
        Obtiene un artículo por su ID incluyendo precio_venta
        """
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT a.idarticulo, a.codigo, a.nombre, a.descripcion, a.imagen,
                   a.idcategoria, c.nombre as categoria,
                   a.idpresentacion, p.nombre as presentacion,
                   a.precio_venta, a.precio_referencia
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
        """Busca un artículo por su código"""
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT idarticulo, codigo, nombre, precio_venta
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
    
    def crear(self, codigo_barra, nombre, idcategoria, idpresentacion, descripcion=None, 
              imagen=None, precio_venta=0, precio_referencia=None):
        """
        Inserta un nuevo artículo con precio de venta
        """
        try:
            cursor = self.conn.cursor()
            
            query = """
            INSERT INTO articulo 
            (codigo, nombre, idcategoria, idpresentacion, descripcion, imagen, 
             precio_venta, precio_referencia)
            OUTPUT INSERTED.idarticulo
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            cursor.execute(query, (
                codigo, nombre, idcategoria, idpresentacion, descripcion, imagen,
                precio_venta, precio_referencia
            ))
            
            row = cursor.fetchone()
            idarticulo = row[0] if row else None
            self.conn.commit()
            
            logger.info(f"✅ Artículo creado con ID: {idarticulo} - Código: {codigo} - Precio: {precio_venta}")
            return idarticulo
            
        except Exception as e:
            logger.error(f"❌ Error al crear artículo: {e}")
            self.conn.rollback()
            return None
    
    def actualizar(self, idarticulo, codigo, nombre, idcategoria, idpresentacion, 
                   descripcion=None, imagen=None, precio_venta=None, precio_referencia=None):
        """
        Actualiza un artículo existente incluyendo precios
        """
        try:
            cursor = self.conn.cursor()
            
            # Construir query dinámicamente según qué campos vengan
            campos = []
            valores = []
            
            campos.append("codigo = ?")
            valores.append(codigo)
            
            campos.append("nombre = ?")
            valores.append(nombre)
            
            campos.append("idcategoria = ?")
            valores.append(idcategoria)
            
            campos.append("idpresentacion = ?")
            valores.append(idpresentacion)
            
            campos.append("descripcion = ?")
            valores.append(descripcion)
            
            # Solo agregar precio_venta si se proporciona explícitamente
            if precio_venta is not None:
                campos.append("precio_venta = ?")
                valores.append(precio_venta)
            
            # Solo agregar precio_referencia si se proporciona explícitamente
            if precio_referencia is not None:
                campos.append("precio_referencia = ?")
                valores.append(precio_referencia)
            
            if imagen is not None:
                campos.append("imagen = ?")
                valores.append(imagen)
            
            # Agregar ID al final
            valores.append(idarticulo)
            
            query = f"""
            UPDATE articulo 
            SET {', '.join(campos)}
            WHERE idarticulo = ?
            """
            
            cursor.execute(query, valores)
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
        """Busca artículos por nombre"""
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT idarticulo, codigo, nombre, precio_venta
            FROM articulo 
            WHERE nombre LIKE ? OR codigo LIKE ?
            ORDER BY nombre
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
            logger.error(f"Error buscando por nombre '{termino}': {e}")
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

    def buscar_por_codigo_barras(self, codigo):
        """Busca artículo por código de barras"""
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT idarticulo, codigo, nombre, precio_venta, tipo_medida, precio_por_kilo, es_pesado
            FROM articulo 
            WHERE codigo_barras = ?
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
            logger.error(f"Error buscando por código de barras {codigo}: {e}")
            return None
    
    def buscar_por_plu(self, plu):
        """
        Busca artículo por código interno PLU
        """
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT idarticulo, codigo, nombre, tipo_medida, precio_por_kilo, es_pesado
            FROM articulo 
            WHERE plu = ?
            """
            cursor.execute(query, (plu,))
            
            columns = [column[0] for column in cursor.description]
            row = cursor.fetchone()
            
            if row:
                result = {}
                for i, col in enumerate(columns):
                    result[col] = row[i]
                return result
            return None
            
        except Exception as e:
            logger.error(f"Error buscando por PLU {plu}: {e}")
            return None    

    def actualizar_precio(self, idarticulo, nuevo_precio):
        """
        Actualiza el precio de venta de un artículo en la base de datos
        
        Args:
            idarticulo (int): ID del artículo a actualizar
            nuevo_precio (float): Nuevo precio en USD
            
        Returns:
            bool: True si se actualizó correctamente, False en caso contrario
        """
        try:
            # Verificar que la conexión esté activa
            if not self.conn:
                logger.error("❌ No hay conexión a la base de datos")
                return False
            
            cursor = self.conn.cursor()
            
            # Verificar que el artículo existe
            cursor.execute("SELECT idarticulo FROM articulo WHERE idarticulo = ?", (idarticulo,))
            if not cursor.fetchone():
                logger.warning(f"⚠️ Artículo {idarticulo} no encontrado")
                return False
            
            # Actualizar precio
            query = "UPDATE articulo SET precio_venta = ? WHERE idarticulo = ?"
            cursor.execute(query, (nuevo_precio, idarticulo))
            
            # Confirmar cambios
            self.conn.commit()
            
            # Verificar que se actualizó
            if cursor.rowcount > 0:
                logger.info(f"✅ Precio actualizado en BD para artículo {idarticulo}: ${nuevo_precio:.2f}")
                return True
            else:
                logger.warning(f"⚠️ No se actualizó ningún registro para artículo {idarticulo}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error actualizando precio en BD: {e}")
            # Revertir cambios en caso de error
            try:
                self.conn.rollback()
            except:
                pass
            return False

    def actualizar_stock_minimo(self, idarticulo, stock_minimo):
        """
        Actualiza el stock mínimo de un artículo
        
        Args:
            idarticulo: ID del artículo
            stock_minimo: Nuevo stock mínimo
            
        Returns:
            bool: True si se actualizó correctamente
        """
        try:
            cursor = self.conn.cursor()
            query = "UPDATE articulo SET stock_minimo = ? WHERE idarticulo = ?"
            cursor.execute(query, (stock_minimo, idarticulo))
            self.conn.commit()
            logger.info(f"✅ Stock mínimo actualizado para artículo {idarticulo}: {stock_minimo}")
            return True
        except Exception as e:
            logger.error(f"❌ Error actualizando stock mínimo: {e}")
            self.conn.rollback()
            return False

    def actualizar_nombre(self, idarticulo: int, nuevo_nombre: str) -> bool:
        """
        Actualiza el nombre de un artículo en la base de datos
        
        Args:
            idarticulo: ID del artículo
            nuevo_nombre: Nuevo nombre
            
        Returns:
            bool: True si se actualizó correctamente
        """
        try:
            if not self.conn:
                logger.error("❌ No hay conexión a la base de datos")
                return False
            
            cursor = self.conn.cursor()
            
            # Verificar que el artículo existe
            cursor.execute("SELECT idarticulo FROM articulo WHERE idarticulo = ?", (idarticulo,))
            if not cursor.fetchone():
                logger.warning(f"⚠️ Artículo {idarticulo} no encontrado")
                return False
            
            # Actualizar nombre
            query = "UPDATE articulo SET nombre = ? WHERE idarticulo = ?"
            cursor.execute(query, (nuevo_nombre, idarticulo))
            
            self.conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"✅ Nombre actualizado en BD para artículo {idarticulo}: {nuevo_nombre}")
                return True
            else:
                logger.warning(f"⚠️ No se actualizó ningún registro para artículo {idarticulo}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error actualizando nombre en BD: {e}")
            try:
                self.conn.rollback()
            except:
                pass
            return False

    def actualizar_categoria(self, idarticulo: int, nueva_categoria: int) -> bool:
        """
        Actualiza la categoría de un artículo en la base de datos
        
        Args:
            idarticulo: ID del artículo
            nueva_categoria: ID de la nueva categoría
            
        Returns:
            bool: True si se actualizó correctamente
        """
        try:
            if not self.conn:
                logger.error("❌ No hay conexión a la base de datos")
                return False
            
            cursor = self.conn.cursor()
            
            # Verificar que el artículo existe
            cursor.execute("SELECT idarticulo FROM articulo WHERE idarticulo = ?", (idarticulo,))
            if not cursor.fetchone():
                logger.warning(f"⚠️ Artículo {idarticulo} no encontrado")
                return False
            
            # Verificar que la categoría existe
            cursor.execute("SELECT idcategoria FROM categoria WHERE idcategoria = ?", (nueva_categoria,))
            if not cursor.fetchone():
                logger.warning(f"⚠️ Categoría {nueva_categoria} no encontrada")
                return False
            
            # Actualizar categoría
            query = "UPDATE articulo SET idcategoria = ? WHERE idarticulo = ?"
            cursor.execute(query, (nueva_categoria, idarticulo))
            
            self.conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"✅ Categoría actualizada en BD para artículo {idarticulo}: {nueva_categoria}")
                return True
            else:
                logger.warning(f"⚠️ No se actualizó ningún registro para artículo {idarticulo}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error actualizando categoría en BD: {e}")
            try:
                self.conn.rollback()
            except:
                pass
            return False
