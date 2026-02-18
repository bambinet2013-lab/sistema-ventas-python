from typing import List, Dict, Optional
from datetime import datetime, date
from loguru import logger
from capa_negocio.base_service import BaseService
from capa_negocio.validacion_venezuela import ValidacionVenezuela

class ClienteService(BaseService):
    """Servicio de clientes con validaciones y lógica de negocio"""
    
    def __init__(self, repositorio):
        self.repositorio = repositorio
    
    def listar(self) -> List[Dict]:
        """Lista todos los clientes"""
        try:
            return self.repositorio.listar()
        except Exception as e:
            logger.error(f"❌ Error al listar clientes: {e}")
            return []
    
    def obtener_por_id(self, idcliente: int) -> Optional[Dict]:
        """Obtiene un cliente por ID"""
        if not self.validar_entero_positivo(idcliente, "ID de cliente"):
            return None
        return self.repositorio.obtener_por_id(idcliente)
    
    def buscar_por_documento(self, num_documento: str) -> Optional[Dict]:
        """Busca cliente por documento"""
        if not num_documento:
            return None
        return self.repositorio.buscar_por_documento(num_documento)
    
    def _procesar_fecha(self, fecha_nacimiento):
        """
        Procesa una fecha en diferentes formatos y retorna un objeto date
        """
        try:
            if isinstance(fecha_nacimiento, date):
                # Ya es un objeto date, retornarlo directamente
                return fecha_nacimiento
                
            elif isinstance(fecha_nacimiento, str):
                fecha_nacimiento = fecha_nacimiento.strip()
                
                # Si viene en formato DD/MM/YYYY (de la máscara)
                if '/' in fecha_nacimiento:
                    partes = fecha_nacimiento.split('/')
                    if len(partes) == 3:
                        dia, mes, anio = partes
                        if not (dia.isdigit() and mes.isdigit() and anio.isdigit()):
                            raise ValueError("La fecha debe contener solo números")
                        if int(dia) < 1 or int(dia) > 31:
                            raise ValueError("Día inválido")
                        if int(mes) < 1 or int(mes) > 12:
                            raise ValueError("Mes inválido")
                        if int(anio) < 1900 or int(anio) > 2100:
                            raise ValueError("Año inválido")
                        return datetime.strptime(f"{anio}-{mes}-{dia}", '%Y-%m-%d').date()
                    else:
                        raise ValueError("Formato de fecha inválido")
                
                # Si viene en formato DD-MM-YYYY
                elif '-' in fecha_nacimiento and len(fecha_nacimiento) == 10:
                    partes = fecha_nacimiento.split('-')
                    if len(partes) == 3:
                        if len(partes[0]) == 4:  # YYYY-MM-DD
                            anio, mes, dia = partes
                        else:  # DD-MM-YYYY
                            dia, mes, anio = partes
                        
                        if not (dia.isdigit() and mes.isdigit() and anio.isdigit()):
                            raise ValueError("La fecha debe contener solo números")
                        if int(dia) < 1 or int(dia) > 31:
                            raise ValueError("Día inválido")
                        if int(mes) < 1 or int(mes) > 12:
                            raise ValueError("Mes inválido")
                        if int(anio) < 1900 or int(anio) > 2100:
                            raise ValueError("Año inválido")
                        return datetime.strptime(f"{anio}-{mes}-{dia}", '%Y-%m-%d').date()
                    else:
                        raise ValueError("Formato de fecha inválido")
                
                # Si viene como YYYY-MM-DD (formato de BD)
                elif '-' in fecha_nacimiento and len(fecha_nacimiento) == 10:
                    partes = fecha_nacimiento.split('-')
                    if len(partes) == 3:
                        anio, mes, dia = partes
                        if not (dia.isdigit() and mes.isdigit() and anio.isdigit()):
                            raise ValueError("La fecha debe contener solo números")
                        if int(dia) < 1 or int(dia) > 31:
                            raise ValueError("Día inválido")
                        if int(mes) < 1 or int(mes) > 12:
                            raise ValueError("Mes inválido")
                        if int(anio) < 1900 or int(anio) > 2100:
                            raise ValueError("Año inválido")
                        return datetime.strptime(fecha_nacimiento, '%Y-%m-%d').date()
                
                # Si viene sin separadores (DDMMYYYY)
                elif len(fecha_nacimiento) == 8 and fecha_nacimiento.isdigit():
                    dia = fecha_nacimiento[0:2]
                    mes = fecha_nacimiento[2:4]
                    anio = fecha_nacimiento[4:8]
                    if int(dia) < 1 or int(dia) > 31:
                        raise ValueError("Día inválido")
                    if int(mes) < 1 or int(mes) > 12:
                        raise ValueError("Mes inválido")
                    if int(anio) < 1900 or int(anio) > 2100:
                        raise ValueError("Año inválido")
                    return datetime.strptime(f"{anio}-{mes}-{dia}", '%Y-%m-%d').date()
                
                else:
                    raise ValueError("Formato de fecha no reconocido")
            
            else:
                raise ValueError(f"Tipo de dato no soportado para fecha: {type(fecha_nacimiento)}")
                
        except Exception as e:
            logger.warning(f"⚠️ Error al procesar fecha: {e}")
            raise
    
    def crear(self, nombre: str, apellidos: str, fecha_nacimiento,
              tipo_documento: str, num_documento: str,
              sexo: str = None, direccion: str = None,
              telefono: str = None, email: str = None) -> bool:
        """Crea un nuevo cliente con validaciones y formato de fecha flexible"""
        
        # Validaciones requeridas
        if not self.validar_requerido(nombre, "nombre"):
            return False
        if not self.validar_requerido(apellidos, "apellidos"):
            return False
        if not self.validar_requerido(tipo_documento, "tipo de documento"):
            return False
        if not self.validar_requerido(num_documento, "número de documento"):
            return False
        
        # Validaciones de longitud
        if not self.validar_longitud(nombre, "nombre", max_len=50):
            return False
        if not self.validar_longitud(apellidos, "apellidos", max_len=100):
            return False
        
        # Validar documento
        if not self.validar_documento(tipo_documento, num_documento):
            return False
        
        # Validación específica para Venezuela
        if tipo_documento.upper() in ['V', 'E']:
            # Es una cédula venezolana (persona natural)
            if not ValidacionVenezuela.validar_cedula(num_documento):
                logger.warning("⚠️ Cédula venezolana inválida")
                return False
        
        elif tipo_documento.upper() in ['J', 'G', 'C']:
            # Es un RIF de empresa, gobierno o consejo comunal
            rif_completo = f"{tipo_documento}-{num_documento}"
            if not ValidacionVenezuela.validar_rif(rif_completo):
                logger.warning("⚠️ RIF venezolano inválido")
                return False
        
        # Procesar fecha
        try:
            fecha_nacimiento = self._procesar_fecha(fecha_nacimiento)
        except Exception as e:
            print(f"\n❌ Fecha inválida. Use formato: DD/MM/YYYY (ej: 15/05/1990)")
            print(f"   También puede escribir: 15051990 (sin diagonales)")
            return False
        
        # Validar edad (mayor de edad)
        hoy = date.today()
        edad = hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))
        
        if edad < 18:
            logger.warning("⚠️ El cliente debe ser mayor de edad")
            return False
        
        # Validar email si se proporciona
        if email and not self.validar_email(email):
            return False
        
        # Validar teléfono si se proporciona
        if telefono and not self.validar_telefono(telefono):
            return False
        
        # Validar sexo
        if sexo and sexo not in ['M', 'F', 'O']:
            logger.warning("⚠️ Sexo debe ser M, F u O")
            return False
        
        try:
            return self.repositorio.insertar(
                nombre.strip(), apellidos.strip(), fecha_nacimiento,
                tipo_documento, num_documento, sexo, direccion, telefono, email
            )
        except Exception as e:
            logger.error(f"❌ Error al crear cliente: {e}")
            return False
    
    def actualizar(self, idcliente: int, nombre: str, apellidos: str, fecha_nacimiento,
                   tipo_documento: str, num_documento: str,
                   sexo: str = None, direccion: str = None,
                   telefono: str = None, email: str = None) -> bool:
        """Actualiza un cliente con validaciones (acepta fecha como string u objeto date)"""
        
        if not self.validar_entero_positivo(idcliente, "ID de cliente"):
            return False
        
        # Validaciones requeridas
        if not self.validar_requerido(nombre, "nombre"):
            return False
        if not self.validar_requerido(apellidos, "apellidos"):
            return False
        if not self.validar_requerido(tipo_documento, "tipo de documento"):
            return False
        if not self.validar_requerido(num_documento, "número de documento"):
            return False
        
        # Validar documento
        if not self.validar_documento(tipo_documento, num_documento):
            return False
        
        # Validación específica para Venezuela
        if tipo_documento.upper() in ['V', 'E']:
            if not ValidacionVenezuela.validar_cedula(num_documento):
                logger.warning("⚠️ Cédula venezolana inválida")
                return False
        
        elif tipo_documento.upper() in ['J', 'G', 'C']:
            rif_completo = f"{tipo_documento}-{num_documento}"
            if not ValidacionVenezuela.validar_rif(rif_completo):
                logger.warning("⚠️ RIF venezolano inválido")
                return False
        
        # Procesar fecha
        try:
            fecha_nacimiento = self._procesar_fecha(fecha_nacimiento)
        except Exception as e:
            print(f"\n❌ Fecha inválida. Use formato: DD/MM/YYYY (ej: 15/05/1990)")
            return False
        
        # Validar email si se proporciona
        if email and not self.validar_email(email):
            return False
        
        # Validar teléfono si se proporciona
        if telefono and not self.validar_telefono(telefono):
            return False
        
        # Validar sexo
        if sexo and sexo not in ['M', 'F', 'O']:
            logger.warning("⚠️ Sexo debe ser M, F u O")
            return False
        
        try:
            return self.repositorio.actualizar(
                idcliente, nombre.strip(), apellidos.strip(), fecha_nacimiento,
                tipo_documento, num_documento, sexo, direccion, telefono, email
            )
        except Exception as e:
            logger.error(f"❌ Error al actualizar cliente: {e}")
            return False
    
    def eliminar(self, idcliente: int) -> bool:
        """Elimina un cliente"""
        if not self.validar_entero_positivo(idcliente, "ID de cliente"):
            return False
        return self.repositorio.eliminar(idcliente)
