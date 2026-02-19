"""
Servicio para la gestión de clientes
"""
from loguru import logger
import re
from capa_negocio.base_service import BaseService
from capa_negocio.validacion_venezuela import ValidacionVenezuela

class ClienteService(BaseService):
    """Servicio que implementa la lógica de negocio para clientes"""
    
    def __init__(self, repositorio):
        """
        Inicializa el servicio con un repositorio de clientes
        
        Args:
            repositorio: Instancia de ClienteRepositorio
        """
        # CORRECCIÓN: Llamar correctamente al constructor de BaseService
        # BaseService no requiere argumentos en __init__
        super().__init__()
        self.repositorio = repositorio
    
    def listar(self):
        """
        Lista todos los clientes
        
        Returns:
            list: Lista de clientes o lista vacía si hay error
        """
        try:
            return self.repositorio.listar()
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
            return self.repositorio.obtener_por_id(idcliente)
        except Exception as e:
            logger.error(f"Error al obtener cliente {idcliente}: {e}")
            return None
    
    def buscar_por_documento(self, documento):
        """
        Busca un cliente por su número de documento
        
        Args:
            documento (str): Documento completo (ej: V12345678)
            
        Returns:
            dict: Datos del cliente o None si no existe
        """
        try:
            # Separar tipo y número
            if documento and documento[0] in ['V', 'E', 'J', 'G', 'C']:
                tipo = documento[0]
                numero = documento[1:]
                return self.repositorio.buscar_por_documento(tipo, numero)
            return None
        except Exception as e:
            logger.error(f"Error al buscar cliente por documento {documento}: {e}")
            return None
    
    def crear(self, nombre, apellidos, fecha_nacimiento, tipo_documento, 
              num_documento, sexo=None, direccion=None, telefono=None, email=None):
        """
        Crea un nuevo cliente (fecha_nacimiento puede ser None)
        
        Args:
            nombre (str): Nombre del cliente
            apellidos (str): Apellidos del cliente
            fecha_nacimiento (str or None): Fecha de nacimiento (YYYY-MM-DD o None)
            tipo_documento (str): Tipo de documento (V, E, J, G, C, PASAPORTE)
            num_documento (str): Número de documento
            sexo (str, optional): Sexo (M, F, O)
            direccion (str, optional): Dirección
            telefono (str, optional): Teléfono
            email (str, optional): Email
            
        Returns:
            bool: True si se creó correctamente, False en caso contrario
        """
        try:
            # Validar campos obligatorios
            if not nombre or not nombre.strip():
                logger.error("El nombre es obligatorio")
                return False
            
            if not apellidos or not apellidos.strip():
                logger.error("Los apellidos son obligatorios")
                return False
            
            if not tipo_documento:
                logger.error("El tipo de documento es obligatorio")
                return False
            
            if not num_documento or not num_documento.strip():
                logger.error("El número de documento es obligatorio")
                return False
            
            # Validar formato del documento según el tipo
            if tipo_documento in ['V', 'E', 'J', 'G', 'C']:
                # Debe ser solo números y tener 8 dígitos
                if not num_documento.isdigit():
                    logger.error(f"El número de documento para tipo {tipo_documento} debe contener solo dígitos")
                    return False
                if len(num_documento) != 8:
                    logger.error(f"El número de documento para tipo {tipo_documento} debe tener 8 dígitos")
                    return False
            elif tipo_documento == 'PASAPORTE':
                # Pasaporte: entre 6 y 12 caracteres alfanuméricos
                if len(num_documento) < 6 or len(num_documento) > 12:
                    logger.error("El pasaporte debe tener entre 6 y 12 caracteres")
                    return False
                # Puede contener letras y números
                if not num_documento.isalnum():
                    logger.error("El pasaporte solo puede contener letras y números")
                    return False
            else:
                logger.error(f"Tipo de documento no válido: {tipo_documento}")
                return False
            
            # Validar email si se proporciona
            if email:
                if not self.validar_email(email):
                    logger.error("Formato de email inválido")
                    return False
            
            # Validar teléfono si se proporciona
            if telefono:
                if not self.validar_telefono(telefono):
                    logger.error("Formato de teléfono inválido")
                    return False
            
            # Validar fecha si se proporciona (formato YYYY-MM-DD)
            if fecha_nacimiento:
                # Verificar formato básico
                if not re.match(r'^\d{4}-\d{2}-\d{2}$', fecha_nacimiento):
                    logger.error("Formato de fecha inválido. Use YYYY-MM-DD")
                    return False
            
            # Crear cliente
            resultado = self.repositorio.crear(
                nombre.strip(), 
                apellidos.strip(), 
                fecha_nacimiento,  # Puede ser None
                tipo_documento, 
                num_documento.strip(),
                sexo.strip().upper() if sexo else None, 
                direccion.strip() if direccion else None, 
                telefono.strip() if telefono else None, 
                email.strip().lower() if email else None
            )
            
            if resultado:
                logger.info(f"Cliente creado: {nombre} {apellidos}")
                return True
            else:
                logger.error("No se pudo crear el cliente")
                return False
                
        except Exception as e:
            logger.error(f"Error al crear cliente: {e}")
            return False
    
    def actualizar(self, idcliente, nombre, apellidos, fecha_nacimiento, tipo_documento,
                   num_documento, sexo=None, direccion=None, telefono=None, email=None):
        """
        Actualiza un cliente existente
        
        Args:
            idcliente (int): ID del cliente a actualizar
            nombre (str): Nombre del cliente
            apellidos (str): Apellidos del cliente
            fecha_nacimiento (str or None): Fecha de nacimiento (YYYY-MM-DD o None)
            tipo_documento (str): Tipo de documento
            num_documento (str): Número de documento
            sexo (str, optional): Sexo
            direccion (str, optional): Dirección
            telefono (str, optional): Teléfono
            email (str, optional): Email
            
        Returns:
            bool: True si se actualizó correctamente, False en caso contrario
        """
        try:
            # Validar que el cliente existe
            cliente = self.obtener_por_id(idcliente)
            if not cliente:
                logger.error(f"Cliente {idcliente} no encontrado")
                return False
            
            # Validar campos obligatorios
            if not nombre or not nombre.strip():
                logger.error("El nombre es obligatorio")
                return False
            
            if not apellidos or not apellidos.strip():
                logger.error("Los apellidos son obligatorios")
                return False
            
            if not tipo_documento:
                logger.error("El tipo de documento es obligatorio")
                return False
            
            if not num_documento or not num_documento.strip():
                logger.error("El número de documento es obligatorio")
                return False
            
            # Validar formato del documento según el tipo
            if tipo_documento in ['V', 'E', 'J', 'G', 'C']:
                if not num_documento.isdigit():
                    logger.error(f"El número de documento para tipo {tipo_documento} debe contener solo dígitos")
                    return False
                if len(num_documento) != 8:
                    logger.error(f"El número de documento para tipo {tipo_documento} debe tener 8 dígitos")
                    return False
            elif tipo_documento == 'PASAPORTE':
                if len(num_documento) < 6 or len(num_documento) > 12:
                    logger.error("El pasaporte debe tener entre 6 y 12 caracteres")
                    return False
                if not num_documento.isalnum():
                    logger.error("El pasaporte solo puede contener letras y números")
                    return False
            else:
                logger.error(f"Tipo de documento no válido: {tipo_documento}")
                return False
            
            # Validar email si se proporciona
            if email:
                if not self.validar_email(email):
                    logger.error("Formato de email inválido")
                    return False
            
            # Validar teléfono si se proporciona
            if telefono:
                if not self.validar_telefono(telefono):
                    logger.error("Formato de teléfono inválido")
                    return False
            
            # Actualizar cliente
            resultado = self.repositorio.actualizar(
                idcliente,
                nombre.strip(), 
                apellidos.strip(), 
                fecha_nacimiento,  # Puede ser None
                tipo_documento, 
                num_documento.strip(),
                sexo.strip().upper() if sexo else None, 
                direccion.strip() if direccion else None, 
                telefono.strip() if telefono else None, 
                email.strip().lower() if email else None
            )
            
            if resultado:
                logger.info(f"Cliente {idcliente} actualizado correctamente")
                return True
            else:
                logger.error(f"No se pudo actualizar el cliente {idcliente}")
                return False
                
        except Exception as e:
            logger.error(f"Error al actualizar cliente {idcliente}: {e}")
            return False
    
    def eliminar(self, idcliente):
        """
        Elimina un cliente (lógicamente)
        
        Args:
            idcliente (int): ID del cliente a eliminar
            
        Returns:
            bool: True si se eliminó correctamente, False en caso contrario
        """
        try:
            # Validar que el cliente existe
            cliente = self.obtener_por_id(idcliente)
            if not cliente:
                logger.error(f"Cliente {idcliente} no encontrado")
                return False
            
            # Verificar si tiene ventas asociadas (esto lo haría el repositorio)
            resultado = self.repositorio.eliminar(idcliente)
            
            if resultado:
                logger.info(f"Cliente {idcliente} eliminado correctamente")
                return True
            else:
                logger.error(f"No se pudo eliminar el cliente {idcliente}")
                return False
                
        except Exception as e:
            logger.error(f"Error al eliminar cliente {idcliente}: {e}")
            return False
    
    def validar_email(self, email):
        """
        Valida el formato de un email
        
        Args:
            email (str): Email a validar
            
        Returns:
            bool: True si es válido, False en caso contrario
        """
        if not email:
            return True  # Email opcional
        
        patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(patron, email) is not None
    
    def validar_telefono(self, telefono):
        """
        Valida el formato de un teléfono venezolano
        
        Args:
            telefono (str): Teléfono a validar
            
        Returns:
            bool: True si es válido, False en caso contrario
        """
        if not telefono:
            return True  # Teléfono opcional
        
        # Limpiar el teléfono (quitar +, -, espacios)
        telefono_limpio = re.sub(r'[\+\-\s]', '', telefono)
        
        # Verificar que sea solo números y tenga entre 10 y 12 dígitos
        if not telefono_limpio.isdigit():
            return False
        
        if len(telefono_limpio) < 10 or len(telefono_limpio) > 12:
            return False
        
        return True
