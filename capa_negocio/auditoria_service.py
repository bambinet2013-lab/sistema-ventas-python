"""
Servicio de auditoría para cumplimiento SENIAT
"""
from datetime import datetime
from loguru import logger

class AuditoriaService:
    """Registra todas las acciones del sistema para cumplimiento legal"""
    
    def __init__(self, repositorio):
        """
        Inicializa el servicio de auditoría
        
        Args:
            repositorio: Instancia de AuditoriaRepositorio
        """
        self.repositorio = repositorio
    
    def registrar(self, usuario, accion, tabla, registro_id, datos_anteriores=None, datos_nuevos=None):
        """
        Registra una acción en el log de auditoría
        
        Args:
            usuario: Nombre del usuario que ejecuta la acción
            accion: Tipo de acción (CREAR, MODIFICAR, ELIMINAR, ANULAR, etc)
            tabla: Tabla afectada
            registro_id: ID del registro afectado
            datos_anteriores: Estado anterior (para modificaciones)
            datos_nuevos: Estado nuevo
            
        Returns:
            bool: True si se registró correctamente
        """
        try:
            # Obtener IP (en un sistema real, obtener de la conexión)
            ip = '127.0.0.1'
            
            resultado = self.repositorio.insertar(
                usuario=usuario,
                accion=accion,
                tabla=tabla,
                registro_id=registro_id,
                datos_anteriores=str(datos_anteriores) if datos_anteriores else None,
                datos_nuevos=str(datos_nuevos) if datos_nuevos else None,
                ip_address=ip
            )
            
            if resultado:
                logger.info(f"📝 Auditoría: {usuario} - {accion} en {tabla} ID:{registro_id}")
            else:
                logger.error(f"❌ Error registrando auditoría: {usuario} - {accion}")
            
            return resultado
            
        except Exception as e:
            logger.error(f"Error en servicio de auditoría: {e}")
            return False
    
    def consultar_por_fecha(self, fecha_inicio, fecha_fin):
        """
        Consulta registros de auditoría por rango de fechas
        
        Args:
            fecha_inicio: Fecha inicial
            fecha_fin: Fecha final
            
        Returns:
            list: Lista de registros
        """
        return self.repositorio.consultar_por_fecha(fecha_inicio, fecha_fin)
    
    def consultar_por_usuario(self, usuario):
        """
        Consulta registros de un usuario específico
        
        Args:
            usuario: Nombre del usuario
            
        Returns:
            list: Lista de registros
        """
        return self.repositorio.consultar_por_usuario(usuario)
    
    def consultar_por_tabla(self, tabla, registro_id):
        """
        Consulta historial de cambios en un registro específico
        
        Args:
            tabla: Nombre de la tabla
            registro_id: ID del registro
            
        Returns:
            list: Lista de registros
        """
        return self.repositorio.consultar_por_tabla(tabla, registro_id)
