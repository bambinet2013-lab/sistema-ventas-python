from typing import List, Dict, Optional
import os
from datetime import datetime
from loguru import logger
from capa_negocio.base_service import BaseService

class ProveedorArchivoService(BaseService):
    """Servicio para gestión de archivos de proveedores"""
    
    # Extensiones permitidas
    EXTENSIONES_PERMITIDAS = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.pdf': 'application/pdf',
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.csv': 'text/csv',
        '.txt': 'text/plain',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }
    
    TAMANO_MAXIMO = 10 * 1024 * 1024  # 10 MB
    
    def __init__(self, repositorio, proveedor_service=None):
        self.repositorio = repositorio
        self.proveedor_service = proveedor_service
    
    def listar_archivos_proveedor(self, idproveedor: int) -> List[Dict]:
        """Lista los archivos de un proveedor"""
        if not self.validar_entero_positivo(idproveedor, "ID de proveedor"):
            return []
        return self.repositorio.listar_por_proveedor(idproveedor)
    
    def obtener_archivo(self, idarchivo: int) -> Optional[Dict]:
        """Obtiene un archivo completo por su ID"""
        if not self.validar_entero_positivo(idarchivo, "ID de archivo"):
            return None
        return self.repositorio.obtener_archivo(idarchivo)
    
    def validar_archivo(self, nombre_archivo: str, contenido: bytes) -> bool:
        """Valida que el archivo sea válido (extensión y tamaño)"""
        if len(contenido) > self.TAMANO_MAXIMO:
            logger.warning(f"⚠️ Archivo demasiado grande: {len(contenido)} bytes")
            return False
        
        extension = os.path.splitext(nombre_archivo)[1].lower()
        if extension not in self.EXTENSIONES_PERMITIDAS:
            logger.warning(f"⚠️ Extensión '{extension}' no permitida")
            return False
        
        return True
    
    def subir_archivo(self, idproveedor: int, ruta_archivo: str, 
                      descripcion: str = None) -> Optional[int]:
        """Sube un archivo desde el sistema de archivos local"""
        
        if not self.validar_entero_positivo(idproveedor, "ID de proveedor"):
            return None
        
        if not os.path.exists(ruta_archivo):
            logger.warning(f"⚠️ El archivo '{ruta_archivo}' no existe")
            return None
        
        try:
            with open(ruta_archivo, 'rb') as f:
                contenido = f.read()
            
            nombre_archivo = os.path.basename(ruta_archivo)
            
            if not self.validar_archivo(nombre_archivo, contenido):
                return None
            
            extension = os.path.splitext(nombre_archivo)[1].lower()
            tipo_archivo = self.EXTENSIONES_PERMITIDAS.get(extension, 'application/octet-stream')
            
            return self.repositorio.insertar(
                idproveedor, nombre_archivo, tipo_archivo, contenido, descripcion
            )
        except Exception as e:
            logger.error(f"❌ Error al subir archivo: {e}")
            return None
    
    def guardar_archivo(self, idarchivo: int, ruta_destino: str) -> bool:
        """Guarda un archivo de la BD al sistema de archivos local"""
        if not self.validar_entero_positivo(idarchivo, "ID de archivo"):
            return False
        
        archivo = self.obtener_archivo(idarchivo)
        if not archivo:
            return False
        
        try:
            directorio = os.path.dirname(ruta_destino)
            if directorio and not os.path.exists(directorio):
                os.makedirs(directorio)
            
            with open(ruta_destino, 'wb') as f:
                f.write(archivo['contenido'])
            
            logger.success(f"✅ Archivo guardado en '{ruta_destino}'")
            return True
        except Exception as e:
            logger.error(f"❌ Error al guardar archivo: {e}")
            return False
    
    def eliminar_archivo(self, idarchivo: int) -> bool:
        """Elimina un archivo de la BD"""
        if not self.validar_entero_positivo(idarchivo, "ID de archivo"):
            return False
        return self.repositorio.eliminar(idarchivo)
    
    def obtener_tamano_legible(self, tamano_bytes: int) -> str:
        """Convierte tamaño de bytes a formato legible"""
        if tamano_bytes < 1024:
            return f"{tamano_bytes} B"
        elif tamano_bytes < 1024 * 1024:
            return f"{tamano_bytes / 1024:.1f} KB"
        else:
            return f"{tamano_bytes / (1024 * 1024):.1f} MB"
