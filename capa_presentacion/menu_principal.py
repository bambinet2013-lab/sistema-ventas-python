#!/usr/bin/env python3
"""
Menú principal del sistema de ventas (Interfaz de consola)
"""
import os
import sys
import readchar
from datetime import datetime

# Añadir el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from capa_datos.conexion import ConexionDB
from capa_datos.categoria_repo import CategoriaRepositorio
from capa_datos.cliente_repo import ClienteRepositorio
from capa_datos.articulo_repo import ArticuloRepositorio
from capa_datos.proveedor_repo import ProveedorRepositorio
from capa_datos.trabajador_repo import TrabajadorRepositorio
from capa_datos.venta_repo import VentaRepositorio
from capa_datos.ingreso_repo import IngresoRepositorio
from capa_datos.lote_repo import LoteRepositorio
from capa_datos.rol_repo import RolRepositorio
from capa_datos.usuario_admin_repo import UsuarioAdminRepositorio
from capa_datos.proveedor_archivo_repo import ProveedorArchivoRepositorio

from capa_negocio.categoria_service import CategoriaService
from capa_negocio.cliente_service import ClienteService
from capa_negocio.articulo_service import ArticuloService
from capa_negocio.trabajador_service import TrabajadorService
from capa_negocio.venta_service import VentaService
from capa_negocio.rol_service import RolService, PermisoDenegadoError
from capa_negocio.base_service import BaseService
from capa_negocio.email_service import EmailService
from capa_negocio.usuario_admin_service import UsuarioAdminService
from capa_negocio.token_service import TokenService
from capa_negocio.proveedor_service import ProveedorService
from capa_negocio.validacion_venezuela import ValidacionVenezuela
from capa_negocio.inventario_service import InventarioService
from capa_negocio.ingreso_service import IngresoService
from capa_negocio.proveedor_archivo_service import ProveedorArchivoService
from capa_negocio.reporte_contable_service import ReporteContableService

# Importaciones para SENIAT y auditoría
from capa_datos.auditoria_repo import AuditoriaRepositorio
from capa_datos.tasa_repo import TasaRepositorio
from capa_negocio.auditoria_service import AuditoriaService
from config.seniat_config import SENIAT_CONFIG, TECLAS_ATAJO, MENSAJES_LEGALES

from capa_presentacion.decoradores import requiere_permiso
from capa_presentacion.input_con_mascara import leer_con_mascara

from loguru import logger

# Configurar logger
logger.remove()
logger.add(sys.stderr, format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

class SistemaVentas:
    """Clase principal del sistema"""
    
    # Colores para la terminal
    COLOR_ROJO = '\033[91m'
    COLOR_VERDE = '\033[92m'
    COLOR_AMARILLO = '\033[93m'
    COLOR_AZUL = '\033[94m'
    COLOR_MAGENTA = '\033[95m'
    COLOR_CYAN = '\033[96m'
    COLOR_NARANJA = '\033[38;5;208m'
    COLOR_RESET = '\033[0m'
    COLOR_NEGRITA = '\033[1m'
    
    def __init__(self):
        self.db = ConexionDB()
        self.conn = None
        self.trabajador_service = None
        self.categoria_service = None
        self.cliente_service = None
        self.articulo_service = None
        self.proveedor_service = None
        self.proveedor_archivo_service = None
        self.venta_service = None
        self.rol_service = None
        self.email_service = None
        self.usuario_admin_service = None
        self.token_service = None
        self.inventario_service = None
        self.ingreso_service = None
        self.auditoria_service = None
    
    def conectar_db(self):
        """Establece conexión con la base de datos"""
        self.conn = self.db.conectar()
        if not self.conn:
            print("❌ No se pudo conectar a la base de datos")
            return False
        
        # Inicializar repositorios
        trabajador_repo = TrabajadorRepositorio(self.conn)
        categoria_repo = CategoriaRepositorio(self.conn)
        cliente_repo = ClienteRepositorio(self.conn)
        articulo_repo = ArticuloRepositorio(self.conn)
        proveedor_repo = ProveedorRepositorio(self.conn)
        venta_repo = VentaRepositorio(self.conn)
        ingreso_repo = IngresoRepositorio(self.conn)
        rol_repo = RolRepositorio(self.conn)
        usuario_admin_repo = UsuarioAdminRepositorio(self.conn)
        proveedor_archivo_repo = ProveedorArchivoRepositorio(self.conn)
        
        # Inicializar repositorio de tasas
        from capa_datos.tasa_repo import TasaRepositorio
        tasa_repo = TasaRepositorio(self.conn)
        
        # Inicializar servicios base
        self.trabajador_service = TrabajadorService(trabajador_repo)
        self.categoria_service = CategoriaService(categoria_repo)
        self.cliente_service = ClienteService(cliente_repo)
        self.articulo_service = ArticuloService(articulo_repo, self.categoria_service)
        self.proveedor_service = ProveedorService(proveedor_repo)
        self.proveedor_archivo_service = ProveedorArchivoService(proveedor_archivo_repo, self.proveedor_service)
        
        # Inicializar inventario
        self.inventario_service = InventarioService(self.articulo_service)
        logger.info("✅ InventarioService inicializado")
        
        # Inicializar venta con soporte de tasas
        self.venta_service = VentaService(
            venta_repo, 
            self.cliente_service, 
            self.trabajador_service, 
            self.inventario_service,
            tasa_repo=tasa_repo
        )
        logger.info("✅ VentaService inicializado con soporte de tasas")
        
        self.ingreso_service = IngresoService(
            ingreso_repo, 
            self.articulo_service, 
            self.proveedor_service,
            self.trabajador_service
        )
        self.rol_service = RolService(rol_repo)
        self.usuario_admin_service = UsuarioAdminService(usuario_admin_repo, self.rol_service)
        self.token_service = TokenService(self.conn)
        
        self.trabajador_service.rol_service = self.rol_service
        
        self.email_service = EmailService(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            email_remitente="carlosberenguel554@gmail.com",
            password="fhnh tiax mfus fmok"
        )
        
        # Inicializar servicio de auditoría
        from capa_datos.auditoria_repo import AuditoriaRepositorio
        from capa_negocio.auditoria_service import AuditoriaService
        auditoria_repo = AuditoriaRepositorio(self.conn)
        self.auditoria_service = AuditoriaService(auditoria_repo)
        logger.info("✅ Servicio de auditoría inicializado")
        
        # Inicializar servicio de reportes contables
        from capa_negocio.reporte_contable_service import ReporteContableService
        self.reporte_service = ReporteContableService(
            self.venta_service,
            self.inventario_service
        )
        logger.info("✅ ReporteContableService inicializado")
        
        return True
    
    def limpiar_pantalla(self):
        """Limpia la pantalla de la consola"""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def pausa(self):
        """Pausa la ejecución hasta que el usuario presione Enter"""
        input(f"\n{self.COLOR_AMARILLO}🔹 Presione Enter para continuar...{self.COLOR_RESET}")
    
    def obtener_tasas_actuales(self):
        """
        Obtiene las tasas de cambio actuales del sistema
        Returns:
            dict: Diccionario con tasas de USD y EUR
        """
        tasas = {'USD': None, 'EUR': None}
        
        try:
            # Intentar obtener tasas desde el servicio de ventas
            if hasattr(self, 'venta_service') and self.venta_service and hasattr(self.venta_service, 'tasa_service'):
                if self.venta_service.tasa_service:
                    tasas['USD'] = self.venta_service.tasa_service.obtener_tasa_del_dia('USD')
                    tasas['EUR'] = self.venta_service.tasa_service.obtener_tasa_del_dia('EUR')
            else:
                # Fallback: consulta directa a BD
                if hasattr(self, 'conn') and self.conn:
                    tasa_repo = TasaRepositorio(self.conn)
                    tasas['USD'] = tasa_repo.obtener_ultima_tasa('USD')
                    tasas['EUR'] = tasa_repo.obtener_ultima_tasa('EUR')
        except Exception as e:
            logger.error(f"Error obteniendo tasas para menú: {e}")
        
        return tasas

    def obtener_fecha_hora_actual(self):
        """
        Retorna la fecha y hora actual formateada
        Returns:
            tuple: (dia_semana, fecha, hora)
        """
        ahora = datetime.now()
        dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        dia_semana = dias_semana[ahora.weekday()]
        fecha = ahora.strftime("%d/%m/%Y")
        hora = ahora.strftime("%I:%M:%S %p")
        return dia_semana, fecha, hora

    def registrar_auditoria(self, accion, tabla, registro_id, datos_anteriores=None, datos_nuevos=None):
        """
        Registra una acción en el log de auditoría
        """
        try:
            usuario_actual = self.trabajador_service.get_usuario_actual()
            if usuario_actual:
                usuario_nombre = f"{usuario_actual['nombre']} {usuario_actual['apellidos']}"
            else:
                usuario_nombre = "SISTEMA"
            
            if self.auditoria_service:
                self.auditoria_service.registrar(
                    usuario=usuario_nombre,
                    accion=accion,
                    tabla=tabla,
                    registro_id=registro_id,
                    datos_anteriores=datos_anteriores,
                    datos_nuevos=datos_nuevos
                )
        except Exception as e:
            logger.error(f"Error registrando auditoría: {e}")
    
    def mostrar_cabecera(self, titulo):
        """Muestra una cabecera formateada con color"""
        self.limpiar_pantalla()
        print(f"{self.COLOR_AZUL}{'=' * 60}{self.COLOR_RESET}")
        print(f"{self.COLOR_NEGRITA}{titulo:^60}{self.COLOR_RESET}")
        print(f"{self.COLOR_AZUL}{'=' * 60}{self.COLOR_RESET}")
        print()
    
    def mostrar_menu_principal(self):
        """Muestra el menú principal con fecha, hora, tasas de cambio y colores"""
        self.limpiar_pantalla()
        
        dia_semana, fecha, hora = self.obtener_fecha_hora_actual()
        
        # Obtener tasas de cambio
        tasas = self.obtener_tasas_actuales()
        
        # Línea superior
        print(f"{self.COLOR_AZUL}╔" + "═" * 78 + f"╗{self.COLOR_RESET}")
        
        # Título centrado
        titulo = "SISTEMA DE VENTAS - 3 CAPAS"
        espacios_izq = (78 - len(titulo)) // 2
        espacios_der = 78 - len(titulo) - espacios_izq
        print(f"{self.COLOR_AZUL}║{self.COLOR_RESET}{' ' * espacios_izq}{self.COLOR_NEGRITA}{titulo}{self.COLOR_RESET}{' ' * espacios_der}{self.COLOR_AZUL}║{self.COLOR_RESET}")
        
        # Línea separadora
        print(f"{self.COLOR_AZUL}╠" + "═" * 78 + f"╣{self.COLOR_RESET}")
        
        # Fecha y hora
        fecha_hora_str = f"   {self.COLOR_VERDE}📅 {dia_semana}, {fecha}{self.COLOR_RESET}  {self.COLOR_AMARILLO}⏰ {hora}{self.COLOR_RESET}  {self.COLOR_NARANJA}🇻🇪 Hora Local{self.COLOR_RESET}"
        print(f"{self.COLOR_AZUL}║{self.COLOR_RESET}{fecha_hora_str:<78}{self.COLOR_AZUL}║{self.COLOR_RESET}")
        
        # Línea separadora
        print(f"{self.COLOR_AZUL}╠" + "═" * 78 + f"╣{self.COLOR_RESET}")
        
        # Tasas de cambio
        linea_tasas = f"   {self.COLOR_AMARILLO}💱 TASAS DEL DÍA:{self.COLOR_RESET}"
        print(f"{self.COLOR_AZUL}║{self.COLOR_RESET}{linea_tasas:<78}{self.COLOR_AZUL}║{self.COLOR_RESET}")
        
        if tasas['USD']:
            linea_usd = f"      {self.COLOR_VERDE}💵 USD:{self.COLOR_RESET} 1 = {self.COLOR_AMARILLO}Bs. {tasas['USD']:.2f}{self.COLOR_RESET}"
        else:
            linea_usd = f"      {self.COLOR_VERDE}💵 USD:{self.COLOR_RESET} {self.COLOR_ROJO}No registrada{self.COLOR_RESET}"
        
        if tasas['EUR']:
            linea_eur = f"      {self.COLOR_VERDE}💶 EUR:{self.COLOR_RESET} 1 = {self.COLOR_AMARILLO}Bs. {tasas['EUR']:.2f}{self.COLOR_RESET}"
        else:
            linea_eur = f"      {self.COLOR_VERDE}💶 EUR:{self.COLOR_RESET} {self.COLOR_ROJO}No registrada{self.COLOR_RESET}"
        
        print(f"{self.COLOR_AZUL}║{self.COLOR_RESET}{linea_usd:<78}{self.COLOR_AZUL}║{self.COLOR_RESET}")
        print(f"{self.COLOR_AZUL}║{self.COLOR_RESET}{linea_eur:<78}{self.COLOR_AZUL}║{self.COLOR_RESET}")
        
        # NUEVA OPCIÓN PARA MODIFICAR TASAS
        print(f"{self.COLOR_AZUL}║{self.COLOR_RESET}      {self.COLOR_AMARILLO}[X]{self.COLOR_RESET} Modificar tasas de cambio{' ' * 54}{self.COLOR_AZUL}║{self.COLOR_RESET}")
        
        # Línea separadora
        print(f"{self.COLOR_AZUL}╠" + "═" * 78 + f"╣{self.COLOR_RESET}")
        
        # Información de usuario
        usuario = self.trabajador_service.get_usuario_actual()
        if usuario:
            rol_nombre = "Sin rol"
            if usuario.get('idrol'):
                rol = self.rol_service.repositorio.obtener_rol(usuario['idrol'])
                if rol:
                    rol_nombre = rol['nombre']
            
            usuario_str = f"   👤 Usuario: {self.COLOR_VERDE}{usuario['nombre']} {usuario['apellidos']} [{rol_nombre}]{self.COLOR_RESET}"
            permisos_str = f"   🔑 Permisos: {self.COLOR_AMARILLO}{len(self.rol_service.get_permisos_usuario())} activos{self.COLOR_RESET}"
            
            print(f"{self.COLOR_AZUL}║{self.COLOR_RESET}{usuario_str:<78}{self.COLOR_AZUL}║{self.COLOR_RESET}")
            print(f"{self.COLOR_AZUL}║{self.COLOR_RESET}{permisos_str:<78}{self.COLOR_AZUL}║{self.COLOR_RESET}")
        else:
            usuario_str = f"   👤 Usuario: {self.COLOR_AMARILLO}No autenticado{self.COLOR_RESET}"
            print(f"{self.COLOR_AZUL}║{self.COLOR_RESET}{usuario_str:<78}{self.COLOR_AZUL}║{self.COLOR_RESET}")
        
        # Línea separadora
        print(f"{self.COLOR_AZUL}╠" + "═" * 78 + f"╣{self.COLOR_RESET}")
        
        # Título del menú
        menu_titulo = "MENÚ PRINCIPAL"
        espacios_izq_menu = (78 - len(menu_titulo)) // 2
        espacios_der_menu = 78 - len(menu_titulo) - espacios_izq_menu
        print(f"{self.COLOR_AZUL}║{self.COLOR_RESET}{' ' * espacios_izq_menu}{self.COLOR_NEGRITA}{menu_titulo}{self.COLOR_RESET}{' ' * espacios_der_menu}{self.COLOR_AZUL}║{self.COLOR_RESET}")
        
        # Línea separadora
        print(f"{self.COLOR_AZUL}╠" + "═" * 78 + f"╣{self.COLOR_RESET}")
        
        # Opciones del menú
        opciones = []
        
        if not usuario or self.rol_service.tiene_permiso('clientes_ver'):
            opciones.append(("1", "Gestión de Clientes", "👥"))
        if not usuario or self.rol_service.tiene_permiso('articulos_ver'):
            opciones.append(("2", "Gestión de Artículos", "📦"))
        if not usuario or self.rol_service.tiene_permiso('proveedores_ver'):
            opciones.append(("3", "Gestión de Proveedores", "🏢"))
        if not usuario or self.rol_service.tiene_permiso('ventas_ver'):
            opciones.append(("4", "Gestión de Ventas", "💰"))
        if not usuario or self.rol_service.tiene_permiso('inventario_ver'):
            opciones.append(("5", "Gestión de Inventario", "📊"))
        if not usuario or self.rol_service.tiene_permiso('reportes_ventas'):
            opciones.append(("6", "Reportes Contables", "📈"))
        if usuario and self.rol_service.tiene_permiso('usuarios_ver'):
            opciones.append(("7", "Administración de Usuarios", "👤"))
        
        for num, desc, icono in opciones:
            linea_opcion = f"   {icono} {num}. {desc}"
            espacios = 78 - len(linea_opcion)
            print(f"{self.COLOR_AZUL}║{self.COLOR_RESET}{linea_opcion}{' ' * espacios}{self.COLOR_AZUL}║{self.COLOR_RESET}")
        
        # Línea separadora
        print(f"{self.COLOR_AZUL}╠" + "═" * 78 + f"╣{self.COLOR_RESET}")
        
        # Opción de sesión
        if usuario:
            linea_sesion = f"   🔑 8. Cerrar Sesión"
        else:
            linea_sesion = f"   🔑 8. Iniciar Sesión"
        espacios_sesion = 78 - len(linea_sesion)
        print(f"{self.COLOR_AZUL}║{self.COLOR_RESET}{linea_sesion}{' ' * espacios_sesion}{self.COLOR_AZUL}║{self.COLOR_RESET}")
        
        # Opción de salir
        linea_salir = f"   ❌ 0. Salir"
        espacios_salir = 78 - len(linea_salir)
        print(f"{self.COLOR_AZUL}║{self.COLOR_RESET}{linea_salir}{' ' * espacios_salir}{self.COLOR_AZUL}║{self.COLOR_RESET}")
        
        # Línea inferior
        print(f"{self.COLOR_AZUL}╚" + "═" * 78 + f"╝{self.COLOR_RESET}")
        print()
        
        return input(f"{self.COLOR_AMARILLO}🔹 Seleccione una opción: {self.COLOR_RESET}").strip()
        
        return input(f"{self.COLOR_AMARILLO}🔹 Seleccione una opción: {self.COLOR_RESET}").strip()

    def menu_login(self):
        """Menú de inicio de sesión con opción de recuperación"""
        while True:
            self.mostrar_cabecera("INICIAR SESIÓN")
            
            print("1. Iniciar sesión")
            print("2. ¿Olvidaste tu contraseña?")
            print("0. Volver")
            print()
            
            opcion = input(f"{self.COLOR_AMARILLO}🔹 Seleccione una opción: {self.COLOR_RESET}").strip()
            
            if opcion == '1':
                self._login_normal()
                break
            elif opcion == '2':
                self._recuperar_contraseña()
            elif opcion == '0':
                break
            else:
                print("❌ Opción no válida")
                self.pausa()
    
    def _login_normal(self):
        """Login normal con email y contraseña"""
        self.mostrar_cabecera("INICIAR SESIÓN POR EMAIL")
        
        print("🔐 Ingrese sus credenciales")
        print()
        email = input("Email: ")
        password = input("Contraseña: ")
        
        if self.trabajador_service.login_por_email(email, password):
            print(f"{self.COLOR_VERDE}✅ Sesión iniciada correctamente{self.COLOR_RESET}")
            self.registrar_auditoria(
                accion="LOGIN",
                tabla="trabajador",
                registro_id=self.trabajador_service.get_usuario_actual()['idtrabajador'],
                datos_nuevos=f"Login exitoso - Email: {email}"
            )
        else:
            print(f"{self.COLOR_ROJO}❌ Email o contraseña incorrectos{self.COLOR_RESET}")
        
        self.pausa()
    
    def _recuperar_contraseña(self):
        """Proceso de recuperación con enlace mágico"""
        while True:
            self.mostrar_cabecera("RECUPERAR CONTRASEÑA")
            
            print("1. Solicitar enlace mágico por email")
            print("2. Ya tengo un token, ingresar manualmente")
            print("0. Volver")
            print()
            
            opcion = input(f"{self.COLOR_AMARILLO}🔹 Seleccione una opción: {self.COLOR_RESET}").strip()
            
            if opcion == '1':
                self._solicitar_enlace_magico()
            elif opcion == '2':
                self._ingresar_token_manual()
            elif opcion == '0':
                break
            else:
                print("❌ Opción no válida")
                self.pausa()
    
    def _solicitar_enlace_magico(self):
        """Solicita un enlace mágico por email"""
        self.mostrar_cabecera("SOLICITAR ENLACE MÁGICO")
        
        email = input("Ingrese su email registrado: ")
        
        usuario = self.trabajador_service.buscar_por_email(email)
        
        if not usuario:
            print("❌ No existe un usuario con ese email")
            self.pausa()
            return
        
        print(f"\n👤 Usuario encontrado: {usuario['nombre']} {usuario['apellidos']}")
        print(f"📧 Email: {usuario['email']}")
        print()
        
        token = self.token_service.crear_token(usuario['idtrabajador'])
        
        if token:
            if self.email_service.enviar_enlace_magico(
                email, token, usuario['nombre']
            ):
                print(f"✅ Se ha enviado un enlace mágico a:")
                print(f"   {email}")
                print(f"\n📧 Revisa tu bandeja de entrada (y carpeta SPAM)")
                print(f"⏰ El enlace expirará en 30 minutos")
                print(f"\n📝 Si no recibes el correo, usa la opción 2 para ingresar manualmente:")
                print(f"   Token: {token}")
                
                self.registrar_auditoria(
                    accion="RECUPERAR_CONTRASEÑA",
                    tabla="trabajador",
                    registro_id=usuario['idtrabajador'],
                    datos_nuevos=f"Token enviado a: {email}"
                )
            else:
                print("❌ Error al enviar el correo")
                print(f"\n📝 Para pruebas, usa este token manualmente:")
                print(f"   {token}")
        else:
            print("❌ Error al generar el token")
        
        self.pausa()
    
    def _ingresar_token_manual(self):
        """Permite ingresar un token manualmente para restablecer contraseña"""
        self.mostrar_cabecera("INGRESAR TOKEN MANUAL")
        
        token = input("Ingrese el token recibido: ").strip()
        
        idtrabajador = self.token_service.verificar_token(token)
        
        if idtrabajador:
            usuario = self.trabajador_service.obtener_por_id(idtrabajador)
            print(f"\n✅ Token válido para: {usuario['nombre']} {usuario['apellidos']}")
            
            print("\n" + "="*50)
            print("🔑 CAMBIO DE CONTRASEÑA")
            print("="*50)
            print()
            
            logger.remove()
            logger.add(lambda msg: None)
            
            try:
                nueva_pass = input("➤ Ingrese NUEVA contraseña (mínimo 6 caracteres): ")
                confirmar = input("➤ Confirme la NUEVA contraseña: ")
            finally:
                logger.remove()
                logger.add(sys.stderr, format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
            
            if nueva_pass == confirmar and len(nueva_pass) >= 6:
                if self.trabajador_service.actualizar_password(usuario['email'], nueva_pass):
                    self.token_service.marcar_token_usado(token)
                    print("\n✅ Contraseña actualizada correctamente")
                    print("🔐 Ya puede iniciar sesión con su nueva contraseña")
                    
                    self.registrar_auditoria(
                        accion="CAMBIAR_CONTRASEÑA",
                        tabla="trabajador",
                        registro_id=idtrabajador,
                        datos_nuevos="Contraseña actualizada mediante recuperación"
                    )
                else:
                    print("\n❌ Error al actualizar la contraseña")
            else:
                print("\n❌ Las contraseñas no coinciden o son muy cortas")
        else:
            print("\n❌ Token inválido o expirado")
        
        self.pausa()
    
    @requiere_permiso('usuarios_ver')
    def menu_administracion_usuarios(self):
        """Menú de administración de usuarios"""
        while True:
            self.mostrar_cabecera("ADMINISTRACIÓN DE USUARIOS")
            print("1. Listar usuarios")
            print("2. Crear nuevo usuario")
            print("3. Ver detalle de usuario")
            print("4. Editar usuario")
            print("5. Eliminar usuario")
            print("0. Volver")
            print()
            
            opcion = input(f"{self.COLOR_AMARILLO}🔹 Seleccione una opción: {self.COLOR_RESET}").strip()
            
            if opcion == '1':
                self._listar_usuarios()
            elif opcion == '2':
                self._crear_usuario()
            elif opcion == '3':
                self._ver_usuario()
            elif opcion == '4':
                self._editar_usuario()
            elif opcion == '5':
                self._eliminar_usuario()
            elif opcion == '0':
                break
            else:
                print("❌ Opción no válida")
                self.pausa()
    
    def _listar_usuarios(self):
        """Lista todos los usuarios"""
        self.mostrar_cabecera("LISTADO DE USUARIOS")
        
        usuarios = self.usuario_admin_service.listar_usuarios()
        
        if not usuarios:
            print("📭 No hay usuarios registrados")
        else:
            print(f"{'ID':<5} {'USUARIO':<15} {'NOMBRE':<25} {'EMAIL':<30} {'ROL':<15}")
            print("-" * 90)
            for u in usuarios:
                rol = u.get('rol_nombre') or f"Rol {u['idrol']}"
                email_val = u.get('email', '') or ''
                print(f"{u['idtrabajador']:<5} {u['usuario']:<15} {u['nombre'] + ' ' + u['apellidos']:<25} {email_val:<30} {rol:<15}")
        
        self.pausa()
    
    def _crear_usuario(self):
        """Crea un nuevo usuario del sistema"""
        self.mostrar_cabecera("CREAR NUEVO USUARIO")
        
        print("📝 Complete los datos del nuevo usuario:")
        print()
        
        nombre = input("Nombre: ")
        apellidos = input("Apellidos: ")
        sexo = input("Sexo (M/F/O): ").upper()
        
        print("\n📅 Fecha de nacimiento (OPCIONAL - presione Enter para omitir)")
        print("   Formato: DD/MM/YYYY (ej: 15/05/1990)")
        
        while True:
            fecha_nac_str = input("Fecha de nacimiento: ").strip()
            
            if fecha_nac_str == "":
                fecha_nac = None
                break
            
            valida, fecha_obj, mensaje = ValidacionVenezuela.validar_fecha(fecha_nac_str)
            
            if valida:
                fecha_nac = fecha_obj
                break
            else:
                print(mensaje)
                print("   Intente nuevamente o presione Enter para omitir:")
        
        print("\n" + "="*60)
        print("🔍 TIPO DE DOCUMENTO DEL USUARIO")
        print("="*60)
        print("1. 🇻🇪 Venezolano (V) → V12345678")
        print("2. 🌎 Extranjero (E) → E87654321")
        print("3. 🛂 Pasaporte → número de pasaporte")
        print("="*60)
        
        tipo_persona = input("Seleccione tipo de documento (1-3): ").strip()
        
        if tipo_persona == '1':
            tipo_doc = 'V'
            print("\n✅ Seleccionó: Venezolano (V)")
            print("📝 Formato requerido: V + 8 dígitos")
            print("   Ejemplo: V12345678")
            num_doc = input("Documento completo: ").upper()
            
            if not num_doc.startswith('V'):
                print("❌ El documento debe comenzar con 'V'")
                self.pausa()
                return
            documento_completo = num_doc
            
        elif tipo_persona == '2':
            tipo_doc = 'E'
            print("\n✅ Seleccionó: Extranjero (E)")
            print("📝 Formato requerido: E + 8 dígitos")
            print("   Ejemplo: E87654321")
            num_doc = input("Documento completo: ").upper()
            
            if not num_doc.startswith('E'):
                print("❌ El documento debe comenzar con 'E'")
                self.pausa()
                return
            documento_completo = num_doc
            
        elif tipo_persona == '3':
            tipo_doc = 'PASAPORTE'
            print("\n✅ Seleccionó: Pasaporte")
            print("📝 Ingrese número de pasaporte (6-12 caracteres)")
            print("   Ejemplo: ABC123456")
            documento_completo = input("Pasaporte: ").upper()
            
        else:
            print("❌ Opción no válida")
            self.pausa()
            return
        
        usuario = input("Nombre de usuario: ")
        password = input("Contraseña (mínimo 6 caracteres): ")
        email = input("Email: ")
        telefono = input("Teléfono (opcional): ") or None
        direccion = input("Dirección (opcional): ") or None
        
        print("\nRoles disponibles:")
        roles = self.rol_service.listar_roles()
        for r in roles:
            print(f"  {r['idrol']}. {r['nombre']}")
        
        try:
            idrol = int(input("\nID del rol: "))
        except:
            print("❌ Rol inválido")
            self.pausa()
            return
        
        fecha_nac_bd = ValidacionVenezuela.formatear_fecha_para_bd(fecha_nac) if fecha_nac else None
        
        if self.usuario_admin_service.crear_usuario(
            nombre, apellidos, sexo, fecha_nac_bd, documento_completo,
            usuario, password, email, idrol, direccion, telefono
        ):
            print("\n✅ Usuario creado exitosamente")
            if not fecha_nac:
                print("   ℹ️ Fecha de nacimiento no registrada")
            
            self.registrar_auditoria(
                accion="CREAR",
                tabla="trabajador",
                registro_id=self.trabajador_service.buscar_por_email(email)['idtrabajador'],
                datos_nuevos=f"Usuario: {usuario}, Email: {email}"
            )
        else:
            print("\n❌ Error al crear el usuario")
        
        self.pausa()
    
    def _ver_usuario(self):
        """Muestra detalle de un usuario"""
        self.mostrar_cabecera("DETALLE DE USUARIO")
        
        try:
            iduser = int(input("ID del usuario: "))
            usuario = self.usuario_admin_service.obtener_usuario(iduser)
            
            if usuario:
                print(f"\n📌 ID: {usuario['idtrabajador']}")
                print(f"📌 Nombre: {usuario['nombre']} {usuario['apellidos']}")
                print(f"📌 Sexo: {usuario['sexo']}")
                print(f"📌 Fecha Nac.: {usuario['fecha_nacimiento'] or 'No registrada'}")
                print(f"📌 Documento: {usuario['num_documento']}")
                print(f"📌 Usuario: {usuario['usuario']}")
                print(f"📌 Email: {usuario['email']}")
                print(f"📌 Teléfono: {usuario.get('telefono', 'No registrado')}")
                print(f"📌 Dirección: {usuario.get('direccion', 'No registrada')}")
                print(f"📌 Rol: {usuario.get('rol_nombre')} (ID: {usuario['idrol']})")
                
                print("\n📋 ÚLTIMAS ACCIONES DE AUDITORÍA:")
                logs = self.auditoria_service.consultar_por_tabla("trabajador", iduser)
                for log in logs[:5]:
                    print(f"   - {log['fecha_hora']}: {log['accion']}")
            else:
                print(f"❌ No existe usuario con ID {iduser}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        self.pausa()
    
    def _editar_usuario(self):
        """Edita un usuario existente"""
        self.mostrar_cabecera("EDITAR USUARIO")
        
        try:
            iduser = int(input("ID del usuario a editar: "))
            usuario = self.usuario_admin_service.obtener_usuario(iduser)
            
            if not usuario:
                print(f"❌ No existe usuario con ID {iduser}")
                self.pausa()
                return
            
            datos_anteriores = f"Usuario: {usuario['usuario']}, Email: {usuario['email']}, Rol: {usuario['idrol']}"
            
            print(f"\nEditando a: {usuario['nombre']} {usuario['apellidos']}")
            print("(Deje en blanco para mantener el valor actual)")
            print()
            
            nombre = input(f"Nombre [{usuario['nombre']}]: ") or usuario['nombre']
            apellidos = input(f"Apellidos [{usuario['apellidos']}]: ") or usuario['apellidos']
            sexo = input(f"Sexo [{usuario['sexo']}]: ").upper() or usuario['sexo']
            
            fecha_actual = usuario['fecha_nacimiento']
            fecha_actual_str = fecha_actual.strftime('%d/%m/%Y') if fecha_actual else "No registrada"
            
            print(f"\n📅 Fecha de nacimiento actual: {fecha_actual_str}")
            print("   (Enter para mantener, 'NUEVA' para cambiar, 'BORRAR' para eliminar)")
            
            while True:
                opcion_fecha = input("Opción: ").strip().upper()
                
                if opcion_fecha == "":
                    fecha_nac = fecha_actual
                    break
                elif opcion_fecha == "BORRAR":
                    fecha_nac = None
                    print("✅ Fecha de nacimiento eliminada")
                    break
                elif opcion_fecha == "NUEVA":
                    print("Ingrese nueva fecha (DD/MM/YYYY) o Enter para cancelar:")
                    nueva_fecha = input("Nueva fecha: ").strip()
                    
                    if nueva_fecha == "":
                        fecha_nac = fecha_actual
                        break
                    
                    valida, fecha_obj, mensaje = ValidacionVenezuela.validar_fecha(nueva_fecha)
                    if valida:
                        fecha_nac = fecha_obj
                        break
                    else:
                        print(mensaje)
                else:
                    print("Opción no válida. Use Enter, NUEVA o BORRAR")
            
            documento = input(f"Documento [{usuario['num_documento']}]: ") or usuario['num_documento']
            username = input(f"Usuario [{usuario['usuario']}]: ") or usuario['usuario']
            email = input(f"Email [{usuario['email']}]: ") or usuario['email']
            telefono = input(f"Teléfono [{usuario.get('telefono', '')}]: ") or usuario.get('telefono')
            direccion = input(f"Dirección [{usuario.get('direccion', '')}]: ") or usuario.get('direccion')
            
            cambiar_pass = input("¿Cambiar contraseña? (s/N): ").lower()
            nueva_pass = None
            if cambiar_pass == 's':
                nueva_pass = input("Nueva contraseña: ")
                confirmar = input("Confirmar contraseña: ")
                if nueva_pass != confirmar:
                    print("❌ Las contraseñas no coinciden")
                    self.pausa()
                    return
            
            print("\nRoles disponibles:")
            roles = self.rol_service.listar_roles()
            for r in roles:
                print(f"  {r['idrol']}. {r['nombre']}")
            
            try:
                idrol = int(input(f"\nID del rol [{usuario['idrol']}]: ") or usuario['idrol'])
            except:
                idrol = usuario['idrol']
            
            fecha_nac_bd = ValidacionVenezuela.formatear_fecha_para_bd(fecha_nac) if fecha_nac else None
            
            if self.usuario_admin_service.actualizar_usuario(
                iduser, nombre, apellidos, sexo, fecha_nac_bd, documento,
                username, email, idrol, direccion, telefono, nueva_pass
            ):
                print("✅ Usuario actualizado correctamente")
                
                datos_nuevos = f"Usuario: {username}, Email: {email}, Rol: {idrol}"
                self.registrar_auditoria(
                    accion="MODIFICAR",
                    tabla="trabajador",
                    registro_id=iduser,
                    datos_anteriores=datos_anteriores,
                    datos_nuevos=datos_nuevos
                )
            else:
                print("❌ Error al actualizar el usuario")
        
        except Exception as e:
            print(f"❌ Error: {e}")
        
        self.pausa()
    
    def _eliminar_usuario(self):
        """Elimina un usuario"""
        self.mostrar_cabecera("ELIMINAR USUARIO")
        
        try:
            iduser = int(input("ID del usuario a eliminar: "))
            
            usuario_actual = self.trabajador_service.get_usuario_actual()
            if usuario_actual and usuario_actual['idtrabajador'] == iduser:
                print("❌ No puede eliminarse a sí mismo")
                self.pausa()
                return
            
            usuario = self.usuario_admin_service.obtener_usuario(iduser)
            if not usuario:
                print(f"❌ No existe usuario con ID {iduser}")
                self.pausa()
                return
            
            datos_usuario = f"Usuario: {usuario['usuario']}, Email: {usuario['email']}"
            
            print(f"\n¿Está seguro de eliminar a {usuario['nombre']} {usuario['apellidos']}?")
            confirmacion = input("Esta acción no se puede deshacer (escriba 'ELIMINAR' para confirmar): ")
            
            if confirmacion == 'ELIMINAR':
                if self.usuario_admin_service.eliminar_usuario(iduser):
                    print("✅ Usuario eliminado correctamente")
                    
                    self.registrar_auditoria(
                        accion="ELIMINAR",
                        tabla="trabajador",
                        registro_id=iduser,
                        datos_anteriores=datos_usuario
                    )
                else:
                    print("❌ Error al eliminar el usuario")
            else:
                print("Operación cancelada")
        
        except Exception as e:
            print(f"❌ Error: {e}")
        
        self.pausa()
    
    def menu_categorias(self):
        """Menú de gestión de categorías"""
        while True:
            self.mostrar_cabecera("GESTIÓN DE CATEGORÍAS")
            print("1. Listar categorías")
            print("2. Buscar categoría por ID")
            print("3. Crear categoría")
            print("4. Actualizar categoría")
            print("5. Eliminar categoría")
            print("0. Volver")
            print()
            
            opcion = input(f"{self.COLOR_AMARILLO}🔹 Seleccione una opción: {self.COLOR_RESET}").strip()
            
            if opcion == '1':
                self.listar_categorias()
            elif opcion == '2':
                self.buscar_categoria()
            elif opcion == '3':
                self.crear_categoria()
            elif opcion == '4':
                self.actualizar_categoria()
            elif opcion == '5':
                self.eliminar_categoria()
            elif opcion == '0':
                break
            else:
                print("❌ Opción no válida")
                self.pausa()
    
    def listar_categorias(self):
        """Lista todas las categorías"""
        self.mostrar_cabecera("LISTADO DE CATEGORÍAS")
        
        categorias = self.categoria_service.listar()
        
        if not categorias:
            print("📭 No hay categorías registradas")
        else:
            print(f"{'ID':<5} {'NOMBRE':<30} {'DESCRIPCIÓN':<40}")
            print("-" * 75)
            for cat in categorias:
                desc = cat['descripcion'][:37] + "..." if cat['descripcion'] and len(cat['descripcion']) > 40 else cat['descripcion'] or ""
                print(f"{cat['idcategoria']:<5} {cat['nombre']:<30} {desc:<40}")
        
        self.pausa()
    
    def buscar_categoria(self):
        """Busca una categoría por ID"""
        self.mostrar_cabecera("BUSCAR CATEGORÍA")
        
        try:
            idcategoria = int(input("Ingrese ID de categoría: "))
            categoria = self.categoria_service.obtener_por_id(idcategoria)
            
            if categoria:
                print(f"\n📌 ID: {categoria['idcategoria']}")
                print(f"📌 Nombre: {categoria['nombre']}")
                print(f"📌 Descripción: {categoria['descripcion'] or 'Sin descripción'}")
            else:
                print(f"❌ No existe categoría con ID {idcategoria}")
        except ValueError:
            print("❌ Debe ingresar un número válido")
        
        self.pausa()
    
    def crear_categoria(self):
        """Crea una nueva categoría"""
        self.mostrar_cabecera("CREAR CATEGORÍA")
        
        nombre = input("Ingrese nombre de categoría: ")
        descripcion = input("Ingrese descripción (opcional): ") or None
        
        if self.categoria_service.crear(nombre, descripcion):
            print("✅ Categoría creada exitosamente")
            
            categorias = self.categoria_service.listar()
            if categorias:
                idcategoria = categorias[0]['idcategoria']
                self.registrar_auditoria(
                    accion="CREAR",
                    tabla="categoria",
                    registro_id=idcategoria,
                    datos_nuevos=f"Categoría: {nombre}"
                )
        else:
            print("❌ No se pudo crear la categoría")
        
        self.pausa()
    
    def actualizar_categoria(self):
        """Actualiza una categoría"""
        self.mostrar_cabecera("ACTUALIZAR CATEGORÍA")
        
        try:
            idcategoria = int(input("Ingrese ID de categoría a actualizar: "))
            categoria = self.categoria_service.obtener_por_id(idcategoria)
            
            if not categoria:
                print(f"❌ No existe categoría con ID {idcategoria}")
                self.pausa()
                return
            
            datos_anteriores = f"Categoría: {categoria['nombre']}"
            
            print(f"\n📌 Datos actuales:")
            print(f"   Nombre: {categoria['nombre']}")
            print(f"   Descripción: {categoria['descripcion'] or 'Sin descripción'}")
            print()
            
            nombre = input("Nuevo nombre (Enter para mantener): ") or categoria['nombre']
            descripcion = input("Nueva descripción (Enter para mantener): ") or categoria['descripcion']
            
            if self.categoria_service.actualizar(idcategoria, nombre, descripcion):
                print("✅ Categoría actualizada exitosamente")
                
                self.registrar_auditoria(
                    accion="MODIFICAR",
                    tabla="categoria",
                    registro_id=idcategoria,
                    datos_anteriores=datos_anteriores,
                    datos_nuevos=f"Categoría: {nombre}"
                )
            else:
                print("❌ No se pudo actualizar la categoría")
        except ValueError:
            print("❌ Debe ingresar un número válido")
        
        self.pausa()
    
    def eliminar_categoria(self):
        """Elimina una categoría"""
        self.mostrar_cabecera("ELIMINAR CATEGORÍA")
        
        try:
            idcategoria = int(input("Ingrese ID de categoría a eliminar: "))
            categoria = self.categoria_service.obtener_por_id(idcategoria)
            
            if not categoria:
                print(f"❌ No existe categoría con ID {idcategoria}")
                self.pausa()
                return
            
            datos_categoria = f"Categoría: {categoria['nombre']}"
            
            confirmacion = input(f"¿Está seguro de eliminar la categoría {idcategoria}? (s/N): ")
            if confirmacion.lower() == 's':
                if self.categoria_service.eliminar(idcategoria):
                    print("✅ Categoría eliminada exitosamente")
                    
                    self.registrar_auditoria(
                        accion="ELIMINAR",
                        tabla="categoria",
                        registro_id=idcategoria,
                        datos_anteriores=datos_categoria
                    )
                else:
                    print("❌ No se pudo eliminar la categoría (puede tener artículos asociados)")
            else:
                print("Operación cancelada")
        except ValueError:
            print("❌ Debe ingresar un número válido")
        
        self.pausa()
    
    def menu_clientes(self):
        """Menú de gestión de clientes"""
        while True:
            self.mostrar_cabecera("GESTIÓN DE CLIENTES")
            print("1. Listar clientes")
            print("2. Buscar cliente")
            print("3. Crear cliente")
            print("4. Editar cliente")
            print("5. Eliminar cliente")
            print("0. Volver")
            print()
            
            opcion = input(f"{self.COLOR_AMARILLO}🔹 Seleccione una opción: {self.COLOR_RESET}").strip()
            
            if opcion == '1':
                self._listar_clientes()
            elif opcion == '2':
                self._buscar_cliente()
            elif opcion == '3':
                self._crear_cliente()
            elif opcion == '4':
                self._editar_cliente()
            elif opcion == '5':
                self._eliminar_cliente()
            elif opcion == '0':
                break
            else:
                print("❌ Opción no válida")
                self.pausa()
    
    @requiere_permiso('clientes_ver')
    def _listar_clientes(self):
        """Lista todos los clientes"""
        self.mostrar_cabecera("LISTADO DE CLIENTES")
        
        clientes = self.cliente_service.listar()
        
        if not clientes:
            print("📭 No hay clientes registrados")
        else:
            print(f"{'ID':<5} {'NOMBRE':<25} {'DOCUMENTO':<20} {'TELÉFONO':<12} {'EMAIL':<25}")
            print("-" * 87)
            for c in clientes:
                nombre_completo = f"{c['nombre']} {c['apellidos']}"
                documento = f"{c['tipo_documento']}-{c['num_documento']}"
                telefono_val = c.get('telefono', '') or ''
                email_val = c.get('email', '') or ''
                print(f"{c['idcliente']:<5} {nombre_completo:<25} {documento:<20} {telefono_val:<12} {email_val:<25}")
        
        self.pausa()
    
    @requiere_permiso('clientes_crear')
    def _crear_cliente(self):
        """Crea un nuevo cliente con validación venezolana y fecha opcional"""
        self.mostrar_cabecera("CREAR CLIENTE")
        
        print("📝 Complete los datos del cliente (los campos con * son obligatorios):")
        print()
        
        nombre = input("* Nombre: ")
        apellidos = input("* Apellidos: ")
        sexo = input("* Sexo (M/F/O): ").upper()
        
        print("\n📅 Fecha de nacimiento (OPCIONAL - presione Enter para omitir)")
        print("   Formato: DD/MM/YYYY (ej: 15/05/1990)")
        
        while True:
            fecha_nac_str = input("Fecha de nacimiento: ").strip()
            
            if fecha_nac_str == "":
                fecha_nac = None
                break
            
            valida, fecha_obj, mensaje = ValidacionVenezuela.validar_fecha(fecha_nac_str)
            
            if valida:
                fecha_nac = fecha_obj
                break
            else:
                print(mensaje)
                print("   Intente nuevamente o presione Enter para omitir:")
        
        print("\n" + "="*60)
        print("🔍 TIPO DE PERSONA - FORMATO DEL DOCUMENTO")
        print("="*60)
        print("1. 🇻🇪 Persona Natural Venezolana  →  V12345678")
        print("2. 🌎 Persona Natural Extranjera   →  E87654321")
        print("3. 🏢 Persona Jurídica (Empresa)   →  J12345678")
        print("4. 🏛️ Gobierno / Institución        →  G12345678")
        print("5. 👥 Consejo Comunal               →  C12345678")
        print("6. 🛂 Pasaporte                      →  Número de pasaporte")
        print("="*60)
        
        tipo_persona = input("Seleccione tipo de persona (1-6): ").strip()
        
        if tipo_persona == '1':
            tipo_doc = 'V'
            print("\n✅ Seleccionó: Persona Natural Venezolana (V)")
            print("📝 Formato requerido: V + 8 dígitos")
            print("   Ejemplo: V12345678")
            num_doc_completo = input("Documento completo: ").upper()
            
            if not num_doc_completo.startswith('V'):
                print("❌ El documento debe comenzar con 'V'")
                self.pausa()
                return
            num_doc = num_doc_completo[1:]
            
        elif tipo_persona == '2':
            tipo_doc = 'E'
            print("\n✅ Seleccionó: Persona Natural Extranjera (E)")
            print("📝 Formato requerido: E + 8 dígitos")
            print("   Ejemplo: E87654321")
            num_doc_completo = input("Documento completo: ").upper()
            
            if not num_doc_completo.startswith('E'):
                print("❌ El documento debe comenzar con 'E'")
                self.pausa()
                return
            num_doc = num_doc_completo[1:]
            
        elif tipo_persona == '3':
            tipo_doc = 'J'
            print("\n✅ Seleccionó: Empresa (J)")
            print("📝 Formato requerido: J + 8 dígitos")
            print("   Ejemplo: J12345678")
            num_doc_completo = input("Documento completo: ").upper()
            
            if not num_doc_completo.startswith('J'):
                print("❌ El documento debe comenzar con 'J'")
                self.pausa()
                return
            num_doc = num_doc_completo[1:]
            
        elif tipo_persona == '4':
            tipo_doc = 'G'
            print("\n✅ Seleccionó: Gobierno / Institución (G)")
            print("📝 Formato requerido: G + 8 dígitos")
            print("   Ejemplo: G12345678")
            num_doc_completo = input("Documento completo: ").upper()
            
            if not num_doc_completo.startswith('G'):
                print("❌ El documento debe comenzar con 'G'")
                self.pausa()
                return
            num_doc = num_doc_completo[1:]
            
        elif tipo_persona == '5':
            tipo_doc = 'C'
            print("\n✅ Seleccionó: Consejo Comunal (C)")
            print("📝 Formato requerido: C + 8 dígitos")
            print("   Ejemplo: C12345678")
            num_doc_completo = input("Documento completo: ").upper()
            
            if not num_doc_completo.startswith('C'):
                print("❌ El documento debe comenzar con 'C'")
                self.pausa()
                return
            num_doc = num_doc_completo[1:]
            
        elif tipo_persona == '6':
            tipo_doc = 'PASAPORTE'
            print("\n✅ Seleccionó: Pasaporte")
            print("📝 Ingrese número de pasaporte (6-12 caracteres)")
            print("   Ejemplo: ABC123456")
            num_doc = input("Pasaporte: ").upper()
            
        else:
            print("❌ Opción no válida")
            self.pausa()
            return
        
        print("\n📧 Email (opcional para clientes):")
        email = input("Email: ").strip()
        if email and ('@' not in email or '.' not in email):
            print("❌ El email no tiene un formato válido")
            self.pausa()
            return
        if not email:
            email = None
        
        direccion = input("Dirección (opcional): ") or None
        telefono = input("Teléfono (opcional): ") or None
        
        fecha_nac_bd = ValidacionVenezuela.formatear_fecha_para_bd(fecha_nac) if fecha_nac else None
        
        if self.cliente_service.crear(
            nombre, apellidos, fecha_nac_bd, tipo_doc, num_doc,
            sexo, direccion, telefono, email
        ):
            print("\n✅ Cliente creado exitosamente")
            if not fecha_nac:
                print("   ℹ️ Fecha de nacimiento no registrada")
            
            cliente_nuevo = self.cliente_service.buscar_por_documento(tipo_doc + num_doc)
            if cliente_nuevo:
                idcliente = cliente_nuevo['idcliente']
                self.registrar_auditoria(
                    accion="CREAR",
                    tabla="cliente",
                    registro_id=idcliente,
                    datos_nuevos=f"Cliente: {nombre} {apellidos}, Doc: {tipo_doc}-{num_doc}"
                )
        else:
            print("\n❌ Error al crear el cliente")
        
        self.pausa()
    
    @requiere_permiso('clientes_ver')
    def _buscar_cliente(self):
        """Busca un cliente por ID o documento"""
        self.mostrar_cabecera("BUSCAR CLIENTE")
        
        print("1. Buscar por ID")
        print("2. Buscar por documento")
        opcion = input(f"{self.COLOR_AMARILLO}🔹 Seleccione: {self.COLOR_RESET}").strip()
        
        if opcion == '1':
            try:
                idcliente = int(input("ID del cliente: "))
                cliente = self.cliente_service.obtener_por_id(idcliente)
                if cliente:
                    self._mostrar_detalle_cliente(cliente)
                else:
                    print(f"❌ No existe cliente con ID {idcliente}")
            except:
                print("❌ ID inválido")
        
        elif opcion == '2':
            doc = input("Número de documento (ej: V12345678): ").upper()
            if doc and doc[0] in ['V', 'E', 'J', 'G', 'C']:
                tipo = doc[0]
                numero = doc[1:]
                clientes = self.cliente_service.listar()
                encontrado = None
                for c in clientes:
                    if c['tipo_documento'] == tipo and c['num_documento'] == numero:
                        encontrado = c
                        break
                if encontrado:
                    self._mostrar_detalle_cliente(encontrado)
                    
                    self.registrar_auditoria(
                        accion="CONSULTAR",
                        tabla="cliente",
                        registro_id=encontrado['idcliente'],
                        datos_nuevos=f"Búsqueda por documento: {doc}"
                    )
                else:
                    print(f"❌ No existe cliente con documento {doc}")
            else:
                print("❌ Formato de documento inválido")
        
        self.pausa()
    
    def _mostrar_detalle_cliente(self, c):
        """Muestra detalles completos de un cliente"""
        print(f"\n📌 ID: {c['idcliente']}")
        print(f"📌 Nombre: {c['nombre']} {c['apellidos']}")
        print(f"📌 Sexo: {c.get('sexo', 'No especificado')}")
        print(f"📌 Fecha Nac.: {c['fecha_nacimiento'] or 'No registrada'}")
        print(f"📌 Documento: {c['tipo_documento']}-{c['num_documento']}")
        print(f"📌 Dirección: {c.get('direccion', 'No registrada')}")
        print(f"📌 Teléfono: {c.get('telefono', 'No registrado')}")
        print(f"📌 Email: {c.get('email', 'No registrado')}")
    
    @requiere_permiso('clientes_editar')
    def _editar_cliente(self):
        """Edita un cliente existente con fecha opcional"""
        self.mostrar_cabecera("EDITAR CLIENTE")
        
        print("¿Cómo desea buscar el cliente?")
        print("1. Buscar por ID")
        print("2. Buscar por documento")
        opcion = input(f"{self.COLOR_AMARILLO}🔹 Seleccione: {self.COLOR_RESET}").strip()
        
        cliente = None
        
        if opcion == '1':
            try:
                idcliente = int(input("ID del cliente: "))
                cliente = self.cliente_service.obtener_por_id(idcliente)
                if not cliente:
                    print(f"❌ No existe cliente con ID {idcliente}")
                    self.pausa()
                    return
            except ValueError:
                print("❌ ID inválido")
                self.pausa()
                return
                
        elif opcion == '2':
            doc = input("Número de documento (ej: V12345678): ").upper()
            doc_limpio = doc.replace('-', '').replace(' ', '')
            
            cliente_simple = None
            cliente_simple = self.cliente_service.buscar_por_documento(doc)
            if not cliente_simple:
                cliente_simple = self.cliente_service.buscar_por_documento(doc_limpio)
            if not cliente_simple and len(doc_limpio) >= 9:
                doc_con_guion = doc_limpio[0] + '-' + doc_limpio[1:]
                cliente_simple = self.cliente_service.buscar_por_documento(doc_con_guion)
            
            if not cliente_simple:
                print(f"❌ No existe cliente con documento {doc}")
                self.pausa()
                return
            cliente = self.cliente_service.obtener_por_id(cliente_simple['idcliente'])
            
        else:
            print("❌ Opción no válida")
            self.pausa()
            return
        
        tipo_actual = cliente['tipo_documento']
        tipo_texto = {
            'V': "🇻🇪 Persona Natural Venezolana",
            'E': "🌎 Persona Natural Extranjera",
            'J': "🏢 Empresa",
            'G': "🏛️ Gobierno / Institución",
            'C': "👥 Consejo Comunal",
            'PASAPORTE': "🛂 Pasaporte"
        }.get(tipo_actual, tipo_actual)
        
        print(f"\nEditando a: {cliente['nombre']} {cliente['apellidos']}")
        print(f"📌 Tipo actual: {tipo_texto}")
        print("(Deje en blanco para mantener el valor actual)")
        print()
        
        datos_anteriores = f"Cliente: {cliente['nombre']} {cliente['apellidos']}, Doc: {cliente['tipo_documento']}-{cliente['num_documento']}"
        
        nombre = input(f"Nombre [{cliente['nombre']}]: ") or cliente['nombre']
        apellidos = input(f"Apellidos [{cliente['apellidos']}]: ") or cliente['apellidos']
        sexo = input(f"Sexo [{cliente['sexo']}]: ").upper() or cliente['sexo']
        
        fecha_actual = cliente['fecha_nacimiento']
        fecha_actual_str = fecha_actual.strftime('%d/%m/%Y') if fecha_actual else "No registrada"
        
        print(f"\n📅 Fecha de nacimiento actual: {fecha_actual_str}")
        print("   (Enter para mantener, 'NUEVA' para cambiar, 'BORRAR' para eliminar)")
        
        while True:
            opcion_fecha = input("Opción: ").strip().upper()
            
            if opcion_fecha == "":
                fecha_nac = fecha_actual
                break
            elif opcion_fecha == "BORRAR":
                fecha_nac = None
                print("✅ Fecha de nacimiento eliminada")
                break
            elif opcion_fecha == "NUEVA":
                print("Ingrese nueva fecha (DD/MM/YYYY) o Enter para cancelar:")
                nueva_fecha = input("Nueva fecha: ").strip()
                
                if nueva_fecha == "":
                    fecha_nac = fecha_actual
                    break
                
                valida, fecha_obj, mensaje = ValidacionVenezuela.validar_fecha(nueva_fecha)
                if valida:
                    fecha_nac = fecha_obj
                    break
                else:
                    print(mensaje)
            else:
                print("Opción no válida. Use Enter, NUEVA o BORRAR")
        
        print("\n¿Cambiar tipo de documento? (s/N): ", end="")
        cambiar_tipo = input().lower()
        
        if cambiar_tipo == 's':
            print("\n" + "="*60)
            print("🔍 NUEVO TIPO DE DOCUMENTO")
            print("="*60)
            print("1. 🇻🇪 Venezolano (V) → V12345678")
            print("2. 🌎 Extranjero (E) → E87654321")
            print("3. 🏢 Empresa (J) → J12345678")
            print("4. 🏛️ Gobierno (G) → G12345678")
            print("5. 👥 Consejo Comunal (C) → C12345678")
            print("6. 🛂 Pasaporte → texto libre")
            print("="*60)
            
            tipo_op = input("Seleccione nuevo tipo (1-6): ").strip()
            
            if tipo_op == '1':
                tipo_doc = 'V'
                print("Ingrese documento completo (ej: V12345678):")
                doc_completo = input("Documento: ").upper()
                if doc_completo.startswith('V'):
                    num_doc = doc_completo[1:]
                else:
                    print("❌ Debe comenzar con V")
                    self.pausa()
                    return
            elif tipo_op == '2':
                tipo_doc = 'E'
                print("Ingrese documento completo (ej: E87654321):")
                doc_completo = input("Documento: ").upper()
                if doc_completo.startswith('E'):
                    num_doc = doc_completo[1:]
                else:
                    print("❌ Debe comenzar con E")
                    self.pausa()
                    return
            elif tipo_op == '3':
                tipo_doc = 'J'
                print("Ingrese documento completo (ej: J12345678):")
                doc_completo = input("Documento: ").upper()
                if doc_completo.startswith('J'):
                    num_doc = doc_completo[1:]
                else:
                    print("❌ Debe comenzar con J")
                    self.pausa()
                    return
            elif tipo_op == '4':
                tipo_doc = 'G'
                print("Ingrese documento completo (ej: G12345678):")
                doc_completo = input("Documento: ").upper()
                if doc_completo.startswith('G'):
                    num_doc = doc_completo[1:]
                else:
                    print("❌ Debe comenzar con G")
                    self.pausa()
                    return
            elif tipo_op == '5':
                tipo_doc = 'C'
                print("Ingrese documento completo (ej: C12345678):")
                doc_completo = input("Documento: ").upper()
                if doc_completo.startswith('C'):
                    num_doc = doc_completo[1:]
                else:
                    print("❌ Debe comenzar con C")
                    self.pausa()
                    return
            elif tipo_op == '6':
                tipo_doc = 'PASAPORTE'
                num_doc = input("Número de pasaporte: ").upper()
            else:
                print("❌ Opción no válida")
                self.pausa()
                return
        else:
            tipo_doc = cliente['tipo_documento']
            num_doc = cliente['num_documento']
        
        direccion = input(f"Dirección [{cliente.get('direccion', '')}]: ") or cliente.get('direccion')
        telefono = input(f"Teléfono [{cliente.get('telefono', '')}]: ") or cliente.get('telefono')
        email = input(f"Email [{cliente.get('email', '')}]: ") or cliente.get('email')
        
        fecha_nac_bd = ValidacionVenezuela.formatear_fecha_para_bd(fecha_nac) if fecha_nac else None
        
        if self.cliente_service.actualizar(
            cliente['idcliente'], nombre, apellidos, fecha_nac_bd, tipo_doc, num_doc,
            sexo, direccion, telefono, email
        ):
            print("\n✅ Cliente actualizado correctamente")
            
            datos_nuevos = f"Cliente: {nombre} {apellidos}, Doc: {tipo_doc}-{num_doc}"
            self.registrar_auditoria(
                accion="MODIFICAR",
                tabla="cliente",
                registro_id=cliente['idcliente'],
                datos_anteriores=datos_anteriores,
                datos_nuevos=datos_nuevos
            )
        else:
            print("\n❌ Error al actualizar el cliente")
        
        self.pausa()
    
    @requiere_permiso('clientes_eliminar')
    def _eliminar_cliente(self):
        """Elimina un cliente"""
        self.mostrar_cabecera("ELIMINAR CLIENTE")
        
        try:
            idcliente = int(input("ID del cliente a eliminar: "))
            
            cliente = self.cliente_service.obtener_por_id(idcliente)
            if not cliente:
                print(f"❌ No existe cliente con ID {idcliente}")
                self.pausa()
                return
            
            datos_cliente = f"Cliente: {cliente['nombre']} {cliente['apellidos']}, Doc: {cliente['tipo_documento']}-{cliente['num_documento']}"
            
            print(f"\n¿Está seguro de eliminar a {cliente['nombre']} {cliente['apellidos']}?")
            confirmacion = input("Esta acción no se puede deshacer (escriba 'ELIMINAR' para confirmar): ")
            
            if confirmacion == 'ELIMINAR':
                if self.cliente_service.eliminar(idcliente):
                    print("✅ Cliente eliminado correctamente")
                    
                    self.registrar_auditoria(
                        accion="ELIMINAR",
                        tabla="cliente",
                        registro_id=idcliente,
                        datos_anteriores=datos_cliente
                    )
                else:
                    print("❌ Error al eliminar el cliente (puede tener ventas asociadas)")
            else:
                print("Operación cancelada")
        
        except Exception as e:
            print(f"❌ Error: {e}")
        
        self.pausa()
    
    @requiere_permiso('articulos_ver')
    def menu_articulos(self):
        """Menú de gestión de artículos"""
        while True:
            self.mostrar_cabecera("GESTIÓN DE ARTÍCULOS")
            print("1. Listar artículos")
            print("2. Buscar artículo (por código/nombre)")
            print("3. Crear artículo")
            print("4. Editar artículo")
            print("5. Eliminar artículo")
            print("6. Ver stock por lote")
            print("7. 🔍 Búsqueda avanzada (código barras/PLU)")
            print("0. Volver")
            print()
            
            opcion = input(f"{self.COLOR_AMARILLO}🔹 Seleccione una opción: {self.COLOR_RESET}").strip()
            
            if opcion == '1':
                self._listar_articulos()
            elif opcion == '2':
                self._buscar_articulo()
            elif opcion == '3':
                self._crear_articulo()
            elif opcion == '4':
                self._editar_articulo()
            elif opcion == '5':
                self._eliminar_articulo()
            elif opcion == '6':
                self._ver_stock_lotes()
            elif opcion == '7':
                self._buscar_articulo_gestion()
            elif opcion == '0':
                break
            else:
                print("❌ Opción no válida")
                self.pausa()
    
    @requiere_permiso('articulos_ver')
    def _listar_articulos(self):
        """Lista todos los artículos con opciones de edición"""
        while True:
            self.mostrar_cabecera("LISTADO DE ARTÍCULOS")
            
            articulos_con_stock = self.inventario_service.listar_con_stock()
            
            if not articulos_con_stock:
                print("📭 No hay artículos registrados")
                self.pausa()
                return
            
            # Ordenar artículos por ID
            articulos_con_stock.sort(key=lambda x: x['idarticulo'])
            
            # Cabecera con columnas
            print(f"{'ID':<5} {'CÓDIGO':<15} {'NOMBRE':<30} {'CATEGORÍA':<20} {'PRECIO $':<12} {'STOCK':<10} {'ESTADO':<10}")
            print("-" * 107)
            
            for a in articulos_con_stock:
                precio = a.get('precio_venta', 0)
                stock_str = f"{a['stock_actual']} und"
                
                # Formatear precio en dólares (enteros sin decimales, decimales con 2 dígitos)
                if precio == int(precio):  # Si es entero (ej: 150.0 → 150)
                    precio_str = f"${int(precio)}"
                else:  # Si tiene decimales (ej: 0.60, 2.5, 4.50)
                    # Mostrar con 2 decimales pero sin ceros innecesarios
                    precio_str = f"${precio:.2f}".rstrip('0').rstrip('.') if precio % 1 != 0 else f"${int(precio)}"
                
                estado = f"{a['emoji']}"
                
                linea = f"{a['idarticulo']:<5} {a['codigo']:<15} {a['nombre']:<30} {a['categoria']:<20} {precio_str:<12} {stock_str:<10} {estado:<10}"
                print(f"{a['color']}{linea}{self.inventario_service.COLOR_RESET}")
            
            print("-" * 107)
            print("Opciones de edición:")
            print("  [E] Editar TODO (categoría, nombre, stock) - Ingrese ID")
            print("  [M] Editar solo PRECIO en dólares $ - Ingrese ID")
            print("  [V] Volver al menú")
            print("-" * 40)
            
            opcion = input(f"{self.COLOR_AMARILLO}🔹 Seleccione: {self.COLOR_RESET}").strip().upper()
            
            if opcion == 'V':
                break
            
            elif opcion == 'E':
                try:
                    id_input = input("ID del artículo a editar (todo excepto precio): ").strip()
                    if id_input.isdigit():
                        id_editar = int(id_input)
                        articulo = self.articulo_service.obtener_por_id(id_editar)
                        if articulo:
                            self._editar_articulo_completo(id_editar)
                        else:
                            print(f"{self.COLOR_ROJO}❌ No existe artículo con ID {id_editar}{self.COLOR_RESET}")
                            self.pausa()
                    else:
                        print(f"{self.COLOR_ROJO}❌ ID inválido{self.COLOR_RESET}")
                        self.pausa()
                except Exception as e:
                    print(f"{self.COLOR_ROJO}❌ Error: {e}{self.COLOR_RESET}")
                    self.pausa()
            
            elif opcion == 'M':
                try:
                    id_input = input("ID del artículo a editar (solo precio $): ").strip()
                    if id_input.isdigit():
                        id_editar = int(id_input)
                        articulo = self.articulo_service.obtener_por_id(id_editar)
                        if articulo:
                            self._editar_precio_articulo(id_editar)
                        else:
                            print(f"{self.COLOR_ROJO}❌ No existe artículo con ID {id_editar}{self.COLOR_RESET}")
                            self.pausa()
                    else:
                        print(f"{self.COLOR_ROJO}❌ ID inválido{self.COLOR_RESET}")
                        self.pausa()
                except Exception as e:
                    print(f"{self.COLOR_ROJO}❌ Error: {e}{self.COLOR_RESET}")
                    self.pausa()
            
            elif opcion.isdigit():
                # Si el usuario ingresa directamente un número, por defecto va a edición completa
                id_editar = int(opcion)
                articulo = self.articulo_service.obtener_por_id(id_editar)
                if articulo:
                    self._editar_articulo_completo(id_editar)
                else:
                    print(f"{self.COLOR_ROJO}❌ No existe artículo con ID {id_editar}{self.COLOR_RESET}")
                    self.pausa()
            
            else:
                print(f"{self.COLOR_ROJO}❌ Opción no válida{self.COLOR_RESET}")
                self.pausa()

    def _editar_precio_articulo(self, idarticulo):
        """
        Edita SOLO el precio de un artículo (rápido)
        """
        self.mostrar_cabecera(f"EDITAR PRECIO - ID: {idarticulo}")
        
        art = self.articulo_service.obtener_por_id(idarticulo)
        
        if not art:
            print(f"{self.COLOR_ROJO}❌ No existe artículo con ID {idarticulo}{self.COLOR_RESET}")
            self.pausa()
            return
        
        # Mostrar información actual
        print(f"\n{self.COLOR_VERDE}📌 Artículo:{self.COLOR_RESET} {art['nombre']}")
        print(f"   Código: {art['codigo']}")
        print(f"   Precio actual: ${art.get('precio_venta', 0):.2f}".rstrip('0').rstrip('.') if art.get('precio_venta', 0) % 1 != 0 else f"   Precio actual: ${int(art.get('precio_venta', 0))}")
        
        print(f"\n{self.COLOR_AMARILLO}💰 Ingrese el nuevo precio en DÓLARES (puede usar decimales: 0.60, 2.5, 4.50):{self.COLOR_RESET}")
        
        try:
            precio_input = input(f"Nuevo precio $: ").strip()
            if precio_input:
                nuevo_precio = float(precio_input.replace(',', '.'))
                if nuevo_precio >= 0:
                    
                    # Actualizar solo el precio en BD
                    if self.articulo_service.actualizar(
                        idarticulo=idarticulo,
                        codigo=art['codigo'],
                        nombre=art['nombre'],
                        idcategoria=art['idcategoria'],
                        idpresentacion=art['idpresentacion'],
                        descripcion=art.get('descripcion'),
                        precio_venta=nuevo_precio,
                        precio_referencia=art.get('precio_referencia')
                    ):
                        # Mostrar formato apropiado
                        if nuevo_precio == int(nuevo_precio):
                            print(f"\n{self.COLOR_VERDE}✅ Precio actualizado a ${int(nuevo_precio)}{self.COLOR_RESET}")
                        else:
                            print(f"\n{self.COLOR_VERDE}✅ Precio actualizado a ${nuevo_precio:.2f}".rstrip('0').rstrip('.') + f"{self.COLOR_RESET}")
                    else:
                        print(f"\n{self.COLOR_ROJO}❌ Error al actualizar precio{self.COLOR_RESET}")
                else:
                    print("❌ El precio no puede ser negativo")
            else:
                print("Precio no modificado")
                
        except ValueError:
            print(f"{self.COLOR_ROJO}❌ Error: Ingrese un número válido (ej: 150, 0.60, 2.5){self.COLOR_RESET}")
        except Exception as e:
            print(f"{self.COLOR_ROJO}❌ Error: {e}{self.COLOR_RESET}")
        
        self.pausa()

    def _editar_articulo_completo(self, idarticulo):
        """
        Edita un artículo completo (todo excepto precio)
        """
        self.mostrar_cabecera(f"EDITAR ARTÍCULO COMPLETO - ID: {idarticulo}")
        
        art = self.articulo_service.obtener_por_id(idarticulo)
        
        if not art:
            print(f"{self.COLOR_ROJO}❌ No existe artículo con ID {idarticulo}{self.COLOR_RESET}")
            self.pausa()
            return
        
        # Mostrar información actual
        print(f"\n{self.COLOR_VERDE}📌 Datos actuales:{self.COLOR_RESET}")
        print(f"   Código: {art['codigo']}")
        print(f"   Nombre: {art['nombre']}")
        
        # Obtener precio actual (FORZAR A FLOAT)
        precio_actual = art.get('precio_venta', 0)
        try:
            precio_actual = float(precio_actual)
        except:
            precio_actual = 0.0
        
        print(f"   Precio actual: ${precio_actual:,.2f}")
        
        # Obtener stock actual
        stock_actual = self.inventario_service.obtener_stock_articulo(idarticulo)
        print(f"   Stock actual: {stock_actual} unidades")
        
        print(f"\n{self.COLOR_AMARILLO}📝 Ingrese los nuevos datos (Enter para mantener):{self.COLOR_RESET}")
        print()
        
        # Código
        nuevo_codigo = input(f"Código [{art['codigo']}]: ").strip() or art['codigo']
        
        # Nombre
        nuevo_nombre = input(f"Nombre [{art['nombre']}]: ").strip() or art['nombre']
        
        # Categoría
        categorias = self.categoria_service.listar()
        print("\nCategorías disponibles:")
        for c in categorias:
            print(f"  {c['idcategoria']}. {c['nombre']}")
        try:
            cat_input = input(f"ID categoría [{art['idcategoria']}]: ").strip()
            nueva_categoria = int(cat_input) if cat_input else art['idcategoria']
        except:
            nueva_categoria = art['idcategoria']
        
        # Stock (opcional)
        print("\n" + "="*40)
        print("¿Desea ajustar el stock?")
        print("1. Sí, agregar stock")
        print("2. Sí, quitar stock")
        print("3. No, mantener stock")
        opcion_stock = input(f"{self.COLOR_AMARILLO}🔹 Seleccione: {self.COLOR_RESET}").strip()
        
        if opcion_stock == '1':
            try:
                cantidad = int(input("Cantidad a AGREGAR: "))
                if cantidad > 0:
                    self.inventario_service.reponer_stock(
                        idarticulo=idarticulo,
                        cantidad=cantidad,
                        idingreso=None,
                        precio_compra=art.get('precio_referencia', 0)
                    )
                    print(f"{self.COLOR_VERDE}✅ Stock aumentado: +{cantidad} unidades{self.COLOR_RESET}")
            except:
                print("❌ Cantidad inválida")
        
        elif opcion_stock == '2':
            try:
                cantidad = int(input("Cantidad a QUITAR: "))
                if cantidad > 0 and cantidad <= stock_actual:
                    self.inventario_service.descontar_stock(
                        idarticulo=idarticulo,
                        cantidad=cantidad,
                        idventa=None,
                        precio_unitario=precio_actual
                    )
                    print(f"{self.COLOR_VERDE}✅ Stock disminuido: -{cantidad} unidades{self.COLOR_RESET}")
                else:
                    print(f"❌ Cantidad inválida o superior al stock actual ({stock_actual})")
            except:
                print("❌ Cantidad inválida")
        
        # Actualizar en BD (MANTENIENDO EL PRECIO ACTUAL)
        print(f"\n🔍 Manteniendo precio: ${precio_actual:,.2f}")
        
        if self.articulo_service.actualizar(
            idarticulo=idarticulo,
            codigo=nuevo_codigo,
            nombre=nuevo_nombre,
            idcategoria=nueva_categoria,
            idpresentacion=art['idpresentacion'],
            descripcion=art.get('descripcion'),
            precio_venta=precio_actual,  # Pasamos el precio actual como float
            precio_referencia=art.get('precio_referencia')
        ):
            print(f"\n{self.COLOR_VERDE}✅ Artículo actualizado correctamente (precio mantenido en ${precio_actual:,.2f}){self.COLOR_RESET}")
        else:
            print(f"\n{self.COLOR_ROJO}❌ Error al actualizar{self.COLOR_RESET}")
        
        self.pausa()
    
    @requiere_permiso('articulos_crear')
    def _crear_articulo(self):
        """Crea un nuevo artículo con precio de venta"""
        self.mostrar_cabecera("CREAR ARTÍCULO")
        
        # Mostrar categorías disponibles
        categorias = self.categoria_service.listar()
        if not categorias:
            print("❌ No hay categorías. Cree una primero.")
            self.pausa()
            return
        
        print("Categorías disponibles:")
        for c in categorias:
            print(f"  {c['idcategoria']}. {c['nombre']}")
        
        try:
            idcat = int(input("\nID de categoría: "))
        except:
            print("❌ Categoría inválida")
            self.pausa()
            return
        
        # Mostrar presentaciones
        print("\nPresentaciones:")
        print("  1. Unidad")
        print("  2. Caja")
        print("  3. Kilogramo")
        
        try:
            idpres = int(input("ID de presentación: "))
        except:
            print("❌ Presentación inválida")
            self.pausa()
            return
        
        print()
        codigo = input("Código del artículo: ")
        nombre = input("Nombre del artículo: ")
        descripcion = input("Descripción (opcional): ") or None
        
        # Solicitar precio de venta
        print("\n💰 PRECIO DE VENTA")
        print("="*40)
        try:
            precio_venta = float(input("Precio de venta (Bs.): "))
            if precio_venta < 0:
                print("❌ El precio no puede ser negativo")
                precio_venta = 0
        except:
            print("❌ Precio inválido. Se asignará 0 por defecto.")
            precio_venta = 0
        
        # Solicitar precio de referencia (opcional)
        print("\n📦 PRECIO DE REFERENCIA (costo)")
        print("="*40)
        print("(Opcional - Enter para omitir)")
        try:
            precio_ref_input = input("Precio de referencia (costo): ").strip()
            if precio_ref_input:
                precio_referencia = float(precio_ref_input)
                if precio_referencia < 0:
                    precio_referencia = 0
            else:
                precio_referencia = None
        except:
            precio_referencia = None
        
        # Solicitar stock inicial
        print("\n📦 STOCK INICIAL")
        print("="*40)
        try:
            stock_inicial = int(input("Cantidad inicial: "))
            if stock_inicial < 0:
                print("❌ La cantidad no puede ser negativa")
                stock_inicial = 0
        except:
            print("❌ Cantidad inválida. Se asignará 0 por defecto.")
            stock_inicial = 0
        
        if self.articulo_service.crear(
            codigo, nombre, idcat, idpres, descripcion, 
            precio_venta, precio_referencia
        ):
            print(f"\n{self.COLOR_VERDE}✅ Artículo creado exitosamente{self.COLOR_RESET}")
            
            # Buscar el ID del artículo recién creado
            articulo_nuevo = self.articulo_service.buscar_por_codigo(codigo)
            if articulo_nuevo:
                idarticulo = articulo_nuevo['idarticulo']
                
                # Registrar stock inicial en kardex
                if stock_inicial > 0:
                    self.inventario_service.reponer_stock(
                        idarticulo=idarticulo,
                        cantidad=stock_inicial,
                        idingreso=None,
                        precio_compra=precio_referencia or 0
                    )
                    print(f"   📦 Stock inicial: {stock_inicial} unidades")
                    print(f"   💰 Precio venta: Bs. {precio_venta:.2f}")
                    if precio_referencia:
                        print(f"   💰 Precio referencia: Bs. {precio_referencia:.2f}")
                
                self.registrar_auditoria(
                    accion="CREAR",
                    tabla="articulo",
                    registro_id=idarticulo,
                    datos_nuevos=f"Artículo: {nombre}, Código: {codigo}, Precio: {precio_venta}"
                )
        else:
            print(f"\n{self.COLOR_ROJO}❌ Error al crear el artículo{self.COLOR_RESET}")
        
        self.pausa()
    
    @requiere_permiso('articulos_ver')
    def _buscar_articulo(self):
        """Busca un artículo por ID o código"""
        self.mostrar_cabecera("BUSCAR ARTÍCULO")
        
        print("1. Buscar por ID")
        print("2. Buscar por código")
        opcion = input(f"{self.COLOR_AMARILLO}🔹 Seleccione: {self.COLOR_RESET}").strip()
        
        if opcion == '1':
            try:
                idart = int(input("ID del artículo: "))
                art = self.articulo_service.obtener_por_id(idart)
                if art:
                    self._mostrar_detalle_articulo(art)
                    
                    self.registrar_auditoria(
                        accion="CONSULTAR",
                        tabla="articulo",
                        registro_id=idart,
                        datos_nuevos=f"Artículo: {art['nombre']}"
                    )
                else:
                    print(f"❌ No existe artículo con ID {idart}")
            except:
                print("❌ ID inválido")
        
        elif opcion == '2':
            codigo = input("Código del artículo: ")
            art = self.articulo_service.buscar_por_codigo(codigo)
            if art:
                art = self.articulo_service.obtener_por_id(art['idarticulo'])
                self._mostrar_detalle_articulo(art)
                
                self.registrar_auditoria(
                    accion="CONSULTAR",
                    tabla="articulo",
                    registro_id=art['idarticulo'],
                    datos_nuevos=f"Artículo: {art['nombre']}, Código: {codigo}"
                )
            else:
                print(f"❌ No existe artículo con código {codigo}")
        
        self.pausa()
    
    def _mostrar_detalle_articulo(self, a):
        """Muestra detalles completos de un artículo"""
        print(f"\n📌 ID: {a['idarticulo']}")
        print(f"📌 Código: {a['codigo']}")
        print(f"📌 Nombre: {a['nombre']}")
        print(f"📌 Categoría: {a.get('categoria', 'N/A')}")
        print(f"📌 Presentación: {a.get('presentacion', 'N/A')}")
        print(f"📌 Descripción: {a.get('descripcion', 'Sin descripción')}")
    
    @requiere_permiso('articulos_editar')
    def _editar_articulo(self):
        """Edita un artículo existente mostrando stock actual"""
        self.mostrar_cabecera("EDITAR ARTÍCULO")
        
        try:
            idart = int(input("ID del artículo a editar: "))
            art = self.articulo_service.obtener_por_id(idart)
            
            if not art:
                print(f"❌ No existe artículo con ID {idart}")
                self.pausa()
                return
            
            # Obtener stock actual
            stock_actual = self.inventario_service.obtener_stock_articulo(idart)
            nivel = self.inventario_service.obtener_nivel_stock(stock_actual)
            
            # Guardar datos anteriores para auditoría
            datos_anteriores = f"Artículo: {art['nombre']}, Código: {art['codigo']}, Stock: {stock_actual}"
            
            print(f"\n📌 Editando: {art['nombre']}")
            print(f"{nivel['color']}📦 Stock actual: {stock_actual} unidades {nivel['emoji']} {nivel['nivel']}{self.COLOR_RESET}")
            print("(Deje en blanco para mantener el valor actual)")
            print()
            
            codigo = input(f"Código [{art['codigo']}]: ") or art['codigo']
            nombre = input(f"Nombre [{art['nombre']}]: ") or art['nombre']
            descripcion = input(f"Descripción [{art.get('descripcion', '')}]: ") or art.get('descripcion')
            
            # Opción de ajustar stock
            print(f"\n📦 AJUSTE DE STOCK")
            print("="*40)
            print(f"Stock actual: {stock_actual} unidades")
            print("¿Desea ajustar el stock?")
            print("1. Sí, agregar stock")
            print("2. Sí, quitar stock")
            print("3. No, mantener stock actual")
            opcion_stock = input(f"{self.COLOR_AMARILLO}🔹 Seleccione: {self.COLOR_RESET}").strip()
            
            if opcion_stock == '1':
                try:
                    cantidad = int(input("Cantidad a AGREGAR: "))
                    if cantidad > 0:
                        self.inventario_service.reponer_stock(
                            idarticulo=idart,
                            cantidad=cantidad,
                            idingreso=None,
                            precio_compra=0
                        )
                        print(f"{self.COLOR_VERDE}✅ Stock aumentado: +{cantidad} unidades{self.COLOR_RESET}")
                        stock_actual += cantidad
                except:
                    print("❌ Cantidad inválida")
            
            elif opcion_stock == '2':
                try:
                    cantidad = int(input("Cantidad a QUITAR: "))
                    if cantidad > 0 and cantidad <= stock_actual:
                        self.inventario_service.descontar_stock(
                            idarticulo=idart,
                            cantidad=cantidad,
                            idventa=None,
                            precio_unitario=0
                        )
                        print(f"{self.COLOR_VERDE}✅ Stock disminuido: -{cantidad} unidades{self.COLOR_RESET}")
                        stock_actual -= cantidad
                    else:
                        print(f"❌ Cantidad inválida o superior al stock actual ({stock_actual})")
                except:
                    print("❌ Cantidad inválida")
            
            # Mostrar categorías
            print("\nCategorías disponibles:")
            categorias = self.categoria_service.listar()
            for c in categorias:
                print(f"  {c['idcategoria']}. {c['nombre']}")
            
            try:
                idcat = int(input(f"ID categoría [{art['idcategoria']}]: ") or art['idcategoria'])
            except:
                idcat = art['idcategoria']
            
            # Presentaciones
            print("\nPresentaciones:")
            print("  1. Unidad")
            print("  2. Caja")
            print("  3. Kilogramo")
            
            try:
                idpres = int(input(f"ID presentación [{art['idpresentacion']}]: ") or art['idpresentacion'])
            except:
                idpres = art['idpresentacion']
            
            if self.articulo_service.actualizar(idart, codigo, nombre, idcat, idpres, descripcion):
                print(f"\n{self.COLOR_VERDE}✅ Artículo actualizado correctamente{self.COLOR_RESET}")
                print(f"   📦 Stock final: {stock_actual} unidades")
                
                datos_nuevos = f"Artículo: {nombre}, Código: {codigo}, Stock: {stock_actual}"
                self.registrar_auditoria(
                    accion="MODIFICAR",
                    tabla="articulo",
                    registro_id=idart,
                    datos_anteriores=datos_anteriores,
                    datos_nuevos=datos_nuevos
                )
            else:
                print(f"\n{self.COLOR_ROJO}❌ Error al actualizar el artículo{self.COLOR_RESET}")
        
        except Exception as e:
            print(f"❌ Error: {e}")
        
        self.pausa()
    
    @requiere_permiso('articulos_eliminar')
    def _eliminar_articulo(self):
        """Elimina un artículo"""
        self.mostrar_cabecera("ELIMINAR ARTÍCULO")
        
        try:
            idart = int(input("ID del artículo a eliminar: "))
            
            art = self.articulo_service.obtener_por_id(idart)
            if not art:
                print(f"❌ No existe artículo con ID {idart}")
                self.pausa()
                return
            
            datos_articulo = f"Artículo: {art['nombre']}, Código: {art['codigo']}"
            
            print(f"\n¿Está seguro de eliminar {art['nombre']}?")
            confirmacion = input("Esta acción no se puede deshacer (escriba 'ELIMINAR' para confirmar): ")
            
            if confirmacion == 'ELIMINAR':
                if self.articulo_service.eliminar(idart):
                    print("✅ Artículo eliminado correctamente")
                    
                    self.registrar_auditoria(
                        accion="ELIMINAR",
                        tabla="articulo",
                        registro_id=idart,
                        datos_anteriores=datos_articulo
                    )
                else:
                    print("❌ Error al eliminar el artículo (puede tener movimientos asociados)")
            else:
                print("Operación cancelada")
        
        except Exception as e:
            print(f"❌ Error: {e}")
        
        self.pausa()
    
    @requiere_permiso('inventario_ver')
    def _ver_stock_lotes(self):
        """Ver stock por lotes de un artículo"""
        self.mostrar_cabecera("STOCK POR LOTES")
        
        try:
            idart = int(input("ID del artículo: "))
            art = self.articulo_service.obtener_por_id(idart)
            
            if not art:
                print(f"❌ No existe artículo con ID {idart}")
                self.pausa()
                return
            
            print(f"\nArtículo: {art['nombre']}")
            stock = self.inventario_service.obtener_stock_articulo(idart)
            nivel = self.inventario_service.obtener_nivel_stock(stock)
            
            print(f"Stock total: {stock} unidades")
            print(f"Estado: {nivel['color']}{nivel['emoji']} {nivel['nivel']}{self.inventario_service.COLOR_RESET}")
            print("🔧 Módulo de lotes en desarrollo")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        self.pausa()
    
    @requiere_permiso('ventas_ver')
    def menu_ventas(self):
        """Menú de gestión de ventas (con 3 opciones de identificación)"""
        while True:
            self.mostrar_cabecera("GESTIÓN DE VENTAS")
            print("1. Listar ventas")
            print("2. Registrar venta")
            print("3. Ver detalle de venta")
            print("4. Anular venta")
            print("0. Volver")
            print()
            
            opcion = input(f"{self.COLOR_AMARILLO}🔹 Seleccione una opción: {self.COLOR_RESET}").strip()
            
            if opcion == '1':
                self._listar_ventas()
            elif opcion == '2':
                self._registrar_venta()
            elif opcion == '3':
                self._ver_venta()
            elif opcion == '4':
                self._anular_venta()
            elif opcion == '0':
                break
            else:
                print("❌ Opción no válida")
                self.pausa()

    @requiere_permiso('ventas_crear')
    def _registrar_venta(self):
        """Registra una nueva venta usando precios de artículos y tasas preconfiguradas"""
        self.mostrar_cabecera("REGISTRAR VENTA - MULTIMONEDA")
        
        # Obtener usuario actual
        usuario = self.trabajador_service.get_usuario_actual()
        if not usuario:
            print(f"{self.COLOR_ROJO}❌ Debe iniciar sesión para registrar ventas{self.COLOR_RESET}")
            self.pausa()
            return
        
        # Obtener tasas actuales preconfiguradas
        tasas_actuales = self.obtener_tasas_actuales()
        tasa_usd = tasas_actuales.get('USD', 0)
        
        if tasa_usd <= 0:
            print(f"{self.COLOR_AMARILLO}⚠️ No hay tasa USD configurada. Use [X] en el menú principal.{self.COLOR_RESET}")
            self.pausa()
            return
        
        # ===== DETECTAR SISTEMA OPERATIVO =====
        import platform
        sistema = platform.system()
        
        # ===== ATAJOS DE TECLADO =====
        print(f"\n{self.COLOR_AMARILLO}⚡ ATAJOS DE TECLADO:{self.COLOR_RESET}")
        
        if sistema == "Windows":
            print(f"  {self.COLOR_VERDE}[F8]{self.COLOR_RESET}  → Consumidor Final (DIRECTO)")
            print(f"  {self.COLOR_VERDE}[F9]{self.COLOR_RESET}  → Buscar por Cédula")
            print(f"  {self.COLOR_VERDE}[F10]{self.COLOR_RESET} → Buscar por RIF")
            print(f"  {self.COLOR_VERDE}[F11]{self.COLOR_RESET} → Imprimir Factura")
            print(f"  {self.COLOR_VERDE}[ESC]{self.COLOR_RESET} → Menú normal")
        else:
            print(f"  {self.COLOR_VERDE}[1]{self.COLOR_RESET} → Consumidor Final")
            print(f"  {self.COLOR_VERDE}[2]{self.COLOR_RESET} → Buscar por Cédula")
            print(f"  {self.COLOR_VERDE}[3]{self.COLOR_RESET} → Buscar por RIF")
            print(f"  {self.COLOR_VERDE}[4]{self.COLOR_RESET} → Imprimir Factura")
            print(f"  {self.COLOR_VERDE}[0]{self.COLOR_RESET} → Menú normal")
            print(f"  {self.COLOR_VERDE}[ESC]{self.COLOR_RESET} → También menú normal")
        
        print("\nPresione una tecla o use los atajos...")
        
        try:
            import readchar
            key = readchar.readkey()
            
            print(f"Tecla detectada: '{key}' - Sistema: {sistema}")
            
            if sistema == "Windows":
                if key == readchar.key.F8:
                    print(f"\n{self.COLOR_VERDE}✅ Atajo F8: Consumidor Final{self.COLOR_RESET}")
                    return self._continuar_venta_consumidor_final(usuario)
                elif key == readchar.key.F9:
                    print(f"\n{self.COLOR_VERDE}✅ Atajo F9: Búsqueda por Cédula{self.COLOR_RESET}")
                    return self._buscar_por_cedula_rapido(usuario)
                elif key == readchar.key.F10:
                    print(f"\n{self.COLOR_VERDE}✅ Atajo F10: Búsqueda por RIF{self.COLOR_RESET}")
                    return self._buscar_por_rif_rapido(usuario)
                elif key == readchar.key.F11:
                    print(f"\n{self.COLOR_VERDE}✅ Atajo F11: Imprimir Factura{self.COLOR_RESET}")
                    return self._imprimir_factura_rapido(usuario)
                elif key == readchar.key.ESC:
                    print(f"\n{self.COLOR_AMARILLO}⏎ ESC detectado - Continuando con menú normal{self.COLOR_RESET}")
                    opcion_ident = None
                else:
                    print(f"\n{self.COLOR_AMARILLO}⏎ Tecla no es atajo - Continuando con menú normal{self.COLOR_RESET}")
                    opcion_ident = None
            else:
                if key == '1':
                    print(f"\n{self.COLOR_VERDE}✅ Atajo 1: Consumidor Final{self.COLOR_RESET}")
                    return self._continuar_venta_consumidor_final(usuario)
                elif key == '2':
                    print(f"\n{self.COLOR_VERDE}✅ Atajo 2: Búsqueda por Cédula{self.COLOR_RESET}")
                    return self._buscar_por_cedula_rapido(usuario)
                elif key == '3':
                    print(f"\n{self.COLOR_VERDE}✅ Atajo 3: Búsqueda por RIF{self.COLOR_RESET}")
                    return self._buscar_por_rif_rapido(usuario)
                elif key == '4':
                    print(f"\n{self.COLOR_VERDE}✅ Atajo 4: Imprimir Factura{self.COLOR_RESET}")
                    return self._imprimir_factura_rapido(usuario)
                elif key == '0':
                    print(f"\n{self.COLOR_AMARILLO}⏎ Atajo 0 - Continuando con menú normal{self.COLOR_RESET}")
                    opcion_ident = None
                elif key == readchar.key.ESC:
                    print(f"\n{self.COLOR_AMARILLO}⏎ ESC detectado - Continuando con menú normal{self.COLOR_RESET}")
                    opcion_ident = None
                else:
                    print(f"\n{self.COLOR_AMARILLO}⏎ Tecla '{key}' no es atajo - Continuando con menú normal{self.COLOR_RESET}")
                    opcion_ident = None
                
        except Exception as e:
            logger.error(f"Error en atajo de teclado: {e}")
            opcion_ident = None
        
        # Si no se usó atajo, mostrar menú normal
        if opcion_ident is None:
            print("\n📋 IDENTIFICACIÓN DEL CLIENTE")
            print("="*60)
            print("Seleccione el tipo de identificación:")
            print("1. 🇻🇪 RIF (Empresas/Contribuyentes)")
            print("2. 🆔 Cédula de Identidad (V/E)")
            print("3. 🛒 CONSUMIDOR FINAL (Sin identificación)")
            print("="*60)
            opcion_ident = input(f"{self.COLOR_AMARILLO}🔹 Seleccione (1-3): {self.COLOR_RESET}").strip()
        
        idcliente = None
        cliente = None
        
        if opcion_ident == '1':
            print("\n📄 FACTURA CON RIF")
            print("="*40)
            print("Buscar cliente por RIF:")
            print("1. Buscar existente")
            print("2. Crear nuevo")
            subop = input(f"{self.COLOR_AMARILLO}🔹 Seleccione: {self.COLOR_RESET}").strip()
            
            if subop == '1':
                rif = input("Ingrese RIF (ej: J123456789): ").upper()
                cliente_simple = self.cliente_service.buscar_por_documento(rif)
                if cliente_simple:
                    idcliente = cliente_simple['idcliente']
                    cliente = self.cliente_service.obtener_por_id(idcliente)
                    print(f"✅ Cliente: {cliente['nombre']} {cliente['apellidos']}")
                else:
                    print("❌ Cliente no encontrado")
                    self.pausa()
                    return
            else:
                print("\n📝 CREAR NUEVO CLIENTE CON RIF")
                self._crear_cliente()
                print("\n✅ Cliente creado. Por favor, regístrelo en la venta")
                self.pausa()
                return
        
        elif opcion_ident == '2':
            print("\n🆔 FACTURA CON CÉDULA")
            print("="*40)
            print("Ingrese la cédula de identidad:")
            print("Formato: V12345678 o E87654321")
            cedula = input("Cédula: ").upper()
            
            if not (cedula.startswith('V') or cedula.startswith('E')):
                print("❌ Formato inválido. Debe comenzar con V o E")
                self.pausa()
                return
            
            cliente_simple = self.cliente_service.buscar_por_documento(cedula)
            
            if cliente_simple:
                idcliente = cliente_simple['idcliente']
                cliente = self.cliente_service.obtener_por_id(idcliente)
                print(f"✅ Cliente encontrado: {cliente['nombre']} {cliente['apellidos']}")
            else:
                print("\n📝 Cliente no registrado")
                print("¿Desea registrarlo ahora?")
                print("1. Sí, crear registro rápido")
                print("2. No, continuar como consumidor final")
                subop = input(f"{self.COLOR_AMARILLO}🔹 Seleccione: {self.COLOR_RESET}").strip()
                
                if subop == '1':
                    print("\n📝 DATOS MÍNIMOS DEL CLIENTE")
                    nombre = input("Nombre: ")
                    apellidos = input("Apellidos: ")
                    
                    tipo_doc = cedula[0]
                    num_doc = cedula[1:]
                    
                    if self.cliente_service.crear(
                        nombre, apellidos, None, tipo_doc, num_doc,
                        None, None, None, None
                    ):
                        print("✅ Cliente registrado exitosamente")
                        cliente_simple = self.cliente_service.buscar_por_documento(cedula)
                        if cliente_simple:
                            idcliente = cliente_simple['idcliente']
                            cliente = self.cliente_service.obtener_por_id(idcliente)
                    else:
                        print("❌ Error al registrar cliente")
                        self.pausa()
                        return
                else:
                    opcion_ident = '3'
        
        if opcion_ident == '3':
            print("\n🛒 CONSUMIDOR FINAL")
            print("="*40)
            print("✅ Venta sin identificación de cliente")
            idcliente = None
        
        # ===== MONEDA DE PAGO =====
        print("\n" + "="*60)
        print("💳 MONEDA DE PAGO")
        print("="*60)
        print("1. Dólares (USD)")
        print("2. Bolívares (VES)")
        print("3. Euros (EUR)")
        opcion_pago = input(f"{self.COLOR_AMARILLO}🔹 Seleccione moneda de pago: {self.COLOR_RESET}").strip()
        
        moneda_pago_map = {'1': 'USD', '2': 'VES', '3': 'EUR'}
        moneda_pago = moneda_pago_map.get(opcion_pago, 'USD')
        
        # ===== DATOS DEL COMPROBANTE =====
        print("\n" + "="*60)
        print("📄 DATOS DEL COMPROBANTE")
        print("="*60)
        
        if opcion_ident == '1':
            print("Tipo de comprobante:")
            print("  1. Factura (con RIF)")
            tipo_op = '1'
            tipo_comprobante = 'FACTURA'
        elif opcion_ident == '2':
            print("Tipo de comprobante:")
            print("  1. Factura (con Cédula)")
            print("  2. Boleta (consumo)")
            tipo_op = input(f"{self.COLOR_AMARILLO}Seleccione: {self.COLOR_RESET}").strip()
            tipo_comprobante = 'FACTURA' if tipo_op == '1' else 'BOLETA'
        else:
            print("Tipo de comprobante:")
            print("  1. Boleta (consumo final)")
            print("  2. Ticket (consumo final)")
            tipo_map = {'1': 'BOLETA', '2': 'TICKET'}
            tipo_op = input(f"{self.COLOR_AMARILLO}Seleccione: {self.COLOR_RESET}").strip()
            tipo_comprobante = tipo_map.get(tipo_op, 'BOLETA')
        
        serie = input("Serie (ej. F001): ")
        numero = input("Número: ")
        
        # ===== NUEVA INTERFAZ DE AGREGAR PRODUCTOS (SIN EL MALDITO "--- Agregar producto ---") =====
        detalle = []
        print("\n" + "="*60)
        print("🛒 AGREGAR PRODUCTOS")
        print("="*60)
        print(f"💡 {self.COLOR_VERDE}Seleccione una opción:{self.COLOR_RESET}")
        print(f"   {self.COLOR_VERDE}[1]{self.COLOR_RESET} Buscar por nombre")
        print(f"   {self.COLOR_VERDE}[2]{self.COLOR_RESET} Buscar por código")
        print(f"   {self.COLOR_VERDE}[3]{self.COLOR_RESET} Ver lista completa con precios")
        print(f"   {self.COLOR_VERDE}[4]{self.COLOR_RESET} Finalizar venta")
        print(f"💰 Tasa USD actual: {self.COLOR_AMARILLO}Bs. {tasa_usd:.2f}{self.COLOR_RESET}")
        print("="*60)
        
        while True:
            opcion_producto = input(f"{self.COLOR_AMARILLO}🔹 Seleccione opción (1-4): {self.COLOR_RESET}").strip()
            
            if opcion_producto == '4':
                break
            
            elif opcion_producto == '3':
                self._mostrar_lista_articulos()
                codigo_articulo = input(f"{self.COLOR_AMARILLO}🔹 Ingrese el código del artículo a agregar (0 para volver): {self.COLOR_RESET}").strip()
                
                if codigo_articulo == '0':
                    continue
                
                # Buscar el artículo por código
                art = self.articulo_service.buscar_por_codigo(codigo_articulo)
                if not art:
                    art = self.articulo_service.buscar_por_codigo_barras(codigo_articulo)
                
                if not art:
                    print(f"{self.COLOR_ROJO}❌ Artículo no encontrado{self.COLOR_RESET}")
                    continue
                
                # Procesar el artículo encontrado
                try:
                    precio_usd = float(art.get('precio_venta', 0))
                except:
                    precio_usd = 0.0
                
                if precio_usd <= 0:
                    print(f"{self.COLOR_AMARILLO}⚠️ Este artículo tiene precio $0. ¿Desea continuar? (s/N){self.COLOR_RESET}")
                    if input().lower() != 's':
                        continue
                
                stock = self.inventario_service.obtener_stock_articulo(art['idarticulo'])
                print(f"\n{self.COLOR_VERDE}📌 Artículo seleccionado:{self.COLOR_RESET}")
                print(f"   Nombre: {art['nombre']}")
                print(f"   Precio: ${precio_usd:.2f} USD")
                print(f"   Stock: {stock} und")
                
                try:
                    cantidad = int(input("Cantidad: "))
                    if cantidad <= 0:
                        print("❌ La cantidad debe ser positiva")
                        continue
                    if cantidad > stock:
                        print(f"❌ Stock insuficiente. Solo hay {stock} unidades")
                        continue
                except ValueError:
                    print("❌ Cantidad inválida")
                    continue
                
                subtotal_usd = float(cantidad) * float(precio_usd)
                subtotal_bs = subtotal_usd * float(tasa_usd)
                
                print(f"\n   Subtotal: ${subtotal_usd:.2f} USD = Bs. {subtotal_bs:.2f}")
                
                detalle.append({
                    'idarticulo': art['idarticulo'],
                    'cantidad': cantidad,
                    'precio_venta': precio_usd,
                    'nombre': art['nombre']
                })
                print(f"{self.COLOR_VERDE}✅ {art['nombre']} agregado{self.COLOR_RESET}")
                
                # Volver a mostrar el menú principal de productos
                print("\n" + "="*60)
                print("🛒 CONTINUAR AGREGANDO PRODUCTOS")
                print("="*60)
                print(f"💡 {self.COLOR_VERDE}Seleccione una opción:{self.COLOR_RESET}")
                print(f"   {self.COLOR_VERDE}[1]{self.COLOR_RESET} Buscar por nombre")
                print(f"   {self.COLOR_VERDE}[2]{self.COLOR_RESET} Buscar por código")
                print(f"   {self.COLOR_VERDE}[3]{self.COLOR_RESET} Ver lista completa con precios")
                print(f"   {self.COLOR_VERDE}[4]{self.COLOR_RESET} Finalizar venta")
                print("="*60)
                continue
            
            elif opcion_producto == '2':
                codigo = input("Ingrese código del artículo: ").strip()
                art = self.articulo_service.buscar_por_codigo(codigo)
                if not art:
                    art = self.articulo_service.buscar_por_codigo_barras(codigo)
                
                if not art:
                    print(f"{self.COLOR_ROJO}❌ Artículo no encontrado{self.COLOR_RESET}")
                    continue
                
                # Procesar el artículo encontrado
                try:
                    precio_usd = float(art.get('precio_venta', 0))
                except:
                    precio_usd = 0.0
                
                if precio_usd <= 0:
                    print(f"{self.COLOR_AMARILLO}⚠️ Este artículo tiene precio $0. ¿Desea continuar? (s/N){self.COLOR_RESET}")
                    if input().lower() != 's':
                        continue
                
                stock = self.inventario_service.obtener_stock_articulo(art['idarticulo'])
                print(f"\n{self.COLOR_VERDE}📌 Artículo encontrado:{self.COLOR_RESET}")
                print(f"   Nombre: {art['nombre']}")
                print(f"   Precio: ${precio_usd:.2f} USD")
                print(f"   Stock: {stock} und")
                
                try:
                    cantidad = int(input("Cantidad: "))
                    if cantidad <= 0:
                        print("❌ La cantidad debe ser positiva")
                        continue
                    if cantidad > stock:
                        print(f"❌ Stock insuficiente. Solo hay {stock} unidades")
                        continue
                except ValueError:
                    print("❌ Cantidad inválida")
                    continue
                
                subtotal_usd = float(cantidad) * float(precio_usd)
                subtotal_bs = subtotal_usd * float(tasa_usd)
                
                print(f"\n   Subtotal: ${subtotal_usd:.2f} USD = Bs. {subtotal_bs:.2f}")
                
                detalle.append({
                    'idarticulo': art['idarticulo'],
                    'cantidad': cantidad,
                    'precio_venta': precio_usd,
                    'nombre': art['nombre']
                })
                print(f"{self.COLOR_VERDE}✅ {art['nombre']} agregado{self.COLOR_RESET}")
                
                # Volver a mostrar el menú principal de productos
                print("\n" + "="*60)
                print("🛒 CONTINUAR AGREGANDO PRODUCTOS")
                print("="*60)
                print(f"💡 {self.COLOR_VERDE}Seleccione una opción:{self.COLOR_RESET}")
                print(f"   {self.COLOR_VERDE}[1]{self.COLOR_RESET} Buscar por nombre")
                print(f"   {self.COLOR_VERDE}[2]{self.COLOR_RESET} Buscar por código")
                print(f"   {self.COLOR_VERDE}[3]{self.COLOR_RESET} Ver lista completa con precios")
                print(f"   {self.COLOR_VERDE}[4]{self.COLOR_RESET} Finalizar venta")
                print("="*60)
                continue
            
            elif opcion_producto == '1':
                nombre = input("Ingrese nombre del artículo: ").strip()
                resultados = self.articulo_service.buscar_por_nombre(nombre)
                
                if not resultados:
                    print(f"{self.COLOR_ROJO}❌ No se encontraron artículos{self.COLOR_RESET}")
                    continue
                
                if len(resultados) == 1:
                    art = resultados[0]
                else:
                    print(f"\n{self.COLOR_VERDE}📋 Múltiples resultados:{self.COLOR_RESET}")
                    for i, a in enumerate(resultados, 1):
                        precio = float(a.get('precio_venta', 0))
                        if precio == int(precio):
                            precio_str = f"${int(precio)}"
                        else:
                            precio_str = f"${precio:.2f}".rstrip('0').rstrip('.')
                        print(f"  {i}. {a['nombre']} ({precio_str})")
                    try:
                        selec = int(input("Seleccione número: ")) - 1
                        if 0 <= selec < len(resultados):
                            art = resultados[selec]
                        else:
                            print("❌ Selección inválida")
                            continue
                    except:
                        print("❌ Selección inválida")
                        continue
                
                # Procesar el artículo seleccionado
                try:
                    precio_usd = float(art.get('precio_venta', 0))
                except:
                    precio_usd = 0.0
                
                if precio_usd <= 0:
                    print(f"{self.COLOR_AMARILLO}⚠️ Este artículo tiene precio $0. ¿Desea continuar? (s/N){self.COLOR_RESET}")
                    if input().lower() != 's':
                        continue
                
                stock = self.inventario_service.obtener_stock_articulo(art['idarticulo'])
                print(f"\n{self.COLOR_VERDE}📌 Artículo seleccionado:{self.COLOR_RESET}")
                print(f"   Nombre: {art['nombre']}")
                print(f"   Precio: ${precio_usd:.2f} USD")
                print(f"   Stock: {stock} und")
                
                try:
                    cantidad = int(input("Cantidad: "))
                    if cantidad <= 0:
                        print("❌ La cantidad debe ser positiva")
                        continue
                    if cantidad > stock:
                        print(f"❌ Stock insuficiente. Solo hay {stock} unidades")
                        continue
                except ValueError:
                    print("❌ Cantidad inválida")
                    continue
                
                subtotal_usd = float(cantidad) * float(precio_usd)
                subtotal_bs = subtotal_usd * float(tasa_usd)
                
                print(f"\n   Subtotal: ${subtotal_usd:.2f} USD = Bs. {subtotal_bs:.2f}")
                
                detalle.append({
                    'idarticulo': art['idarticulo'],
                    'cantidad': cantidad,
                    'precio_venta': precio_usd,
                    'nombre': art['nombre']
                })
                print(f"{self.COLOR_VERDE}✅ {art['nombre']} agregado{self.COLOR_RESET}")
                
                # Volver a mostrar el menú principal de productos
                print("\n" + "="*60)
                print("🛒 CONTINUAR AGREGANDO PRODUCTOS")
                print("="*60)
                print(f"💡 {self.COLOR_VERDE}Seleccione una opción:{self.COLOR_RESET}")
                print(f"   {self.COLOR_VERDE}[1]{self.COLOR_RESET} Buscar por nombre")
                print(f"   {self.COLOR_VERDE}[2]{self.COLOR_RESET} Buscar por código")
                print(f"   {self.COLOR_VERDE}[3]{self.COLOR_RESET} Ver lista completa con precios")
                print(f"   {self.COLOR_VERDE}[4]{self.COLOR_RESET} Finalizar venta")
                print("="*60)
                continue
            
            else:
                print(f"{self.COLOR_ROJO}❌ Opción no válida. Use 1-4{self.COLOR_RESET}")
        
        if not detalle:
            print("❌ Debe agregar al menos un producto")
            self.pausa()
            return
        
        # ===== RESUMEN DE VENTA =====
        print("\n" + "="*60)
        print("📋 RESUMEN DE VENTA")
        print("="*60)
        
        if opcion_ident == '1' and cliente:
            print(f"Tipo: FACTURA CON RIF")
            print(f"Cliente: {cliente['nombre']} {cliente['apellidos']}")
            print(f"RIF: {cliente['tipo_documento']}-{cliente['num_documento']}")
        elif opcion_ident == '2' and cliente:
            print(f"Tipo: FACTURA CON CÉDULA")
            print(f"Cliente: {cliente['nombre']} {cliente['apellidos']}")
            print(f"Cédula: {cliente['tipo_documento']}-{cliente['num_documento']}")
        else:
            print(f"Tipo: {tipo_comprobante} - CONSUMIDOR FINAL")
            print("Cliente: No identificado")
            print(f"ℹ️ {MENSAJES_LEGALES['consumidor_final']}")
        
        print(f"Moneda pago: {moneda_pago}")
        print(f"Tasa USD: Bs. {tasa_usd:.2f}")
        print(f"Comprobante: {tipo_comprobante} {serie}-{numero}")
        print("\n" + "-"*60)
        print("PRODUCTOS:")
        print("-"*60)
        
        total_usd = 0.0
        for item in detalle:
            cantidad = float(item['cantidad'])
            precio = float(item['precio_venta'])
            subtotal_usd = cantidad * precio
            total_usd += subtotal_usd
            if cantidad.is_integer():
                print(f"  {item['nombre']:<30} x{int(cantidad):<3}  ${precio:.2f}  = ${subtotal_usd:.2f}")
            else:
                print(f"  {item['nombre']:<30} x{cantidad:<3}  ${precio:.2f}  = ${subtotal_usd:.2f}")
        
        iva_total_usd = total_usd * 0.16
        total_con_iva_usd = total_usd + iva_total_usd
        total_con_iva_bs = total_con_iva_usd * float(tasa_usd)
        
        print("-"*60)
        print(f"{'SUBTOTAL:':<40} ${total_usd:.2f}")
        print(f"{'IVA (16%):':<40} ${iva_total_usd:.2f}")
        print(f"{'TOTAL USD:':<40} ${total_con_iva_usd:.2f}")
        print(f"{'TOTAL Bs.:':<40} Bs. {total_con_iva_bs:.2f}")
        print("="*60)
        
        confirmar = input(f"\n{self.COLOR_AMARILLO}¿Confirmar venta? (s/N): {self.COLOR_RESET}").lower()
        if confirmar != 's':
            print("Operación cancelada")
            self.pausa()
            return
        
        # ===== REGISTRAR VENTA =====
        idventa = self.venta_service.registrar(
            usuario['idtrabajador'], 
            idcliente,
            tipo_comprobante,
            serie, 
            numero, 
            16.0,
            detalle,
            moneda='USD',
            moneda_pago=moneda_pago,
            tasa_cambio=tasa_usd
        )
        
        if idventa:
            print(f"\n{self.COLOR_VERDE}✅ Venta #{idventa} registrada correctamente{self.COLOR_RESET}")
            print("="*60)
            print("🎫 DATOS DE LA FACTURA:")
            print(f"   Número: {tipo_comprobante} {serie}-{numero}")
            
            if opcion_ident == '1' and cliente:
                print(f"   Cliente: {cliente['nombre']} {cliente['apellidos']}")
                print(f"   RIF: {cliente['tipo_documento']}-{cliente['num_documento']}")
            elif opcion_ident == '2' and cliente:
                print(f"   Cliente: {cliente['nombre']} {cliente['apellidos']}")
                print(f"   Cédula: {cliente['tipo_documento']}-{cliente['num_documento']}")
            else:
                print("   Cliente: CONSUMIDOR FINAL")
                print("   Identificación: No aplica")
            
            print(f"   Total USD: ${total_con_iva_usd:.2f}")
            print(f"   Total Bs.: Bs. {total_con_iva_bs:.2f}")
            print(f"   Tasa aplicada: {tasa_usd:.2f}")
            print(f"   Moneda pago: {moneda_pago}")
            print(f"   {MENSAJES_LEGALES['factura_digital']}")
            print("="*60)
            
            # Preguntar si desea imprimir factura
            imprimir = input(f"\n{self.COLOR_AMARILLO}¿Desea imprimir la factura? (s/N): {self.COLOR_RESET}").lower()
            if imprimir == 's':
                self._imprimir_factura(idventa)
            
            tipo_cliente = "CONSUMIDOR FINAL" if not idcliente else "CLIENTE IDENTIFICADO"
            self.registrar_auditoria(
                accion="CREAR",
                tabla="venta",
                registro_id=idventa,
                datos_nuevos=f"Venta #{idventa} - {tipo_cliente} - Total: ${total_con_iva_usd:.2f} (Bs. {total_con_iva_bs:.2f})"
            )
        else:
            print(f"\n{self.COLOR_ROJO}❌ Error al registrar la venta{self.COLOR_RESET}")
        
        self.pausa()

    def _continuar_flujo_venta(self, usuario, idcliente, cliente, opcion_ident):
        """Continuación del flujo de venta después de seleccionar cliente"""
        
        # Obtener tasas actuales
        tasas_actuales = self.obtener_tasas_actuales()
        tasa_usd = tasas_actuales.get('USD', 0)
        
        # ===== MONEDA DE PAGO =====
        print("\n" + "="*60)
        print("💳 MONEDA DE PAGO")
        print("="*60)
        print("1. Dólares (USD)")
        print("2. Bolívares (VES)")
        print("3. Euros (EUR)")
        opcion_pago = input(f"{self.COLOR_AMARILLO}🔹 Seleccione moneda de pago: {self.COLOR_RESET}").strip()
        
        moneda_pago_map = {'1': 'USD', '2': 'VES', '3': 'EUR'}
        moneda_pago = moneda_pago_map.get(opcion_pago, 'USD')
        
        # ===== DATOS DEL COMPROBANTE =====
        print("\n" + "="*60)
        print("📄 DATOS DEL COMPROBANTE")
        print("="*60)
        
        if opcion_ident == '1':
            print("Tipo de comprobante:")
            print("  1. Factura (con RIF)")
            tipo_op = '1'
            tipo_comprobante = 'FACTURA'
        elif opcion_ident == '2':
            print("Tipo de comprobante:")
            print("  1. Factura (con Cédula)")
            print("  2. Boleta (consumo)")
            tipo_op = input(f"{self.COLOR_AMARILLO}Seleccione: {self.COLOR_RESET}").strip()
            tipo_comprobante = 'FACTURA' if tipo_op == '1' else 'BOLETA'
        else:
            print("Tipo de comprobante:")
            print("  1. Boleta (consumo final)")
            print("  2. Ticket (consumo final)")
            tipo_map = {'1': 'BOLETA', '2': 'TICKET'}
            tipo_op = input(f"{self.COLOR_AMARILLO}Seleccione: {self.COLOR_RESET}").strip()
            tipo_comprobante = tipo_map.get(tipo_op, 'BOLETA')
        
        serie = input("Serie (ej. F001): ")
        numero = input("Número: ")
        
        # ===== AGREGAR PRODUCTOS =====
        detalle = []
        print("\n" + "="*50)
        print("🛒 AGREGAR PRODUCTOS")
        print("="*50)
        print(f"{self.COLOR_VERDE}💡 Use '?' para ver lista, '*' para búsqueda avanzada{self.COLOR_RESET}")
        print(f"{self.COLOR_AMARILLO}💰 Tasa USD actual: Bs. {tasa_usd:.2f}{self.COLOR_RESET}")
        
        while True:
            print("\n--- Agregar producto ---")
            entrada = input("Código/PLU (0=terminar, ?=lista, *=búsqueda): ").lower()
            
            if entrada == '0':
                break
            elif entrada == '?':
                self._mostrar_lista_articulos()
                continue
            elif entrada == '*':
                art = self._buscar_articulo_para_venta()
                if not art:
                    continue
            else:
                art = self.articulo_service.buscar_por_codigo(entrada)
                if not art:
                    art = self.articulo_service.buscar_por_codigo_barras(entrada)
            
            if not art:
                print(f"{self.COLOR_ROJO}❌ Artículo no encontrado. Use '*' para búsqueda avanzada{self.COLOR_RESET}")
                continue
            
            precio_usd = art.get('precio_venta', 0)
            stock = self.inventario_service.obtener_stock_articulo(art['idarticulo'])
            
            print(f"📌 Artículo: {art['nombre']}")
            print(f"   Precio: ${precio_usd:.2f} USD")
            print(f"   Stock: {stock} und")
            
            try:
                if art.get('tipo_medida') == 'PESO':
                    cantidad = float(input("Cantidad (kg): "))
                else:
                    cantidad = int(input("Cantidad (unidades): "))
                
                if cantidad > stock and art.get('tipo_medida') != 'PESO':
                    print(f"❌ Stock insuficiente")
                    continue
            except:
                print("❌ Cantidad inválida")
                continue
            
            detalle.append({
                'idarticulo': art['idarticulo'],
                'cantidad': cantidad,
                'precio_venta': precio_usd,
                'nombre': art['nombre']
            })
            print(f"✅ {art['nombre']} agregado")
        
        if not detalle:
            print("❌ Debe agregar al menos un producto")
            self.pausa()
            return
        
        # ===== RESUMEN =====
        total_usd = sum(item['cantidad'] * item['precio_venta'] for item in detalle)
        iva_usd = total_usd * 0.16
        total_con_iva_usd = total_usd + iva_usd
        total_bs = total_con_iva_usd * tasa_usd
        
        print("\n" + "="*50)
        print("📋 RESUMEN DE VENTA")
        print("="*50)
        for item in detalle:
            print(f"  - {item['nombre']}: {item['cantidad']} x ${item['precio_venta']:.2f} = ${item['cantidad'] * item['precio_venta']:.2f}")
        print(f"\n💰 TOTAL USD: ${total_con_iva_usd:.2f}")
        print(f"💰 TOTAL Bs.: Bs. {total_bs:.2f} (tasa {tasa_usd:.2f})")
        print("="*50)
        
        confirmar = input(f"{self.COLOR_AMARILLO}¿Confirmar venta? (s/N): {self.COLOR_RESET}").lower()
        if confirmar != 's':
            print("Operación cancelada")
            self.pausa()
            return
        
        # ===== REGISTRAR =====
        idventa = self.venta_service.registrar(
            usuario['idtrabajador'], 
            idcliente,
            tipo_comprobante,
            serie, 
            numero, 
            16.0,
            detalle,
            moneda='USD',
            moneda_pago=moneda_pago,
            tasa_cambio=tasa_usd
        )
        
        if idventa:
            print(f"\n{self.COLOR_VERDE}✅ Venta #{idventa} registrada correctamente{self.COLOR_RESET}")
            self.registrar_auditoria(
                accion="CREAR",
                tabla="venta",
                registro_id=idventa,
                datos_nuevos=f"Venta #{idventa} - Total: ${total_con_iva_usd:.2f} (Bs. {total_bs:.2f})"
            )
        else:
            print(f"\n{self.COLOR_ROJO}❌ Error al registrar la venta{self.COLOR_RESET}")
        
        self.pausa()

    def _imprimir_factura_rapido(self, usuario):
        """Atajo para imprimir la última factura o buscar por ID"""
        import platform
        sistema = platform.system()
        atajo = "F11" if sistema == "Windows" else "4"
        
        print(f"\n{self.COLOR_VERDE}🖨️ IMPRIMIR FACTURA (Atajo {atajo}){self.COLOR_RESET}")
        print("="*60)
        print("1. Imprimir última factura")
        print("2. Buscar factura por ID")
        print("3. Volver")
        opcion = input(f"{self.COLOR_AMARILLO}🔹 Seleccione: {self.COLOR_RESET}").strip()
        
        if opcion == '1':
            # Obtener la última venta
            ventas = self.venta_service.listar()
            if ventas:
                ultima_venta = ventas[0]
                self._imprimir_factura(ultima_venta['idventa'])
            else:
                print(f"{self.COLOR_ROJO}❌ No hay ventas registradas{self.COLOR_RESET}")
                self.pausa()
        
        elif opcion == '2':
            try:
                idventa = int(input("ID de la factura a imprimir: "))
                self._imprimir_factura(idventa)
            except:
                print(f"{self.COLOR_ROJO}❌ ID inválido{self.COLOR_RESET}")
                self.pausa()
        
        return self._registrar_venta()

    def _imprimir_factura(self, idventa):
        """Imprime una factura en formato texto"""
        venta = self.venta_service.obtener_por_id(idventa)
        
        if not venta:
            print(f"{self.COLOR_ROJO}❌ Factura {idventa} no encontrada{self.COLOR_RESET}")
            return
        
        print("\n" + "="*50)
        print("🖨️ IMPRIMIENDO FACTURA")
        print("="*50)
        print(f"FACTURA #{venta['idventa']}")
        print(f"Fecha: {venta['fecha']}")
        print(f"Cliente: {venta.get('cliente', 'CONSUMIDOR FINAL')}")
        print(f"Comprobante: {venta['tipo_comprobante']} {venta['serie']}-{venta['numero_comprobante']}")
        print("-"*50)
        print("PRODUCTOS:")
        total = 0
        for d in venta.get('detalle', []):
            subtotal = d['cantidad'] * d['precio_venta']
            total += subtotal
            print(f"  {d['articulo']} x{d['cantidad']} @ {d['precio_venta']:.2f} = {subtotal:.2f}")
        print("-"*50)
        print(f"TOTAL: {total:.2f}")
        print("="*50)
        print("¡Gracias por su compra!")
        print("="*50)
        
        # Aquí iría la lógica para enviar a impresora física
        print(f"\n{self.COLOR_VERDE}✅ Factura enviada a imprimir{self.COLOR_RESET}")
        self.pausa()

    def _buscar_por_cedula_rapido(self, usuario):
        """Búsqueda rápida por cédula (compatible Windows/Linux)"""
        import platform
        sistema = platform.system()
        atajo = "F9" if sistema == "Windows" else "2"
        print(f"\n{self.COLOR_VERDE}🔍 BÚSQUEDA RÁPIDA POR CÉDULA (Atajo {atajo}){self.COLOR_RESET}")
        print("="*60)
        
        cedula = input("Ingrese cédula (ej: V12345678): ").upper()
        
        if not (cedula.startswith('V') or cedula.startswith('E')):
            print(f"{self.COLOR_ROJO}❌ Formato inválido{self.COLOR_RESET}")
            self.pausa()
            return self._registrar_venta()
        
        cliente_simple = self.cliente_service.buscar_por_documento(cedula)
        
        if cliente_simple:
            idcliente = cliente_simple['idcliente']
            cliente = self.cliente_service.obtener_por_id(idcliente)
            print(f"{self.COLOR_VERDE}✅ Cliente encontrado: {cliente['nombre']} {cliente['apellidos']}{self.COLOR_RESET}")
            
            if cliente['tipo_documento'] in ['V', 'E']:
                opcion_ident = '2'
            else:
                opcion_ident = '1'
            
            return self._continuar_flujo_venta(usuario, idcliente, cliente, opcion_ident)
        else:
            print(f"{self.COLOR_AMARILLO}⚠️ Cliente no encontrado{self.COLOR_RESET}")
            print("1. Registrar nuevo cliente")
            print("2. Continuar como consumidor final")
            print("3. Volver")
            opcion = input(f"{self.COLOR_AMARILLO}🔹 Seleccione: {self.COLOR_RESET}").strip()
            
            if opcion == '1':
                self._crear_cliente()
                return self._registrar_venta()
            elif opcion == '2':
                return self._continuar_venta_consumidor_final(usuario)
            else:
                return self._registrar_venta()

    def _buscar_por_rif_rapido(self, usuario):
        """Búsqueda rápida por RIF (compatible Windows/Linux)"""
        import platform
        sistema = platform.system()
        atajo = "F10" if sistema == "Windows" else "3"
        print(f"\n{self.COLOR_VERDE}🔍 BÚSQUEDA RÁPIDA POR RIF (Atajo {atajo}){self.COLOR_RESET}")
        print("="*60)
        
        rif = input("Ingrese RIF (ej: J123456789): ").upper()
        
        if not rif:
            print(f"{self.COLOR_ROJO}❌ RIF no ingresado{self.COLOR_RESET}")
            self.pausa()
            return self._registrar_venta()
        
        cliente_simple = self.cliente_service.buscar_por_documento(rif)
        
        if cliente_simple:
            idcliente = cliente_simple['idcliente']
            cliente = self.cliente_service.obtener_por_id(idcliente)
            print(f"{self.COLOR_VERDE}✅ Cliente encontrado: {cliente['nombre']} {cliente['apellidos']}{self.COLOR_RESET}")
            
            if cliente['tipo_documento'] in ['J', 'G', 'C']:
                opcion_ident = '1'
            else:
                opcion_ident = '2'
            
            return self._continuar_flujo_venta(usuario, idcliente, cliente, opcion_ident)
        else:
            print(f"{self.COLOR_AMARILLO}⚠️ Cliente con RIF {rif} no encontrado{self.COLOR_RESET}")
            print("1. Registrar nuevo cliente")
            print("2. Volver")
            opcion = input(f"{self.COLOR_AMARILLO}🔹 Seleccione: {self.COLOR_RESET}").strip()
            
            if opcion == '1':
                self._crear_cliente()
                return self._registrar_venta()
            else:
                return self._registrar_venta()

    def _continuar_venta_consumidor_final(self, usuario):
        """Continúa con venta a consumidor final"""
        print(f"\n{self.COLOR_VERDE}🛒 Venta a CONSUMIDOR FINAL{self.COLOR_RESET}")
        idcliente = None
        cliente = None
        opcion_ident = '3'
        
        return self._continuar_flujo_venta(usuario, idcliente, cliente, opcion_ident)
    
    def _continuar_venta_con_cliente(self, idcliente, cliente):
        """Continúa el flujo de venta con un cliente ya seleccionado"""
        # Aquí iría la continuación de la venta
        # Por ahora, redirigimos al método principal con los datos
        print(f"\nContinuando venta con cliente: {cliente['nombre']} {cliente['apellidos']}")
        # Este método debería continuar con el flujo normal
        # Por ahora, volvemos al menú principal de ventas
        self.pausa()
        self.menu_ventas()
    
    def _mostrar_lista_articulos(self):
        """Muestra lista de artículos disponibles con precios"""
        articulos = self.articulo_service.listar()
        print("\n" + "="*107)
        print("📋 LISTADO DE ARTÍCULOS DISPONIBLES")
        print("="*107)
        print(f"{'ID':<5} {'CÓDIGO':<15} {'NOMBRE':<30} {'CATEGORÍA':<20} {'PRECIO $':<12} {'STOCK':<10}")
        print("-" * 107)
        for a in articulos:
            stock = self.inventario_service.obtener_stock_articulo(a['idarticulo'])
            precio = float(a.get('precio_venta', 0))
            
            # Formatear precio
            if precio == int(precio):
                precio_str = f"${int(precio)}"
            else:
                precio_str = f"${precio:.2f}".rstrip('0').rstrip('.')
            
            print(f"{a['idarticulo']:<5} {a['codigo']:<15} {a['nombre']:<30} {a.get('categoria', 'N/A'):<20} {precio_str:<12} {stock} und")
        print("-" * 107)

    # ======================================================
    # NUEVOS MÉTODOS DE BÚSQUEDA PARA VENTAS
    # ======================================================
    
    def _buscar_articulo_para_venta(self):
        """
        Menú de búsqueda de artículos durante la venta
        """
        self.mostrar_cabecera("🔍 BUSCAR ARTÍCULO")
        
        print("Opciones de búsqueda:")
        print("1. 🔎 Escanear código de barras")
        print("2. ⌨️ Ingresar código manualmente")
        print("3. 📝 Buscar por nombre")
        print("4. ↩️ Volver")
        
        opcion = input(f"{self.COLOR_AMARILLO}🔹 Seleccione: {self.COLOR_RESET}").strip()
        
        if opcion == '1':
            codigo = input("Ingrese código de barras: ").strip()
            return self._buscar_articulo_por_codigo(codigo)
        
        elif opcion == '2':
            codigo = input("Ingrese código manual: ").strip()
            art = self.articulo_service.buscar_por_codigo(codigo)
            if not art:
                art = self.articulo_service.buscar_por_codigo_barras(codigo)
            if art:
                return art
            print(f"{self.COLOR_ROJO}❌ Artículo no encontrado{self.COLOR_RESET}")
            return None
        
        elif opcion == '3':
            termino = input("Ingrese nombre: ").strip()
            # CORREGIDO: usar _buscar_articulo_por_nombre en lugar de _buscar_por_nombre
            return self._buscar_articulo_por_nombre(termino)
        
        else:
            return None
    
    def _buscar_articulo_por_codigo(self, codigo):
        """
        NUEVO: Busca artículo por código de barras (con soporte para balanza)
        """
        # Intentar buscar por código de barras exacto
        articulo = self.articulo_service.buscar_por_codigo_barras(codigo)
        
        if articulo:
            return articulo
        
        # Si no encuentra, verificar si es código de balanza (prefijo 21)
        if codigo.startswith('21') and len(codigo) == 13:
            return self._procesar_codigo_balanza(codigo)
        
        print(f"{self.COLOR_ROJO}❌ Artículo no encontrado{self.COLOR_RESET}")
        return None
    
    def _procesar_codigo_balanza(self, codigo):
        """
        Procesa códigos de balanza (prefijo 21)
        """
        try:
            # Extraer PLU (posiciones 3-7)
            plu = codigo[2:7].lstrip('0') or '0'
            
            # Extraer peso (posiciones 8-12) convertido a kg
            peso_gramos = int(codigo[7:12])
            peso_kg = peso_gramos / 1000
            
            # Buscar artículo por PLU
            articulo = self.articulo_service.buscar_por_plu(plu)
            
            if articulo:
                # Crear una copia del artículo con datos calculados
                resultado = articulo.copy()
                
                if articulo.get('es_pesado'):
                    precio_por_kilo = float(articulo.get('precio_por_kilo', 0))
                    precio_calculado = precio_por_kilo * peso_kg
                    resultado['precio_calculado'] = precio_calculado
                    resultado['cantidad'] = peso_kg
                    resultado['unidad'] = 'kg'
                    print(f"✅ {articulo['nombre']} - {peso_kg:.3f} kg")
                
                return resultado
            
        except Exception as e:
            logger.error(f"Error procesando código de balanza: {e}")
        
        return None
    
    def _buscar_articulo_por_nombre(self, termino):
        """
        NUEVO: Busca artículos por nombre y muestra lista para seleccionar
        """
        resultados = self.articulo_service.buscar_por_nombre(termino)
        
        if not resultados:
            print(f"{self.COLOR_ROJO}❌ No se encontraron artículos{self.COLOR_RESET}")
            return None
        
        print(f"\n{self.COLOR_VERDE}📋 RESULTADOS ({len(resultados)}):{self.COLOR_RESET}")
        print(f"{'#':<3} {'CÓDIGO':<15} {'NOMBRE':<50} {'PRECIO':<10}")
        print("-" * 78)
        
        for i, art in enumerate(resultados, 1):
            precio = art.get('precio_venta', 0)
            print(f"{i:<3} {art['codigo']:<15} {art['nombre']:<50} {precio:>10.2f}")
        
        try:
            seleccion = input(f"\n{self.COLOR_AMARILLO}Seleccione número (Enter para cancelar): {self.COLOR_RESET}").strip()
            if seleccion:
                idx = int(seleccion) - 1
                if 0 <= idx < len(resultados):
                    return resultados[idx]
        except:
            pass
        
        return None

    # ======================================================
    # NUEVOS MÉTODOS DE BÚSQUEDA PARA GESTIÓN DE ARTÍCULOS
    # ======================================================
    
    def _buscar_articulo_gestion(self):
        """
        NUEVO: Busca artículos en gestión (por código o nombre)
        """
        self.mostrar_cabecera("🔍 BUSCAR ARTÍCULO")
        
        print("Buscar por:")
        print("1. 📦 Código de barras")
        print("2. 📝 Nombre")
        print("3. 🔢 Código interno (PLU)")
        print("4. ↩️ Volver")
        
        opcion = input(f"{self.COLOR_AMARILLO}🔹 Seleccione: {self.COLOR_RESET}").strip()
        
        if opcion == '1':
            codigo = input("Ingrese código de barras: ").strip()
            self._mostrar_resultado_busqueda(codigo, 'codigo')
        
        elif opcion == '2':
            termino = input("Ingrese nombre: ").strip()
            self._mostrar_resultado_busqueda(termino, 'nombre')
        
        elif opcion == '3':
            plu = input("Ingrese PLU: ").strip()
            self._mostrar_resultado_busqueda(plu, 'plu')
        
        self.pausa()
    
    def _mostrar_resultado_busqueda(self, valor, tipo):
        """
        Muestra resultados de búsqueda según el tipo
        """
        if tipo == 'codigo':
            articulo = self.articulo_service.buscar_por_codigo_barras(valor)
            if articulo:
                self._mostrar_detalle_articulo(articulo)
            else:
                print(f"{self.COLOR_ROJO}❌ Artículo no encontrado{self.COLOR_RESET}")
        
        elif tipo == 'plu':
            articulo = self.articulo_service.buscar_por_plu(valor)
            if articulo:
                self._mostrar_detalle_articulo(articulo)
            else:
                print(f"{self.COLOR_ROJO}❌ Artículo con PLU {valor} no encontrado{self.COLOR_RESET}")
        
        elif tipo == 'nombre':
            resultados = self.articulo_service.buscar_por_nombre(valor)
            if resultados:
                print(f"\n{self.COLOR_VERDE}📋 RESULTADOS ({len(resultados)}):{self.COLOR_RESET}")
                print(f"{'ID':<5} {'CÓDIGO':<15} {'NOMBRE':<40} {'PRECIO':<12}")
                print("-" * 72)
                for art in resultados:
                    precio = art.get('precio_venta', 0)
                    print(f"{art['idarticulo']:<5} {art['codigo']:<15} {art['nombre']:<40} Bs.{precio:>10,.2f}")
                
                # Opción de editar desde resultados
                print("\n" + "-" * 30)
                editar = input(f"{self.COLOR_AMARILLO}¿Editar algún artículo? (ID o Enter para continuar): {self.COLOR_RESET}").strip()
                if editar.isdigit():
                    self._editar_articulo_por_id(int(editar))
            else:
                print(f"{self.COLOR_ROJO}❌ No se encontraron artículos{self.COLOR_RESET}")
    
    @requiere_permiso('ventas_ver')
    def _listar_ventas(self):
        """Lista todas las ventas con fecha, hora y montos"""
        self.mostrar_cabecera("LISTADO DE VENTAS")
        
        ventas = self.venta_service.listar()
        
        if not ventas:
            print("📭 No hay ventas registradas")
        else:
            # Cabecera con columna de MONTO
            print(f"{'ID':<5} {'FECHA Y HORA':<19} {'COMPROBANTE':<20} {'CLIENTE':<20} {'MONTO':<15} {'ESTADO':<10}")
            print("-" * 89)
            
            for v in ventas:
                comp = f"{v['tipo_comprobante']} {v['serie']}-{v['numero_comprobante']}"
                
                # Manejar cliente
                cliente_nombre = v.get('cliente')
                if cliente_nombre is None:
                    cliente_nombre = 'CONSUMIDOR FINAL'
                
                # Truncar cliente si es muy largo
                if len(cliente_nombre) > 20:
                    cliente_nombre = cliente_nombre[:17] + "..."
                
                # Determinar monto y moneda
                moneda = v.get('moneda', 'VES')
                
                if moneda == 'USD':
                    monto = v.get('monto_divisa', 0)
                    if monto:
                        monto_str = f"${monto:,.2f}"
                    else:
                        monto_str = "$0.00"
                elif moneda == 'EUR':
                    monto = v.get('monto_divisa', 0)
                    if monto:
                        monto_str = f"€{monto:,.2f}"
                    else:
                        monto_str = "€0.00"
                else:  # VES
                    monto = v.get('monto_bs', v.get('total', 0))
                    if monto:
                        monto_str = f"Bs. {monto:,.2f}".replace(',', ' ')
                    else:
                        monto_str = "Bs. 0.00"
                
                # Truncar monto si es muy largo
                if len(monto_str) > 15:
                    monto_str = monto_str[:12] + "..."
                
                print(f"{v['idventa']:<5} {v['fecha']:<19} {comp:<20} {cliente_nombre:<20} {monto_str:<15} {v['estado']:<10}")
        
        self.pausa()

    def _ver_venta(self):
        """Muestra detalle de una venta con hora exacta"""
        self.mostrar_cabecera("DETALLE DE VENTA")
        
        try:
            idventa = int(input("ID de la venta: "))
            venta = self.venta_service.obtener_por_id(idventa)
            
            if not venta:
                print(f"❌ No existe venta con ID {idventa}")
                self.pausa()
                return
            
            print(f"\n📌 Venta N°: {venta['idventa']}")
            print(f"📌 Fecha y Hora: {venta['fecha']}")
            
            # CORREGIDO: Manejar cliente cuando es None
            cliente_nombre = venta.get('cliente')
            if cliente_nombre is None:
                cliente_nombre = 'CONSUMIDOR FINAL'
                
            print(f"📌 Cliente: {cliente_nombre}")
            print(f"📌 Comprobante: {venta['tipo_comprobante']} {venta['serie']}-{venta['numero_comprobante']}")
            print(f"📌 IGV: {venta['igv']}%")
            print(f"📌 Estado: {venta['estado']}")
            print(f"📌 Trabajador: {venta['trabajador']}")
            
            if venta.get('detalle'):
                print("\n📋 DETALLE:")
                total = 0
                for d in venta['detalle']:
                    subtotal = d['cantidad'] * d['precio_venta']
                    total += subtotal
                    print(f"   - {d['articulo']} x{d['cantidad']} @ {d['precio_venta']:.2f} = {subtotal:.2f}")
                print(f"\n💰 TOTAL: {total:.2f}")
                
            print("\n📋 REGISTROS DE AUDITORÍA:")
            logs = self.auditoria_service.consultar_por_tabla("venta", idventa)
            for log in logs:
                fecha_log = log['fecha_hora'].strftime('%d/%m/%Y %H:%M') if hasattr(log['fecha_hora'], 'strftime') else log['fecha_hora']
                print(f"   - {fecha_log}: {log['accion']}")
        
        except Exception as e:
            print(f"❌ Error: {e}")
        
        self.pausa()
    def _anular_venta(self):
        """Anula una venta"""
        self.mostrar_cabecera("ANULAR VENTA")
        
        try:
            idventa = int(input("ID de la venta a anular: "))
            venta = self.venta_service.obtener_por_id(idventa)
            
            if not venta:
                print(f"❌ No existe venta con ID {idventa}")
                self.pausa()
                return
            
            if venta['estado'] == 'ANULADO':
                print("⚠️ Esta venta ya está anulada")
                self.pausa()
                return
            
            cliente_nombre = venta.get('cliente', 'CONSUMIDOR FINAL')
            print(f"\nVenta: {venta['idventa']} - {venta['fecha']}")
            print(f"Cliente: {cliente_nombre}")
            total = sum(d['cantidad'] * d['precio_venta'] for d in venta.get('detalle', []))
            print(f"Total: {total:.2f}")
            
            confirmacion = input(f"{self.COLOR_AMARILLO}\n¿Está seguro de anular esta venta? (s/N): {self.COLOR_RESET}").lower()
            if confirmacion == 's':
                if self.venta_service.anular(idventa):
                    print(f"{self.COLOR_VERDE}✅ Venta anulada correctamente{self.COLOR_RESET}")
                    
                    self.registrar_auditoria(
                        accion="ANULAR",
                        tabla="venta",
                        registro_id=idventa,
                        datos_nuevos=f"Venta #{idventa} anulada - Total: Bs.{total:.2f}"
                    )
                else:
                    print(f"{self.COLOR_ROJO}❌ Error al anular la venta{self.COLOR_RESET}")
            else:
                print("Operación cancelada")
        
        except Exception as e:
            print(f"❌ Error: {e}")
        
        self.pausa()
    
    @requiere_permiso('proveedores_ver')
    def menu_proveedores(self):
        """Menú de gestión de proveedores"""
        while True:
            self.mostrar_cabecera("GESTIÓN DE PROVEEDORES")
            print("1. Listar proveedores")
            print("2. Buscar proveedor")
            print("3. Crear proveedor")
            print("4. Editar proveedor")
            print("5. Eliminar proveedor")
            print("6. 📁 Ver todos los archivos de proveedores")
            print("0. Volver")
            print()
            
            opcion = input(f"{self.COLOR_AMARILLO}🔹 Seleccione una opción: {self.COLOR_RESET}").strip()
            
            if opcion == '1':
                self._listar_proveedores()
            elif opcion == '2':
                self._buscar_proveedor()
            elif opcion == '3':
                self._crear_proveedor()
            elif opcion == '4':
                self._editar_proveedor()
            elif opcion == '5':
                self._eliminar_proveedor()
            elif opcion == '6':
                self._listar_todos_archivos()
            elif opcion == '0':
                break
            else:
                print("❌ Opción no válida")
                self.pausa()
    
    @requiere_permiso('proveedores_crear')
    def _crear_proveedor(self):
        """Crea un nuevo proveedor"""
        self.mostrar_cabecera("CREAR PROVEEDOR")
        
        print("📝 Complete los datos del proveedor:")
        print()
        
        razon_social = input("Razón Social / Nombre: ")
        sector = input("Sector Comercial: ")
        
        print("\n" + "="*60)
        print("🔍 TIPO DE PERSONA - FORMATO DEL DOCUMENTO")
        print("="*60)
        print("1. 🇻🇪 Persona Natural Venezolana  →  V12345678")
        print("2. 🌎 Persona Natural Extranjera   →  E87654321")
        print("3. 🏢 Persona Jurídica (Empresa)   →  J12345678")
        print("4. 🏛️ Gobierno / Institución        →  G12345678")
        print("5. 👥 Consejo Comunal               →  C12345678")
        print("6. 🛂 Pasaporte                      →  Número de pasaporte")
        print("="*60)
        
        tipo_persona = input("Seleccione tipo de persona (1-6): ").strip()
        
        if tipo_persona == '1':
            tipo_doc = 'V'
            print("\n✅ Seleccionó: Persona Natural Venezolana (V)")
            print("📝 Formato requerido: V + 8 dígitos")
            print("   Ejemplo: V12345678")
            num_doc = input("Documento completo: ").upper()
            
            if not num_doc.startswith('V'):
                print("❌ El documento debe comenzar con 'V'")
                self.pausa()
                return
            num_doc = num_doc[1:]
            
        elif tipo_persona == '2':
            tipo_doc = 'E'
            print("\n✅ Seleccionó: Persona Natural Extranjera (E)")
            print("📝 Formato requerido: E + 8 dígitos")
            print("   Ejemplo: E87654321")
            num_doc = input("Documento completo: ").upper()
            
            if not num_doc.startswith('E'):
                print("❌ El documento debe comenzar con 'E'")
                self.pausa()
                return
            num_doc = num_doc[1:]
            
        elif tipo_persona == '3':
            tipo_doc = 'J'
            print("\n✅ Seleccionó: Empresa (J)")
            print("📝 Formato requerido: J + 8 dígitos")
            print("   Ejemplo: J12345678")
            num_doc = input("Documento completo: ").upper()
            
            if not num_doc.startswith('J'):
                print("❌ El documento debe comenzar con 'J'")
                self.pausa()
                return
            num_doc = num_doc[1:]
            
        elif tipo_persona == '4':
            tipo_doc = 'G'
            print("\n✅ Seleccionó: Gobierno / Institución (G)")
            print("📝 Formato requerido: G + 8 dígitos")
            print("   Ejemplo: G12345678")
            num_doc = input("Documento completo: ").upper()
            
            if not num_doc.startswith('G'):
                print("❌ El documento debe comenzar con 'G'")
                self.pausa()
                return
            num_doc = num_doc[1:]
            
        elif tipo_persona == '5':
            tipo_doc = 'C'
            print("\n✅ Seleccionó: Consejo Comunal (C)")
            print("📝 Formato requerido: C + 8 dígitos")
            print("   Ejemplo: C12345678")
            num_doc = input("Documento completo: ").upper()
            
            if not num_doc.startswith('C'):
                print("❌ El documento debe comenzar con 'C'")
                self.pausa()
                return
            num_doc = num_doc[1:]
            
        elif tipo_persona == '6':
            tipo_doc = 'PASAPORTE'
            print("\n✅ Seleccionó: Pasaporte")
            print("📝 Ingrese número de pasaporte (6-12 caracteres)")
            print("   Ejemplo: ABC123456")
            num_doc = input("Pasaporte: ").upper()
            
        else:
            print("❌ Opción no válida")
            self.pausa()
            return
        
        direccion = input("\nDirección (opcional): ") or None
        telefono = input("Teléfono (opcional): ") or None
        email = input("Email (opcional): ") or None
        url = input("URL (opcional): ") or None
        
        if self.proveedor_service.crear(
            razon_social, sector, tipo_doc, num_doc,
            direccion, telefono, email, url
        ):
            print("\n✅ Proveedor creado exitosamente")
            
            self.registrar_auditoria(
                accion="CREAR",
                tabla="proveedor",
                registro_id=self.proveedor_service.buscar_por_documento(tipo_doc+num_doc)['idproveedor'],
                datos_nuevos=f"Proveedor: {razon_social}, Doc: {tipo_doc}-{num_doc}"
            )
        else:
            print("\n❌ Error al crear el proveedor")
        
        self.pausa()
    
    @requiere_permiso('proveedores_ver')
    def _listar_proveedores(self):
        """Lista todos los proveedores"""
        self.mostrar_cabecera("LISTADO DE PROVEEDORES")
        
        proveedores = self.proveedor_service.listar()
        
        if not proveedores:
            print("📭 No hay proveedores registrados")
        else:
            print(f"{'ID':<5} {'RAZÓN SOCIAL':<30} {'DOCUMENTO':<20} {'TELÉFONO':<15} {'ARCHIVOS':<10}")
            print("-" * 80)
            for p in proveedores:
                archivos = self.proveedor_archivo_service.listar_archivos_proveedor(p['idproveedor'])
                tiene_archivos = "📁" if archivos else ""
                documento = f"{p['tipo_documento']}-{p['num_documento']}"
                telefono_val = p.get('telefono', '') or ''
                print(f"{p['idproveedor']:<5} {p['razon_social']:<30} {documento:<20} {telefono_val:<15} {tiene_archivos:<10}")
        
        self.pausa()
    
    @requiere_permiso('proveedores_ver')
    def _buscar_proveedor(self):
        """Busca un proveedor por ID o documento"""
        self.mostrar_cabecera("BUSCAR PROVEEDOR")
        
        print("1. Buscar por ID")
        print("2. Buscar por documento")
        opcion = input(f"{self.COLOR_AMARILLO}🔹 Seleccione: {self.COLOR_RESET}").strip()
        
        if opcion == '1':
            try:
                idprov = int(input("ID del proveedor: "))
                proveedor = self.proveedor_service.obtener_por_id(idprov)
                if proveedor:
                    self._mostrar_detalle_proveedor(proveedor)
                    
                    self.registrar_auditoria(
                        accion="CONSULTAR",
                        tabla="proveedor",
                        registro_id=idprov,
                        datos_nuevos=f"Proveedor: {proveedor['razon_social']}"
                    )
                else:
                    print(f"❌ No existe proveedor con ID {idprov}")
            except:
                print("❌ ID inválido")
        
        elif opcion == '2':
            doc = input("Número de documento (ej: J12345678): ").upper()
            if doc and doc[0] in ['V', 'E', 'J', 'G', 'C']:
                tipo = doc[0]
                numero = doc[1:]
                proveedores = self.proveedor_service.listar()
                encontrado = None
                for p in proveedores:
                    if p['tipo_documento'] == tipo and p['num_documento'] == numero:
                        encontrado = p
                        break
                if encontrado:
                    self._mostrar_detalle_proveedor(encontrado)
                    
                    self.registrar_auditoria(
                        accion="CONSULTAR",
                        tabla="proveedor",
                        registro_id=encontrado['idproveedor'],
                        datos_nuevos=f"Búsqueda por documento: {doc}"
                    )
                else:
                    print(f"❌ No existe proveedor con documento {doc}")
            else:
                print("❌ Formato de documento inválido")
        
        self.pausa()
    
    def _mostrar_detalle_proveedor(self, p):
        """Muestra detalles completos de un proveedor"""
        print(f"\n📌 ID: {p['idproveedor']}")
        print(f"📌 Razón Social: {p['razon_social']}")
        print(f"📌 Sector Comercial: {p.get('sector_comercial', 'No especificado')}")
        print(f"📌 Documento: {p['tipo_documento']}-{p['num_documento']}")
        print(f"📌 Dirección: {p.get('direccion', 'No registrada')}")
        print(f"📌 Teléfono: {p.get('telefono', 'No registrado')}")
        print(f"📌 Email: {p.get('email', 'No registrado')}")
        print(f"📌 URL: {p.get('url', 'No registrada')}")
        
        archivos = self.proveedor_archivo_service.listar_archivos_proveedor(p['idproveedor'])
        if archivos:
            print(f"\n📁 ARCHIVOS ASOCIADOS ({len(archivos)}):")
            for a in archivos:
                tamano = self.proveedor_archivo_service.obtener_tamano_legible(a['tamano'])
                print(f"   - {a['nombre_archivo']} ({tamano})")
        else:
            print("\n📁 No hay archivos asociados")
    
    @requiere_permiso('proveedores_editar')
    def _editar_proveedor(self):
        """Edita un proveedor existente"""
        self.mostrar_cabecera("EDITAR PROVEEDOR")
        
        try:
            idprov = int(input("ID del proveedor a editar: "))
            proveedor = self.proveedor_service.obtener_por_id(idprov)
            
            if not proveedor:
                print(f"❌ No existe proveedor con ID {idprov}")
                self.pausa()
                return
            
            print(f"\nEditando: {proveedor['razon_social']}")
            print("(Deje en blanco para mantener el valor actual)")
            print()
            
            datos_anteriores = f"Proveedor: {proveedor['razon_social']}, Doc: {proveedor['tipo_documento']}-{proveedor['num_documento']}"
            
            razon = input(f"Razón Social [{proveedor['razon_social']}]: ") or proveedor['razon_social']
            sector = input(f"Sector Comercial [{proveedor['sector_comercial']}]: ") or proveedor['sector_comercial']
            
            print("\n¿Cambiar tipo de documento? (s/N): ", end="")
            cambiar_tipo = input().lower()
            
            if cambiar_tipo == 's':
                print("\n" + "="*60)
                print("🔍 NUEVO TIPO DE DOCUMENTO")
                print("="*60)
                print("1. 🇻🇪 Venezolano (V) → V12345678")
                print("2. 🌎 Extranjero (E) → E87654321")
                print("3. 🏢 Empresa (J) → J12345678")
                print("4. 🏛️ Gobierno (G) → G12345678")
                print("5. 👥 Consejo Comunal (C) → C12345678")
                print("6. 🛂 Pasaporte → texto libre")
                print("="*60)
                
                tipo_op = input("Seleccione nuevo tipo (1-6): ").strip()
                
                if tipo_op == '1':
                    tipo_doc = 'V'
                    print("Ingrese documento completo (ej: V12345678):")
                    doc_completo = input("Documento: ").upper()
                    if doc_completo.startswith('V'):
                        num_doc = doc_completo[1:]
                    else:
                        print("❌ Debe comenzar con V")
                        self.pausa()
                        return
                elif tipo_op == '2':
                    tipo_doc = 'E'
                    print("Ingrese documento completo (ej: E87654321):")
                    doc_completo = input("Documento: ").upper()
                    if doc_completo.startswith('E'):
                        num_doc = doc_completo[1:]
                    else:
                        print("❌ Debe comenzar con E")
                        self.pausa()
                        return
                elif tipo_op == '3':
                    tipo_doc = 'J'
                    print("Ingrese documento completo (ej: J12345678):")
                    doc_completo = input("Documento: ").upper()
                    if doc_completo.startswith('J'):
                        num_doc = doc_completo[1:]
                    else:
                        print("❌ Debe comenzar con J")
                        self.pausa()
                        return
                elif tipo_op == '4':
                    tipo_doc = 'G'
                    print("Ingrese documento completo (ej: G12345678):")
                    doc_completo = input("Documento: ").upper()
                    if doc_completo.startswith('G'):
                        num_doc = doc_completo[1:]
                    else:
                        print("❌ Debe comenzar con G")
                        self.pausa()
                        return
                elif tipo_op == '5':
                    tipo_doc = 'C'
                    print("Ingrese documento completo (ej: C12345678):")
                    doc_completo = input("Documento: ").upper()
                    if doc_completo.startswith('C'):
                        num_doc = doc_completo[1:]
                    else:
                        print("❌ Debe comenzar con C")
                        self.pausa()
                        return
                elif tipo_op == '6':
                    tipo_doc = 'PASAPORTE'
                    num_doc = input("Número de pasaporte: ").upper()
                else:
                    print("❌ Opción no válida")
                    self.pausa()
                    return
            else:
                tipo_doc = proveedor['tipo_documento']
                num_doc = proveedor['num_documento']
            
            direccion = input(f"Dirección [{proveedor.get('direccion', '')}]: ") or proveedor.get('direccion')
            telefono = input(f"Teléfono [{proveedor.get('telefono', '')}]: ") or proveedor.get('telefono')
            email = input(f"Email [{proveedor.get('email', '')}]: ") or proveedor.get('email')
            url = input(f"URL [{proveedor.get('url', '')}]: ") or proveedor.get('url')
            
            if self.proveedor_service.actualizar(
                idprov, razon, sector, tipo_doc, num_doc,
                direccion, telefono, email, url
            ):
                print("\n✅ Proveedor actualizado correctamente")
                
                datos_nuevos = f"Proveedor: {razon}, Doc: {tipo_doc}-{num_doc}"
                self.registrar_auditoria(
                    accion="MODIFICAR",
                    tabla="proveedor",
                    registro_id=idprov,
                    datos_anteriores=datos_anteriores,
                    datos_nuevos=datos_nuevos
                )
            else:
                print("\n❌ Error al actualizar el proveedor")
        
        except Exception as e:
            print(f"❌ Error: {e}")
        
        self.pausa()
    
    @requiere_permiso('proveedores_eliminar')
    def _eliminar_proveedor(self):
        """Elimina un proveedor"""
        self.mostrar_cabecera("ELIMINAR PROVEEDOR")
        
        try:
            idprov = int(input("ID del proveedor a eliminar: "))
            
            proveedor = self.proveedor_service.obtener_por_id(idprov)
            if not proveedor:
                print(f"❌ No existe proveedor con ID {idprov}")
                self.pausa()
                return
            
            datos_proveedor = f"Proveedor: {proveedor['razon_social']}, Doc: {proveedor['tipo_documento']}-{proveedor['num_documento']}"
            
            print(f"\n¿Está seguro de eliminar a {proveedor['razon_social']}?")
            confirmacion = input("Esta acción no se puede deshacer (escriba 'ELIMINAR' para confirmar): ")
            
            if confirmacion == 'ELIMINAR':
                if self.proveedor_service.eliminar(idprov):
                    print("✅ Proveedor eliminado correctamente")
                    
                    self.registrar_auditoria(
                        accion="ELIMINAR",
                        tabla="proveedor",
                        registro_id=idprov,
                        datos_anteriores=datos_proveedor
                    )
                else:
                    print("❌ Error al eliminar el proveedor (puede tener ingresos asociados)")
            else:
                print("Operación cancelada")
        
        except Exception as e:
            print(f"❌ Error: {e}")
        
        self.pausa()
    
    @requiere_permiso('proveedores_ver')
    def _menu_archivos_proveedor(self, idproveedor):
        """Menú de archivos de un proveedor específico"""
        proveedor = self.proveedor_service.obtener_por_id(idproveedor)
        if not proveedor:
            print(f"❌ No existe proveedor con ID {idproveedor}")
            self.pausa()
            return
        
        while True:
            self.mostrar_cabecera(f"ARCHIVOS DE: {proveedor['razon_social']}")
            
            archivos = self.proveedor_archivo_service.listar_archivos_proveedor(idproveedor)
            
            if archivos:
                print(f"📋 ARCHIVOS DE: {proveedor['razon_social']}")
                print(f"{'ID':<5} {'NOMBRE DEL ARCHIVO':<50} {'TIPO':<20} {'TAMAÑO':<10} {'FECHA':<20}")
                print("-" * 105)
                for a in archivos:
                    tamano = self.proveedor_archivo_service.obtener_tamano_legible(a['tamano'])
                    fecha = a['fecha_subida'].strftime('%Y-%m-%d %H:%M') if a['fecha_subida'] else ''
                    nombre = a['nombre_archivo'][:47] + "..." if len(a['nombre_archivo']) > 47 else a['nombre_archivo']
                    print(f"{a['idarchivo']:<5} {nombre:<50} {a['tipo_archivo'][:18]:<20} {tamano:<10} {fecha:<20}")
                print()
            else:
                print(f"📭 No hay archivos para {proveedor['razon_social']}")
                print()
            
            print("1. Subir nuevo archivo")
            print("2. Descargar archivo")
            print("3. Eliminar archivo")
            print("0. Volver")
            print()
            
            opcion = input(f"{self.COLOR_AMARILLO}🔹 Seleccione una opción: {self.COLOR_RESET}").strip()
            
            if opcion == '1':
                self._subir_archivo_proveedor(idproveedor)
            elif opcion == '2':
                self._descargar_archivo_por_id_menu(idproveedor)
            elif opcion == '3':
                self._eliminar_archivo_por_id_menu(idproveedor)
            elif opcion == '0':
                break
            else:
                print("❌ Opción no válida")
                self.pausa()
    
    @requiere_permiso('proveedores_editar')
    def _subir_archivo_proveedor(self, idproveedor):
        """Sube un archivo para un proveedor"""
        self.mostrar_cabecera("SUBIR ARCHIVO")
        
        print("📁 Formatos permitidos:")
        print("  - Imágenes: .jpg, .png, .gif")
        print("  - Documentos: .pdf, .doc, .docx")
        print("  - Hojas de cálculo: .xls, .xlsx, .csv")
        print("  - Texto: .txt")
        print(f"  Tamaño máximo: 10 MB")
        print()
        
        ruta = input("Ruta completa del archivo: ").strip()
        ruta = ruta.replace('"', '').replace("'", "")
        
        if not os.path.exists(ruta):
            print("❌ El archivo no existe")
            self.pausa()
            return
        
        descripcion = input("Descripción (opcional): ").strip() or None
        
        idarchivo = self.proveedor_archivo_service.subir_archivo(idproveedor, ruta, descripcion)
        
        if idarchivo:
            print(f"✅ Archivo subido correctamente (ID: {idarchivo})")
            
            self.registrar_auditoria(
                accion="SUBIR",
                tabla="proveedor_archivos",
                registro_id=idarchivo,
                datos_nuevos=f"Archivo subido para proveedor ID {idproveedor}: {os.path.basename(ruta)}"
            )
        else:
            print("❌ Error al subir el archivo")
        
        self.pausa()
    
    def _descargar_archivo_por_id(self, idarchivo):
        """Descarga un archivo por su ID"""
        archivo = self.proveedor_archivo_service.obtener_archivo(idarchivo)
        if not archivo:
            print(f"❌ No existe archivo con ID {idarchivo}")
            self.pausa()
            return
        
        print(f"\n📌 Archivo: {archivo['nombre_archivo']}")
        print(f"📌 Proveedor: {archivo['proveedor']}")
        print(f"📌 Tamaño: {self.proveedor_archivo_service.obtener_tamano_legible(archivo['tamano'])}")
        print()
        
        ruta_destino = input("Ruta donde guardar (Enter para Descargas/): ").strip()
        if not ruta_destino:
            import os
            home = os.path.expanduser("~")
            ruta_destino = os.path.join(home, "Descargas", archivo['nombre_archivo'])
        
        if self.proveedor_archivo_service.guardar_archivo(idarchivo, ruta_destino):
            print(f"✅ Archivo guardado en: {ruta_destino}")
            
            self.registrar_auditoria(
                accion="DESCARGAR",
                tabla="proveedor_archivos",
                registro_id=idarchivo,
                datos_nuevos=f"Archivo descargado: {archivo['nombre_archivo']}"
            )
        else:
            print("❌ Error al guardar el archivo")
        
        self.pausa()
    
    def _descargar_archivo_por_id_menu(self, idproveedor):
        try:
            idarchivo = int(input("ID del archivo a descargar: "))
            self._descargar_archivo_por_id(idarchivo)
        except ValueError:
            print("❌ ID inválido")
            self.pausa()
    
    def _eliminar_archivo_por_id(self, idarchivo):
        confirmacion = input(f"¿Está seguro de eliminar el archivo ID {idarchivo}? (s/N): ").lower()
        if confirmacion == 's':
            if self.proveedor_archivo_service.eliminar_archivo(idarchivo):
                print("✅ Archivo eliminado correctamente")
                
                self.registrar_auditoria(
                    accion="ELIMINAR",
                    tabla="proveedor_archivos",
                    registro_id=idarchivo,
                    datos_anteriores=f"Archivo ID {idarchivo} eliminado"
                )
            else:
                print("❌ Error al eliminar el archivo")
        else:
            print("Operación cancelada")
        
        self.pausa()
    
    def _eliminar_archivo_por_id_menu(self, idproveedor):
        try:
            idarchivo = int(input("ID del archivo a eliminar: "))
            self._eliminar_archivo_por_id(idarchivo)
        except ValueError:
            print("❌ ID inválido")
            self.pausa()
    
    def _listar_todos_archivos(self):
        """Lista todos los archivos de todos los proveedores"""
        self.mostrar_cabecera("LISTA DE PROVEEDORES (ARCHIVOS)")
        
        proveedores = self.proveedor_service.listar()
        
        todos_archivos = []
        for p in proveedores:
            archivos = self.proveedor_archivo_service.listar_archivos_proveedor(p['idproveedor'])
            for a in archivos:
                a['proveedor_nombre'] = p['razon_social']
                a['proveedor_id'] = p['idproveedor']
                todos_archivos.append(a)
        
        if not todos_archivos:
            print("📭 No hay archivos subidos por ningún proveedor")
            self.pausa()
            return
        
        print(f"{'ID':<5} {'PROVEEDOR':<25} {'NOMBRE DEL ARCHIVO':<50} {'TIPO':<20} {'TAMAÑO':<10} {'FECHA':<15}")
        print("-" * 125)
        for a in todos_archivos:
            tamano = self.proveedor_archivo_service.obtener_tamano_legible(a['tamano'])
            fecha = a['fecha_subida'].strftime('%Y-%m-%d') if a['fecha_subida'] else ''
            nombre = a['nombre_archivo'][:47] + "..." if len(a['nombre_archivo']) > 47 else a['nombre_archivo']
            proveedor = a['proveedor_nombre'][:23] + "..." if len(a['proveedor_nombre']) > 23 else a['proveedor_nombre']
            print(f"{a['idarchivo']:<5} {proveedor:<25} {nombre:<50} {a['tipo_archivo'][:18]:<20} {tamano:<10} {fecha:<15}")
        print()
        
        while True:
            print("\nOpciones:")
            print("1. Descargar archivo por ID")
            print("2. Eliminar archivo por ID")
            print("3. Subir nuevo archivo (seleccionar proveedor)")
            print("4. Ver archivos de un proveedor específico")
            print("0. Volver")
            print()
            
            opcion = input(f"{self.COLOR_AMARILLO}🔹 Seleccione una opción: {self.COLOR_RESET}").strip()
            
            if opcion == '1':
                try:
                    idarchivo = int(input("ID del archivo a descargar: "))
                    self._descargar_archivo_por_id(idarchivo)
                except ValueError:
                    print("❌ ID inválido")
                    self.pausa()
            elif opcion == '2':
                try:
                    idarchivo = int(input("ID del archivo a eliminar: "))
                    self._eliminar_archivo_por_id(idarchivo)
                except ValueError:
                    print("❌ ID inválido")
                    self.pausa()
            elif opcion == '3':
                self._subir_archivo_con_seleccion_proveedor()
            elif opcion == '4':
                try:
                    idprov = int(input("ID del proveedor: "))
                    self._menu_archivos_proveedor(idprov)
                except ValueError:
                    print("❌ ID inválido")
                    self.pausa()
            elif opcion == '0':
                break
            else:
                print("❌ Opción no válida")
                self.pausa()
    
    def _subir_archivo_con_seleccion_proveedor(self):
        proveedores = self.proveedor_service.listar()
        if not proveedores:
            print("❌ No hay proveedores registrados")
            self.pausa()
            return
        
        print("\n📋 PROVEEDORES DISPONIBLES:")
        print(f"{'ID':<5} {'RAZÓN SOCIAL':<30}")
        print("-" * 35)
        for p in proveedores:
            print(f"{p['idproveedor']:<5} {p['razon_social']:<30}")
        print()
        
        try:
            idproveedor = int(input("ID del proveedor: "))
            proveedor = self.proveedor_service.obtener_por_id(idproveedor)
            if not proveedor:
                print("❌ Proveedor no válido")
                self.pausa()
                return
        except ValueError:
            print("❌ ID inválido")
            self.pausa()
            return
        
        self._subir_archivo_proveedor(idproveedor)
    
    @requiere_permiso('inventario_ver')
    def menu_inventario(self):
        """Menú de gestión de inventario"""
        while True:
            self.mostrar_cabecera("GESTIÓN DE INVENTARIO")
            
            alertas = self.inventario_service.obtener_alertas_stock()
            if alertas:
                print("⚠️ ALERTAS DE STOCK:")
                for alerta in alertas[:3]:
                    print(f"   {alerta}")
                print()
            
            print("1. Ver stock completo")
            print("2. Ver resumen de inventario")
            print("3. Artículos con stock crítico")
            print("4. Artículos con stock bajo")
            print("5. Ver detalles de artículo")
            print("6. Registrar ingreso de mercancía")
            print("0. Volver")
            print()
            
            opcion = input(f"{self.COLOR_AMARILLO}🔹 Seleccione una opción: {self.COLOR_RESET}").strip()
            
            if opcion == '1':
                self._ver_stock_completo()
            elif opcion == '2':
                self._ver_resumen_inventario()
            elif opcion == '3':
                self._ver_stock_critico()
            elif opcion == '4':
                self._ver_stock_bajo()
            elif opcion == '5':
                self._ver_detalle_stock()
            elif opcion == '6':
                self._registrar_ingreso()
            elif opcion == '0':
                break
            else:
                print("❌ Opción no válida")
                self.pausa()

    @requiere_permiso('reportes_ventas')
    def menu_reportes(self):
        """Menú de reportes contables"""
        while True:
            self.mostrar_cabecera("📊 REPORTES CONTABLES")
            
            print("1. 📅 Reporte Diario")
            print("2. 📆 Reporte Semanal")
            print("3. 📆 Reporte Mensual")
            print("4. 📆 Reporte Trimestral")
            print("5. 📆 Reporte Anual")
            print("6. 📥 Exportar a Excel/CSV")
            print("0. Volver")
            print()
            
            opcion = input(f"{self.COLOR_AMARILLO}🔹 Seleccione: {self.COLOR_RESET}").strip()
            
            if opcion == '1':
                self._reporte_diario()
            elif opcion == '2':
                self._reporte_semanal()
            elif opcion == '3':
                self._reporte_mensual()
            elif opcion == '4':
                self._reporte_trimestral()
            elif opcion == '5':
                self._reporte_anual()
            elif opcion == '6':
                self._exportar_reporte()
            elif opcion == '0':
                break
            else:
                print("❌ Opción no válida")
                self.pausa()

    def _reporte_diario(self):
        """Muestra reporte de ventas del día"""
        self.mostrar_cabecera("📅 REPORTE DIARIO")
        
        try:
            datos = self.reporte_service.reporte_diario()
            self._mostrar_reporte_contable(datos)
        except Exception as e:
            logger.error(f"Error generando reporte diario: {e}")
            print(f"{self.COLOR_ROJO}❌ Error al generar reporte{self.COLOR_RESET}")
        
        self.pausa()
    
    def _reporte_semanal(self):
        """Muestra reporte de ventas de la semana"""
        self.mostrar_cabecera("📆 REPORTE SEMANAL")
        
        try:
            datos = self.reporte_service.reporte_semanal()
            self._mostrar_reporte_contable(datos)
        except Exception as e:
            logger.error(f"Error generando reporte semanal: {e}")
            print(f"{self.COLOR_ROJO}❌ Error al generar reporte{self.COLOR_RESET}")
        
        self.pausa()
    
    def _reporte_mensual(self):
        """Muestra reporte de ventas del mes"""
        self.mostrar_cabecera("📆 REPORTE MENSUAL")
        
        try:
            datos = self.reporte_service.reporte_mensual()
            self._mostrar_reporte_contable(datos)
        except Exception as e:
            logger.error(f"Error generando reporte mensual: {e}")
            print(f"{self.COLOR_ROJO}❌ Error al generar reporte{self.COLOR_RESET}")
        
        self.pausa()
    
    def _reporte_trimestral(self):
        """Muestra reporte de ventas del trimestre"""
        self.mostrar_cabecera("📆 REPORTE TRIMESTRAL")
        
        try:
            datos = self.reporte_service.reporte_trimestral()
            self._mostrar_reporte_contable(datos)
        except Exception as e:
            logger.error(f"Error generando reporte trimestral: {e}")
            print(f"{self.COLOR_ROJO}❌ Error al generar reporte{self.COLOR_RESET}")
        
        self.pausa()
    
    def _reporte_anual(self):
        """Muestra reporte de ventas del año"""
        self.mostrar_cabecera("📆 REPORTE ANUAL")
        
        try:
            datos = self.reporte_service.reporte_anual()
            self._mostrar_reporte_contable(datos)
        except Exception as e:
            logger.error(f"Error generando reporte anual: {e}")
            print(f"{self.COLOR_ROJO}❌ Error al generar reporte{self.COLOR_RESET}")
        
        self.pausa()
    
    def _mostrar_reporte_contable(self, datos):
        """Muestra un reporte contable formateado"""
        print(f"\n{self.COLOR_AZUL}📊 RESUMEN CONTABLE{self.COLOR_RESET}")
        print("=" * 60)
        print(f"Período: {datos['fecha_inicio']} al {datos['fecha_fin']}")
        print(f"Total de ventas: {datos['total_ventas']}")
        print("-" * 60)
        print(f"{self.COLOR_VERDE}💰 Totales por moneda:{self.COLOR_RESET}")
        print(f"   Bolívares (Bs.): {datos['total_bs']:,.2f}")
        print(f"   Dólares (USD):   ${datos['total_usd']:,.2f}")
        print(f"   Euros (EUR):     €{datos['total_eur']:,.2f}")
        print(f"{self.COLOR_AMARILLO}📊 IGTF Total: Bs. {datos['igtf_total']:,.2f}{self.COLOR_RESET}")
        print("-" * 60)
        print(f"{self.COLOR_CYAN}📅 Detalle por día:{self.COLOR_RESET}")
        print(f"{'Fecha':<12} {'Ventas':<8} {'Bs.':<15} {'USD':<12} {'EUR':<12}")
        print("-" * 60)
        
        # Ordenar fechas cronológicamente
        fechas_ordenadas = sorted(datos['detalle'].keys())
        
        for fecha in fechas_ordenadas:
            det = datos['detalle'][fecha]
            
            # Formatear fecha de manera segura
            try:
                # Intentar formato YYYY-MM-DD
                if '-' in fecha and len(fecha.split('-')) == 3:
                    año, mes, dia = fecha.split('-')
                    fecha_formateada = f"{dia}/{mes}/{año}"
                else:
                    # Si ya viene en otro formato, usarla directamente
                    fecha_formateada = fecha
            except:
                fecha_formateada = fecha
            
            # Formatear números con separadores
            try:
                bs_str = f"{det['bs']:,.2f}".replace(',', ' ')
            except:
                bs_str = "0.00"
            
            try:
                usd_str = f"{det['usd']:,.2f}".replace(',', ' ')
            except:
                usd_str = "0.00"
            
            try:
                eur_str = f"{det['eur']:,.2f}".replace(',', ' ')
            except:
                eur_str = "0.00"
            
            # Imprimir línea con formato corregido
            print(f"{fecha_formateada:<12} {det['ventas']:<8} {bs_str:>14} bs {usd_str:>10} $ {eur_str:>8} €")

    def _exportar_reporte(self):
        """Exporta reporte a CSV"""
        self.mostrar_cabecera("📥 EXPORTAR REPORTE")
        
        print("Seleccione período a exportar:")
        print("1. Diario")
        print("2. Semanal")
        print("3. Mensual")
        print("4. Trimestral")
        print("5. Anual")
        opcion = input(f"{self.COLOR_AMARILLO}🔹 Seleccione: {self.COLOR_RESET}").strip()
        
        if opcion == '1':
            datos = self.reporte_service.reporte_diario()
        elif opcion == '2':
            datos = self.reporte_service.reporte_semanal()
        elif opcion == '3':
            datos = self.reporte_service.reporte_mensual()
        elif opcion == '4':
            datos = self.reporte_service.reporte_trimestral()
        elif opcion == '5':
            datos = self.reporte_service.reporte_anual()
        else:
            print("❌ Opción no válida")
            self.pausa()
            return
        
        try:
            ruta = self.reporte_service.exportar_a_csv(datos)
            print(f"\n{self.COLOR_VERDE}✅ Reporte exportado a: {ruta}{self.COLOR_RESET}")
            print("   Puede abrirlo con Excel para análisis contable")
        except Exception as e:
            logger.error(f"Error exportando reporte: {e}")
            print(f"{self.COLOR_ROJO}❌ Error al exportar reporte{self.COLOR_RESET}")
        
        self.pausa()    

    # ======================================================
    # NUEVOS MÉTODOS PARA MODIFICAR TASAS DE CAMBIO
    # ======================================================
    
    def _modificar_tasas(self):
        """Permite modificar las tasas de cambio USD y EUR manualmente"""
        self.mostrar_cabecera("💱 MODIFICAR TASAS DE CAMBIO")
        
        usuario = self.trabajador_service.get_usuario_actual()
        if not usuario:
            print(f"{self.COLOR_ROJO}❌ Debe iniciar sesión para modificar tasas{self.COLOR_RESET}")
            self.pausa()
            return
        
        print("Tasas actuales:")
        
        # Obtener tasas actuales
        tasas_actuales = self.obtener_tasas_actuales()
        
        if tasas_actuales['USD']:
            print(f"  💵 USD: 1 = {self.COLOR_VERDE}Bs. {tasas_actuales['USD']:.2f}{self.COLOR_RESET}")
        else:
            print(f"  💵 USD: {self.COLOR_ROJO}No registrada{self.COLOR_RESET}")
        
        if tasas_actuales['EUR']:
            print(f"  💶 EUR: 1 = {self.COLOR_VERDE}Bs. {tasas_actuales['EUR']:.2f}{self.COLOR_RESET}")
        else:
            print(f"  💶 EUR: {self.COLOR_ROJO}No registrada{self.COLOR_RESET}")
        
        print("\n" + "="*60)
        print("¿Qué tasa desea modificar?")
        print("1. 💵 Dólar (USD)")
        print("2. 💶 Euro (EUR)")
        print("3. Ambas")
        print("0. Volver")
        
        opcion = input(f"{self.COLOR_AMARILLO}🔹 Seleccione: {self.COLOR_RESET}").strip()
        
        if opcion == '1':
            self._modificar_tasa_unica('USD', usuario)
            self.pausa()
        elif opcion == '2':
            self._modificar_tasa_unica('EUR', usuario)
            self.pausa()
        elif opcion == '3':
            self._modificar_tasa_unica('USD', usuario)
            self._modificar_tasa_unica('EUR', usuario)
            self.pausa()
        elif opcion == '0':
            return
        else:
            print("❌ Opción no válida")
            self.pausa()
    
    def _modificar_tasa_unica(self, moneda, usuario):
        """Modifica una tasa específica"""
        print(f"\n{self.COLOR_AMARILLO}💰 Modificar tasa {moneda}{self.COLOR_RESET}")
        print("="*40)
        
        try:
            nueva_tasa = float(input(f"Nuevo valor para 1 {moneda} = Bs. ").strip())
            if nueva_tasa <= 0:
                print("❌ La tasa debe ser positiva")
                return
            
            # Registrar en el servicio de tasas
            if hasattr(self.venta_service, 'tasa_service') and self.venta_service.tasa_service:
                nombre_usuario = f"{usuario['nombre']} {usuario['apellidos']}"
                
                if self.venta_service.tasa_service.registrar_tasa_manual(
                    moneda=moneda,
                    tasa=nueva_tasa,
                    usuario=nombre_usuario
                ):
                    print(f"{self.COLOR_VERDE}✅ Tasa {moneda} actualizada a Bs. {nueva_tasa:.2f}{self.COLOR_RESET}")
                    
                    # Registrar en auditoría
                    self.registrar_auditoria(
                        accion="MODIFICAR_TASA",
                        tabla="tasa_cambio",
                        registro_id=0,
                        datos_nuevos=f"Tasa {moneda} actualizada a {nueva_tasa}"
                    )
                else:
                    print(f"{self.COLOR_ROJO}❌ Error al actualizar tasa{self.COLOR_RESET}")
            else:
                print(f"{self.COLOR_ROJO}❌ Servicio de tasas no disponible{self.COLOR_RESET}")
                
        except ValueError:
            print("❌ Ingrese un número válido")
    
    def _ver_stock_completo(self):
        self.mostrar_cabecera("STOCK COMPLETO")
        print(self.inventario_service.mostrar_tabla_stock())
        self.pausa()
    
    def _ver_resumen_inventario(self):
        self.mostrar_cabecera("RESUMEN DE INVENTARIO")
        print(self.inventario_service.mostrar_resumen_stock())
        self.pausa()
    
    def _ver_stock_critico(self):
        self.mostrar_cabecera("STOCK CRÍTICO (menos de 3 unidades)")
        
        articulos = self.inventario_service.listar_con_stock()
        criticos = [a for a in articulos if a['nivel_stock'] == 'CRÍTICO']
        
        if not criticos:
            print("✅ No hay artículos con stock crítico")
        else:
            print(f"{'ID':<5} {'CÓDIGO':<15} {'NOMBRE':<30} {'STOCK':<10}")
            print("-" * 60)
            for art in criticos:
                print(f"{art['color']}{art['idarticulo']:<5} {art['codigo']:<15} {art['nombre']:<30} {art['stock_actual']:<10}{self.inventario_service.COLOR_RESET}")
        
        self.pausa()
    
    def _ver_stock_bajo(self):
        self.mostrar_cabecera("STOCK BAJO (entre 3 y 5 unidades)")
        
        articulos = self.inventario_service.listar_con_stock()
        bajos = [a for a in articulos if a['nivel_stock'] == 'BAJO']
        
        if not bajos:
            print("✅ No hay artículos con stock bajo")
        else:
            print(f"{'ID':<5} {'CÓDIGO':<15} {'NOMBRE':<30} {'STOCK':<10}")
            print("-" * 60)
            for art in bajos:
                print(f"{art['color']}{art['idarticulo']:<5} {art['codigo']:<15} {art['nombre']:<30} {art['stock_actual']:<10}{self.inventario_service.COLOR_RESET}")
        
        self.pausa()
    
    def _ver_detalle_stock(self):
        self.mostrar_cabecera("DETALLE DE STOCK")
        
        try:
            idart = int(input("ID del artículo: "))
            art = self.articulo_service.obtener_por_id(idart)
            
            if not art:
                print(f"❌ No existe artículo con ID {idart}")
                self.pausa()
                return
            
            stock = self.inventario_service.obtener_stock_articulo(idart)
            nivel = self.inventario_service.obtener_nivel_stock(stock)
            
            print(f"\n📌 Artículo: {art['nombre']}")
            print(f"📌 Código: {art['codigo']}")
            print(f"📌 Stock actual: {stock} unidades")
            print(f"📌 Estado: {nivel['color']}{nivel['emoji']} {nivel['nivel']}{self.inventario_service.COLOR_RESET}")
            print(f"📌 {nivel['mensaje']}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        self.pausa()
    
    @requiere_permiso('inventario_ingresos')
    def _registrar_ingreso(self):
        """Registra un nuevo ingreso de mercancía"""
        self.mostrar_cabecera("REGISTRAR INGRESO")
        
        proveedores = self.proveedor_service.listar()
        if not proveedores:
            print("❌ No hay proveedores registrados.")
            print("   Por favor, cree un proveedor primero (Opción 3 → Opción 3)")
            self.pausa()
            return
        
        print("Proveedores disponibles:")
        for p in proveedores:
            print(f"  {p['idproveedor']}. {p['razon_social']}")
        
        try:
            idproveedor = int(input("\nID del proveedor: "))
            proveedor = self.proveedor_service.obtener_por_id(idproveedor)
            if not proveedor:
                print("❌ Proveedor no válido")
                self.pausa()
                return
        except:
            print("❌ ID inválido")
            self.pausa()
            return
        
        print("\nTipo de comprobante:")
        print("  1. Factura")
        print("  2. Boleta")
        print("  3. Guía")
        tipo_map = {'1': 'FACTURA', '2': 'BOLETA', '3': 'GUIA'}
        tipo_op = input("Seleccione: ").strip()
        tipo_comprobante = tipo_map.get(tipo_op, 'FACTURA')
        
        serie = input("Serie (ej. F001): ")
        numero = input("Número: ")
        
        detalle = []
        print("\n📦 AGREGAR PRODUCTOS AL INGRESO")
        print("="*40)
        
        print("\n📋 ARTÍCULOS DISPONIBLES:")
        articulos = self.articulo_service.listar()
        if not articulos:
            print("❌ No hay artículos registrados. Cree artículos primero.")
            self.pausa()
            return
        
        print(f"{'ID':<5} {'CÓDIGO':<15} {'NOMBRE':<30} {'CATEGORÍA':<20}")
        print("-" * 70)
        for a in articulos:
            cat_nombre = a.get('categoria', '') or 'N/A'
            print(f"{a['idarticulo']:<5} {a['codigo']:<15} {a['nombre']:<30} {cat_nombre:<20}")
        print()
        
        while True:
            print("\n--- Agregar producto ---")
            codigo = input("Código del artículo (0 para terminar, '?' para ver lista): ")
            
            if codigo == '0':
                break
            elif codigo == '?':
                print("\n📋 ARTÍCULOS DISPONIBLES:")
                print(f"{'ID':<5} {'CÓDIGO':<15} {'NOMBRE':<30} {'CATEGORÍA':<20}")
                print("-" * 70)
                for a in articulos:
                    cat_nombre = a.get('categoria', '') or 'N/A'
                    print(f"{a['idarticulo']:<5} {a['codigo']:<15} {a['nombre']:<30} {cat_nombre:<20}")
                continue
            
            art = self.articulo_service.buscar_por_codigo(codigo)
            if not art:
                try:
                    idart = int(codigo)
                    art = self.articulo_service.obtener_por_id(idart)
                except:
                    pass
            
            if not art:
                print("❌ Artículo no encontrado. Use '?' para ver la lista.")
                continue
            
            categoria_nombre = art.get('categoria', '') or 'No especificada'
            
            print(f"📌 Artículo seleccionado: {art['nombre']}")
            print(f"   Código: {art['codigo']}")
            print(f"   Categoría: {categoria_nombre}")
            
            try:
                cantidad = int(input("Cantidad a ingresar: "))
                if cantidad <= 0:
                    print("❌ La cantidad debe ser positiva")
                    continue
                precio = float(input("Precio de compra: "))
                if precio <= 0:
                    print("❌ El precio debe ser positivo")
                    continue
            except ValueError:
                print("❌ Cantidad o precio inválido")
                continue
            
            detalle.append({
                'idarticulo': art['idarticulo'],
                'cantidad': cantidad,
                'precio_compra': precio
            })
            print(f"✅ {art['nombre']} agregado - {cantidad} unidades a Bs. {precio:.2f}")
        
        if not detalle:
            print("❌ Debe agregar al menos un producto")
            self.pausa()
            return
        
        print("\n" + "="*50)
        print("📋 RESUMEN DEL INGRESO")
        print("="*50)
        print(f"Proveedor: {proveedor['razon_social']}")
        print(f"Comprobante: {tipo_comprobante} {serie}-{numero}")
        print("\nProductos:")
        total = 0
        for item in detalle:
            art = self.articulo_service.obtener_por_id(item['idarticulo'])
            subtotal = item['cantidad'] * item['precio_compra']
            total += subtotal
            print(f"  - {art['nombre']}: {item['cantidad']} und @ Bs.{item['precio_compra']:.2f} = Bs.{subtotal:.2f}")
        print(f"\n💰 TOTAL: Bs.{total:.2f}")
        print("="*50)
        
        confirmar = input(f"{self.COLOR_AMARILLO}¿Confirmar ingreso? (s/N): {self.COLOR_RESET}").lower()
        if confirmar != 's':
            print("Operación cancelada")
            self.pausa()
            return
        
        usuario = self.trabajador_service.get_usuario_actual()
        idingreso = self.ingreso_service.registrar_ingreso(
            usuario['idtrabajador'], idproveedor, tipo_comprobante,
            serie, numero, 16.0, detalle
        )
        
        if idingreso:
            print(f"\n{self.COLOR_VERDE}✅ Ingreso #{idingreso} registrado correctamente{self.COLOR_RESET}")
            print("📦 Stock actualizado automáticamente")
            
            self.registrar_auditoria(
                accion="CREAR",
                tabla="ingreso",
                registro_id=idingreso,
                datos_nuevos=f"Ingreso #{idingreso} - Proveedor: {proveedor['razon_social']} - Total: Bs.{total:.2f}"
            )
        else:
            print(f"\n{self.COLOR_ROJO}❌ Error al registrar el ingreso{self.COLOR_RESET}")
        
        self.pausa()
    
    def run(self):
        """Ejecuta el sistema"""
        if not self.conectar_db():
            return
        
        while True:
            opcion = self.mostrar_menu_principal()
            
            # NUEVA OPCIÓN PARA MODIFICAR TASAS
            if opcion.upper() == 'X':
                self._modificar_tasas()
                continue
            
            if opcion == '1':
                if self.rol_service.tiene_permiso('clientes_ver'):
                    self.menu_clientes()
                else:
                    print("❌ No tiene permisos para acceder a clientes")
                    self.pausa()
            elif opcion == '2':
                if self.rol_service.tiene_permiso('articulos_ver'):
                    self.menu_articulos()
                else:
                    print("❌ No tiene permisos para acceder a artículos")
                    self.pausa()
            elif opcion == '3':
                if self.rol_service.tiene_permiso('proveedores_ver'):
                    self.menu_proveedores()
                else:
                    print("❌ No tiene permisos para acceder a proveedores")
                    self.pausa()
            elif opcion == '4':
                if self.rol_service.tiene_permiso('ventas_ver'):
                    self.menu_ventas()
                else:
                    print("❌ No tiene permisos para acceder a ventas")
                    self.pausa()
            elif opcion == '5':
                if self.rol_service.tiene_permiso('inventario_ver'):
                    self.menu_inventario()
                else:
                    print("❌ No tiene permisos para acceder a inventario")
                    self.pausa()
            elif opcion == '6':
                if self.rol_service.tiene_permiso('reportes_ventas'):
                    self.menu_reportes()
                else:
                    print("❌ No tiene permisos para acceder a reportes")
                    self.pausa()
            elif opcion == '7':
                if self.trabajador_service.get_usuario_actual() and self.rol_service.tiene_permiso('usuarios_ver'):
                    self.menu_administracion_usuarios()
                else:
                    print("❌ No tiene permisos para acceder a esta opción")
                    self.pausa()
            elif opcion == '8':
                if self.trabajador_service.get_usuario_actual():
                    self.trabajador_service.logout()
                    self.pausa()
                else:
                    self.menu_login()
            elif opcion == '0':
                print(f"\n{self.COLOR_VERDE}👋 ¡Hasta luego!{self.COLOR_RESET}")
                break
            else:
                print("❌ Opción no válida")
                self.pausa()
        
        self.db.cerrar()

if __name__ == "__main__":
    sistema = SistemaVentas()
    sistema.run()
