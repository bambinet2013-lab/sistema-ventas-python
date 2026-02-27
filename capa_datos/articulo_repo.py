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
                item = dict(zip(columns, row))
                result.append(item)
            
            logger.info(f"✅ {len(result)} artículos listados")
            return result
            
        except Exception as e:
            logger.error(f"Error al listar artículos: {e}")
            return []
    
    def obtener_por_id(self, idarticulo):
        """
        Obtiene un artículo por su ID
        """
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT a.idarticulo, a.codigo, a.nombre, a.descripcion, a.imagen,
                   a.idcategoria, c.nombre as categoria,
                   a.idpresentacion, p.nombre as presentacion,
                   a.precio_venta, a.precio_referencia, a.stock_minimo,
                   a.codigo_barras_original
            FROM articulo a
            LEFT JOIN categoria c ON a.idcategoria = c.idcategoria
            LEFT JOIN presentacion p ON a.idpresentacion = p.idpresentacion
            WHERE a.idarticulo = ?
            """
            cursor.execute(query, (idarticulo,))
            row = cursor.fetchone()
            
            if row:
                columns = [column[0] for column in cursor.description]
                return dict(zip(columns, row))
            return None
            
        except Exception as e:
            logger.error(f"Error al obtener artículo por ID {idarticulo}: {e}")
            return None
    
    def buscar_por_codigo(self, codigo):
        """
        Busca un artículo por su código de barras o código interno
        """
        try:
            cursor = self.conn.cursor()
            query = """
            SELECT a.idarticulo, a.codigo, a.nombre, a.descripcion, a.imagen,
                   a.idcategoria, c.nombre as categoria,
                   a.idpresentacion, p.nombre as presentacion,
                   a.precio_venta, a.precio_referencia, a.stock_minimo,
                   a.codigo_barras_original
            FROM articulo a
            LEFT JOIN categoria c ON a.idcategoria = c.idcategoria
            LEFT JOIN presentacion p ON a.idpresentacion = p.idpresentacion
            WHERE a.codigo = ? OR a.codigo_barras_original = ?
            """
            cursor.execute(query, (codigo, codigo))
            row = cursor.fetchone()
            
            if row:
                columns = [column[0] for column in cursor.description]
                return dict(zip(columns, row))
            return None
            
        except Exception as e:
            logger.error(f"Error al buscar artículo por código {codigo}: {e}")
            return None
    
    def buscar_por_plu(self, plu):
        """
        Busca un artículo por su PLU
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
            WHERE a.plu = ?
            """
            cursor.execute(query, (plu,))
            row = cursor.fetchone()
            
            if row:
                columns = [column[0] for column in cursor.description]
                return dict(zip(columns, row))
            return None
            
        except Exception as e:
            logger.error(f"Error al buscar artículo por PLU {plu}: {e}")
            return None
    
    def crear(self, codigo, nombre, idcategoria, idpresentacion, 
              codigo_barras_original=None, descripcion=None, 
              imagen=None, precio_venta=0, precio_referencia=None, 
              stock_minimo=5):
        """
        Crea un nuevo artículo en la base de datos
        
        Args:
            codigo: Código profesional del artículo
            nombre: Nombre del artículo
            idcategoria: ID de la categoría
            idpresentacion: ID de la presentación
            codigo_barras_original: Código de barras original
            descripcion: Descripción del artículo
            imagen: Imagen del artículo
            precio_venta: Precio de venta
            precio_referencia: Precio de referencia
            stock_minimo: Stock mínimo
            igtf: Aplica IGTF
        """
        try:
            cursor = self.conn.cursor()
            query = """
            INSERT INTO articulo 
            (codigo, nombre, idcategoria, idpresentacion, codigo_barras_original,
             descripcion, imagen, precio_venta, precio_referencia, stock_minimo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(query, (
                codigo, nombre, idcategoria, idpresentacion, codigo_barras_original,
                descripcion, imagen, precio_venta, precio_referencia, stock_minimo
            ))
            
            # Obtener el ID del artículo insertado
            cursor.execute("SELECT @@IDENTITY AS id")
            row = cursor.fetchone()
            idarticulo = row[0] if row else None
            
            self.conn.commit()
            
            logger.info(f"✅ Artículo creado con ID: {idarticulo} - Código: {codigo} - Precio: {precio_venta}")
            return idarticulo
            
        except Exception as e:
            logger.error(f"❌ Error al crear artículo: {e}")
            self.conn.rollback()
            return None
    
    def actualizar_precio(self, idarticulo, nuevo_precio):
        """
        Actualiza el precio de venta de un artículo
        """
        try:
            cursor = self.conn.cursor()
            
            # Verificar que el artículo existe
            cursor.execute("SELECT idarticulo FROM articulo WHERE idarticulo = ?", (idarticulo,))
            if not cursor.fetchone():
                logger.warning(f"⚠️ Artículo {idarticulo} no encontrado")
                return False
            
            # Actualizar precio
            query = "UPDATE articulo SET precio_venta = ? WHERE idarticulo = ?"
            cursor.execute(query, (nuevo_precio, idarticulo))
            
            self.conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"✅ Precio actualizado en BD para artículo {idarticulo}: {nuevo_precio}")
                return True
            else:
                logger.warning(f"⚠️ No se actualizó ningún registro para artículo {idarticulo}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error actualizando precio en BD: {e}")
            self.conn.rollback()
            return False
    
    def actualizar_stock_minimo(self, idarticulo, stock_minimo):
        """
        Actualiza el stock mínimo de un artículo
        """
        try:
            cursor = self.conn.cursor()
            
            # Verificar que el artículo existe
            cursor.execute("SELECT idarticulo FROM articulo WHERE idarticulo = ?", (idarticulo,))
            if not cursor.fetchone():
                logger.warning(f"⚠️ Artículo {idarticulo} no encontrado")
                return False
            
            # Actualizar stock mínimo
            query = "UPDATE articulo SET stock_minimo = ? WHERE idarticulo = ?"
            cursor.execute(query, (stock_minimo, idarticulo))
            
            self.conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"✅ Stock mínimo actualizado en BD para artículo {idarticulo}: {stock_minimo}")
                return True
            else:
                logger.warning(f"⚠️ No se actualizó ningún registro para artículo {idarticulo}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error actualizando stock mínimo en BD: {e}")
            self.conn.rollback()
            return False
    
    def actualizar_nombre(self, idarticulo, nuevo_nombre):
        """
        Actualiza el nombre de un artículo
        """
        try:
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
            self.conn.rollback()
            return False
    
    def actualizar_categoria(self, idarticulo, nueva_categoria):
        """
        Actualiza la categoría de un artículo
        
        Args:
            idarticulo: ID del artículo
            nueva_categoria: ID de la nueva categoría
            
        Returns:
            bool: True si se actualizó correctamente
        """
        try:
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
            self.conn.rollback()
            return False
