"""
Servicio para gestión de compras - VERSIÓN SIMPLIFICADA
"""
from loguru import logger
from capa_datos.compra_repo import CompraRepositorio
from capa_datos.conexion import ConexionDB

class CompraService:
    def __init__(self):
        # Solo usamos el repositorio de compras
        self.repo = CompraRepositorio()
    
    def listar_compras(self):
        """Lista todas las compras"""
        try:
            return self.repo.listar()
        except Exception as e:
            logger.error(f"Error listando compras: {e}")
            return []
    
    def buscar_compra(self, idcompra):
        """Busca una compra por ID"""
        try:
            return self.repo.buscar_por_id(idcompra)
        except Exception as e:
            logger.error(f"Error buscando compra: {e}")
            return None
    
    def anular_compra(self, idcompra):
        """Anula una compra"""
        try:
            return self.repo.anular(idcompra)
        except Exception as e:
            logger.error(f"Error anulando compra: {e}")
            return False
