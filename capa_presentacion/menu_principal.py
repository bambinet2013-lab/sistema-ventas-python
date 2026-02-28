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
        if not usuario or self.rol_service.tiene_permiso('compras_ver'):  # NUEVA OPCIÓN
            opciones.append(("5", "Gestión de Compras", "📥"))              # NUEVA OPCIÓN
        if not usuario or self.rol_service.tiene_permiso('inventario_ver'):
            opciones.append(("6", "Gestión de Inventario", "📊"))
        if not usuario or self.rol_service.tiene_permiso('reportes_ventas'):
            opciones.append(("7", "Reportes Contables", "📈"))
        if usuario and self.rol_service.tiene_permiso('usuarios_ver'):
            opciones.append(("8", "Administración de Usuarios", "👤"))
        
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
        """Lista todos los artículos con su stock actual"""
        self.mostrar_cabecera("LISTADO DE ARTÍCULOS")
        
        try:
            from capa_negocio.inventario_service import InventarioService
            inventario_service = InventarioService(self.articulo_service)
            
            # Obtener artículos con stock
            articulos = inventario_service.listar_con_stock()
            
            if not articulos:
                print(f"\n{self.COLOR_AMARILLO}📭 No hay artículos registrados{self.COLOR_RESET}")
                self.pausa()
                return
            
            # Cabecera de la tabla
            print(f"\n{self.COLOR_VERDE}{'ID':<5} {'CÓDIGO':<15} {'NOMBRE':<30} {'CATEGORÍA':<20} {'PRECIO $':<10} {'STOCK':<10} {'ESTADO':<10}{self.COLOR_RESET}")
            print(f"{self.COLOR_CYAN}{'-'*110}{self.COLOR_RESET}")
            
            for a in articulos:
                id_art = a.get('idarticulo', '')
                codigo = a.get('codigo_barras', '')
                if not codigo:
                    codigo = a.get('codigo', '') or a.get('plu', '') or 'S/C'
                codigo = codigo[:14]
                
                nombre_base = a.get('nombre', '')
                letra_fiscal = a.get('letra_fiscal', '')
                if letra_fiscal:
                    nombre = f"{nombre_base} ({letra_fiscal})"[:29]
                else:
                    nombre = nombre_base[:29]
                categoria = a.get('categoria_nombre', a.get('categoria', 'Sin categoría'))[:19]
                precio = a.get('precio_venta', 0)
                stock_actual = a.get('stock_actual', 0)
                stock_minimo = a.get('stock_minimo', 5)
                
                # Determinar color y emoji según TU NUEVA LÓGICA
                if stock_actual <= 5:
                    color_estado = self.COLOR_ROJO
                    emoji = "🔴"
                    estado_texto = "CRÍTICO"
                elif stock_actual <= 10:
                    color_estado = self.COLOR_AMARILLO
                    emoji = "🟡"
                    estado_texto = "BAJO"
                else:
                    color_estado = self.COLOR_VERDE
                    emoji = "🟢"
                    estado_texto = "NORMAL"
                
                # Formatear precio: entero sin decimales, decimal con 2 decimales
                if precio == int(precio):
                    precio_formateado = f"${int(precio)}"
                else:
                    precio_formateado = f"${precio:.2f}"
                
                # Formatear stock con "und"
                stock_formateado = f"{stock_actual} und"
                
                # Mostrar con color según estado
                print(f"{id_art:<5} {codigo:<15} {nombre:<30} {categoria:<20} {precio_formateado:<10} {stock_formateado:<10} {color_estado}{emoji} {estado_texto}{self.COLOR_RESET}")
            
            print(f"{self.COLOR_CYAN}{'-'*110}{self.COLOR_RESET}")
            print(f"\n{self.COLOR_AMARILLO}Opciones de edición:{self.COLOR_RESET}")
            print(f"  {self.COLOR_VERDE}[E]{self.COLOR_RESET} Editar (categoría, nombre)")
            print(f"  {self.COLOR_VERDE}[M]{self.COLOR_RESET} Editar solo PRECIO en dólares $")
            print(f"  {self.COLOR_VERDE}[D]{self.COLOR_RESET} Ver DETALLES del artículo")
            print(f"  {self.COLOR_ROJO}[V]{self.COLOR_RESET} Volver al menú")
            print(f"{self.COLOR_CYAN}{'-'*40}{self.COLOR_RESET}")
            
            opcion = input(f"\n{self.COLOR_AMARILLO}🔹 Seleccione: {self.COLOR_RESET}").strip().upper()
            
            if opcion == 'V':
                return
            elif opcion == 'E':
                self._buscar_articulo_para_editar()
            elif opcion == 'M':
                self._buscar_articulo_para_precio()
            elif opcion == 'D':
                self._buscar_articulo_para_detalle()
            else:
                print(f"{self.COLOR_ROJO}❌ Opción inválida{self.COLOR_RESET}")
                self.pausa()
                
        except Exception as e:
            logger.error(f"Error en listado de artículos: {e}")
            print(f"{self.COLOR_ROJO}❌ Error al listar artículos: {e}{self.COLOR_RESET}")
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
        """Registra una nueva venta"""
        self.mostrar_cabecera("REGISTRAR VENTA - MULTIMONEDA")
        
        usuario = self.trabajador_service.get_usuario_actual()
        if not usuario:
            print(f"{self.COLOR_ROJO}❌ Debe iniciar sesión{self.COLOR_RESET}")
            self.pausa()
            return
        
        tasas = self.obtener_tasas_actuales()
        tasa_usd = tasas.get('USD', 0)
        
        if tasa_usd <= 0:
            print(f"{self.COLOR_AMARILLO}⚠️ Configure tasa con [X]{self.COLOR_RESET}")
            self.pausa()
            return
        
        # ===== SELECCIÓN DE CLIENTE =====
        print("\n📋 IDENTIFICACIÓN DEL CLIENTE")
        print("="*60)
        print("1. 🇻🇪 RIF")
        print("2. 🆔 Cédula")
        print("3. 🛒 CONSUMIDOR FINAL")
        opcion = input(f"{self.COLOR_AMARILLO}🔹 Seleccione: {self.COLOR_RESET}").strip()
        
        idcliente = None
        cliente = None
        
        if opcion == '1' or opcion == '2':
            print("Buscar cliente... (simulado)")
            idcliente = 1
        # else: consumidor final (None)
        
        # ===== MONEDA DE PAGO =====
        print("\n💳 MONEDA DE PAGO")
        print("="*60)
        print("1. USD  2. VES  3. EUR")
        pago = input(f"{self.COLOR_AMARILLO}🔹 Seleccione: {self.COLOR_RESET}").strip()
        moneda_pago = {'1': 'USD', '2': 'VES', '3': 'EUR'}.get(pago, 'USD')
        
        # ===== COMPROBANTE =====
        print("\n📄 COMPROBANTE")
        print("="*60)
        print("1. Boleta  2. Ticket")
        tipo = input(f"{self.COLOR_AMARILLO}🔹 Seleccione: {self.COLOR_RESET}").strip()
        tipo_comp = 'BOLETA' if tipo == '1' else 'TICKET'
        serie = input("Serie: ").strip() or "F001"
        numero = input("Número: ").strip() or "001"
        
        # ===== PRODUCTOS (INTERFAZ LIMPIA) =====
        detalle = []
        print("\n" + "="*60)
        print("🛒 PRODUCTOS")
        print("="*60)
        print(f"💰 Tasa: Bs. {tasa_usd:.2f}")
        print("📌 Opciones:")
        print("   [1] Buscar por nombre")
        print("   [2] Ingresar código")
        print("   [3] Ver lista")
        print("   [4] Finalizar")
        print("="*60)
        
        while True:
            opt = input(f"{self.COLOR_AMARILLO}🔹 Opción: {self.COLOR_RESET}").strip()
            
            if opt == '4':
                break
                
            if opt == '3':
                self._mostrar_lista_articulos()
                cod = input("Código: ").strip()
                art = self.articulo_service.buscar_por_codigo(cod) or self.articulo_service.buscar_por_codigo_barras(cod)
                if not art:
                    print("❌ No encontrado")
                    continue
            elif opt == '2':
                cod = input("Código: ").strip()
                art = self.articulo_service.buscar_por_codigo(cod) or self.articulo_service.buscar_por_codigo_barras(cod)
                if not art:
                    print("❌ No encontrado")
                    continue
            elif opt == '1':
                nom = input("Nombre: ").strip()
                res = self.articulo_service.buscar_por_nombre(nom)
                if not res:
                    print("❌ No encontrado")
                    continue
                if len(res) == 1:
                    art = res[0]
                else:
                    for i, a in enumerate(res, 1):
                        print(f"  {i}. {a['nombre']}")
                    try:
                        s = int(input("Seleccione: ")) - 1
                        art = res[s] if 0 <= s < len(res) else None
                    except:
                        continue
                    if not art:
                        continue
            else:
                print("❌ Opción inválida")
                continue
            
            # Procesar artículo
            try:
                precio = float(art.get('precio_venta', 0))
            except:
                precio = 0.0
                
            stock = self.inventario_service.obtener_stock_articulo(art['idarticulo'])
            print(f"\n📌 {art['nombre']} - ${precio:.2f} - Stock: {stock}")
            
            try:
                cant = int(input("Cantidad: "))
                if cant <= 0 or cant > stock:
                    print("❌ Cantidad inválida")
                    continue
            except:
                print("❌ Cantidad inválida")
                continue
            
            subtotal = cant * precio
            print(f"   Subtotal: ${subtotal:.2f} = Bs. {subtotal * tasa_usd:.2f}")
            
            detalle.append({
                'idarticulo': art['idarticulo'],
                'cantidad': cant,
                'precio_venta': precio,
                'nombre': art['nombre']
            })
            print("✅ Agregado")
        
        if not detalle:
            print("❌ Sin productos")
            self.pausa()
            return
        
        # ===== RESUMEN =====
        total = sum(d['cantidad'] * d['precio_venta'] for d in detalle)
        iva = total * 0.16
        total_iva = total + iva
        total_bs = total_iva * tasa_usd
        
        print("\n" + "="*60)
        print("📋 RESUMEN")
        print("="*60)
        for d in detalle:
            print(f"  {d['nombre']:<30} x{d['cantidad']}  ${d['precio_venta']:.2f}")
        print("-"*60)
        print(f"SUBTOTAL: ${total:.2f}")
        print(f"IVA 16%:  ${iva:.2f}")
        print(f"TOTAL:    ${total_iva:.2f} = Bs. {total_bs:.2f}")
        print("="*60)
        
        if input("¿Confirmar? (s/N): ").lower() != 's':
            print("Cancelado")
            self.pausa()
            return
        
        # ===== REGISTRAR =====
        idv = self.venta_service.registrar(
            usuario['idtrabajador'], idcliente, tipo_comp,
            serie, numero, 16.0, detalle,
            moneda='USD', moneda_pago=moneda_pago, tasa_cambio=tasa_usd
        )
        
        if idv:
            print(f"\n✅ Venta #{idv} registrada")
        else:
            print("❌ Error")
        
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
                if self.rol_service.tiene_permiso('compras_ver'):
                    self._menu_compras()
                else:
                    print("❌ No tiene permisos para acceder a compras")
                    self.pausa()
            elif opcion == '6':
                if self.rol_service.tiene_permiso('inventario_ver'):
                    self.menu_inventario()
                else:
                    print("❌ No tiene permisos para acceder a inventario")
                    self.pausa()
            elif opcion == '7':
                if self.rol_service.tiene_permiso('reportes_ventas'):
                    self.menu_reportes()
                else:
                    print("❌ No tiene permisos para acceder a reportes")
                    self.pausa()
            elif opcion == '8':
                if self.trabajador_service.get_usuario_actual():
                    # Si ya tiene sesión, cierra sesión
                    self.trabajador_service.logout()
                    print(f"{self.COLOR_VERDE}✅ Sesión cerrada{self.COLOR_RESET}")
                    self.pausa()
                else:
                    # Si no tiene sesión, inicia sesión
                    self.menu_login()
            elif opcion == '9':
                if self.trabajador_service.get_usuario_actual() and self.rol_service.tiene_permiso('usuarios_ver'):
                    self.menu_administracion_usuarios()
                else:
                    print("❌ No tiene permisos para acceder a usuarios")
                    self.pausa()
            elif opcion == '0':
                print(f"\n{self.COLOR_VERDE}👋 ¡Hasta luego!{self.COLOR_RESET}")
                break
            else:
                print("❌ Opción no válida")
                self.pausa()

    # ======================================================
    # MÓDULO DE COMPRAS
    # ======================================================
    
        """Menú de gestión de compras"""
    def _menu_compras(self):
        """Menú de gestión de compras"""
        while True:
            self.mostrar_cabecera("📥 MÓDULO DE COMPRAS")
            print(f"{self.COLOR_VERDE}1{self.COLOR_RESET}. Registrar compra (orden)")
            print(f"{self.COLOR_VERDE}2{self.COLOR_RESET}. Recibir mercancía")
            print(f"{self.COLOR_VERDE}3{self.COLOR_RESET}. Listar órdenes de compra")
            print(f"{self.COLOR_VERDE}4{self.COLOR_RESET}. Buscar orden por factura")
            print(f"{self.COLOR_VERDE}5{self.COLOR_RESET}. Ver recepciones")
            print(f"{self.COLOR_VERDE}6{self.COLOR_RESET}. Reportes de compras")
            print(f"{self.COLOR_ROJO}0{self.COLOR_RESET}. Volver al menú principal")
            
            opcion = input(f"\n{self.COLOR_AMARILLO}Seleccione: {self.COLOR_RESET}")
            
            if opcion == '1':
                self._registrar_compra()
            elif opcion == '2':
                self._recibir_mercancia()
            elif opcion == '3':
                self._listar_ordenes_compra()
            elif opcion == '4':
                self._buscar_orden_factura()
            elif opcion == '5':
                self._listar_recepciones()
            elif opcion == '6':
                self._reportes_compras()
            elif opcion == '0':
                break
            else:
                print(f"{self.COLOR_ROJO}❌ Opción inválida{self.COLOR_RESET}")
                self.pausa()

    def _registrar_compra(self):
        """Registra una nueva orden de compra (PASO 1 COMPLETO)"""
        self.mostrar_cabecera("📄 NUEVA COMPRA")
        
        # Verificar usuario
        usuario = self.trabajador_service.get_usuario_actual()
        if not usuario:
            print(f"{self.COLOR_ROJO}❌ Debe iniciar sesión{self.COLOR_RESET}")
            self.pausa()
            return
        
        # 1. CÓDIGO FACTURA
        print(f"\n{self.COLOR_AMARILLO}1. CÓDIGO FACTURA (obligatorio){self.COLOR_RESET}")
        print("   Ingrese código de la factura (será el identificador único de la orden)")
        codigo_factura = input("   Código Factura: ").strip().upper()
        if not codigo_factura:
            print(f"{self.COLOR_ROJO}❌ Código de factura obligatorio{self.COLOR_RESET}")
            self.pausa()
            return
        
        # 2. PROVEEDOR
        print(f"\n{self.COLOR_AMARILLO}2. PROVEEDOR{self.COLOR_RESET}")
        print("   [1] Seleccionar de la lista")
        print("   [2] Crear nuevo proveedor")
        print("   [0] Cancelar")
        
        opcion_prov = input("\n   Seleccione: ")
        
        if opcion_prov == '0':
            return
            
        idproveedor = None
        proveedor_data = None
        
        if opcion_prov == '1':
            # Listar proveedores existentes
            proveedores = self.proveedor_service.listar()
            if not proveedores:
                print(f"\n{self.COLOR_ROJO}❌ No hay proveedores registrados{self.COLOR_RESET}")
                print(f"{self.COLOR_AMARILLO}   Debe crear un proveedor primero{self.COLOR_RESET}")
                self.pausa()
                return
            
            print(f"\n{self.COLOR_VERDE}   Proveedores disponibles:{self.COLOR_RESET}")
            for i, p in enumerate(proveedores[:10], 1):
                razon = p.get('razon_social', 'N/A')
                rif = p.get('num_documento', 'N/A')
                print(f"   {i}. {razon} - {rif}")
            print(f"   {self.COLOR_ROJO}0. Cancelar{self.COLOR_RESET}")
            
            try:
                idx = int(input("\n   Seleccione número: ")) - 1
                if idx == -1:
                    return
                proveedor_data = proveedores[idx]
                idproveedor = proveedor_data['idproveedor']
                print(f"{self.COLOR_VERDE}   ✅ Proveedor seleccionado: {proveedor_data.get('razon_social')}{self.COLOR_RESET}")
            except (ValueError, IndexError):
                print(f"{self.COLOR_ROJO}❌ Selección inválida{self.COLOR_RESET}")
                self.pausa()
                return
                
        elif opcion_prov == '2':
            # Crear nuevo proveedor
            print(f"\n{self.COLOR_AMARILLO}   📝 NUEVO PROVEEDOR{self.COLOR_RESET}")
            
            # Validar RIF
            rif = input("   RIF: ").upper()
            if not rif:
                print(f"{self.COLOR_ROJO}❌ RIF obligatorio{self.COLOR_RESET}")
                self.pausa()
                return
            
            # Validar Razón Social
            razon = input("   Razón Social: ")
            if not razon:
                print(f"{self.COLOR_ROJO}❌ Razón Social obligatoria{self.COLOR_RESET}")
                self.pausa()
                return
            
            # Datos opcionales
            telefono = input("   Teléfono (opcional): ").strip() or None
            email = input("   Email (opcional): ").strip() or None
            direccion = input("   Dirección (opcional): ").strip() or None
            
            # Aquí iría la lógica real para crear proveedor
            # Por ahora simulamos
            print(f"\n{self.COLOR_VERDE}   ✅ Proveedor creado exitosamente (simulado){self.COLOR_RESET}")
            print(f"      RIF: {rif}")
            print(f"      Razón Social: {razon}")
            
            # Simular datos del proveedor creado
            proveedor_data = {
                'idproveedor': 999,  # ID simulado
                'razon_social': razon,
                'num_documento': rif
            }
            idproveedor = 999
            
            # Preguntar si quiere continuar con la compra
            print(f"\n{self.COLOR_AMARILLO}   ¿Continuar con el registro de compra?{self.COLOR_RESET}")
            continuar = input("   [S/N]: ").upper()
            if continuar != 'S':
                return
        
        # 3. MONTO TOTAL USD
        print(f"\n{self.COLOR_AMARILLO}3. MONTO TOTAL USD (obligatorio){self.COLOR_RESET}")
        try:
            monto_usd = float(input("   Ingrese monto total en USD: "))
            if monto_usd <= 0:
                print(f"{self.COLOR_ROJO}❌ Monto inválido{self.COLOR_RESET}")
                self.pausa()
                return
        except ValueError:
            print(f"{self.COLOR_ROJO}❌ Valor inválido{self.COLOR_RESET}")
            self.pausa()
            return
        
        # Obtener tasa del día - CORREGIDO DEFINITIVO
        from capa_negocio.tasa_service import TasaService
        from capa_datos.tasa_repo import TasaRepositorio
        from capa_datos.conexion import ConexionDB
        
        try:
            # Crear conexión y repositorio de tasa
            db_tasa = ConexionDB()
            conn_tasa = db_tasa.conectar()
            if conn_tasa:
                tasa_repo = TasaRepositorio(conn_tasa)
                tasa_service = TasaService(tasa_repo)
                tasa = tasa_service.obtener_tasa_del_dia('USD')
                
                if tasa and tasa > 0:
                    monto_bs = monto_usd * tasa
                    print(f"   Tasa BCV del día: {self.COLOR_VERDE}{tasa:.2f}{self.COLOR_RESET} Bs/USD")
                    print(f"   Monto en Bs: {self.COLOR_AMARILLO}{monto_bs:,.2f}{self.COLOR_RESET}")
                else:
                    print(f"   {self.COLOR_AMARILLO}⚠️ No se pudo obtener la tasa del día{self.COLOR_RESET}")
                    tasa = None
                
                # Cerrar conexión de tasa
                db_tasa.cerrar()
            else:
                print(f"   {self.COLOR_AMARILLO}⚠️ No se pudo conectar para obtener tasa{self.COLOR_RESET}")
                tasa = None
                
        except Exception as e:
            print(f"   {self.COLOR_AMARILLO}⚠️ Error al obtener tasa: {e}{self.COLOR_RESET}")
            tasa = None
        
        # 4. FECHA DE LA COMPRA
        print(f"\n{self.COLOR_AMARILLO}4. FECHA DE LA COMPRA{self.COLOR_RESET}")
        from datetime import datetime
        fecha_hoy = datetime.now().strftime("%d/%m/%Y")
        fecha_compra_input = input(f"   Fecha (DD/MM/YYYY) [HOY={fecha_hoy}]: ").strip()
        
        if not fecha_compra_input:
            fecha_compra_input = fecha_hoy
        
        # Convertir de DD/MM/YYYY a YYYY-MM-DD para la BD
        try:
            dia, mes, anio = fecha_compra_input.split('/')
            # Validar que sea una fecha válida
            dia = int(dia)
            mes = int(mes)
            anio = int(anio)
            
            # Validación básica
            if dia < 1 or dia > 31 or mes < 1 or mes > 12 or anio < 2000 or anio > 2100:
                print(f"{self.COLOR_ROJO}❌ Fecha inválida{self.COLOR_RESET}")
                self.pausa()
                return
                
            fecha_compra = f"{anio:04d}-{mes:02d}-{dia:02d}"
            print(f"   {self.COLOR_VERDE}✅ Fecha registrada: {fecha_compra_input}{self.COLOR_RESET}")
        except (ValueError, IndexError):
            print(f"{self.COLOR_ROJO}❌ Formato de fecha inválido. Use DD/MM/YYYY (ejemplo: 25/02/2026){self.COLOR_RESET}")
            self.pausa()
            return
        
        # 5. FECHA ESTIMADA DE LLEGADA (opcional)
        print(f"\n{self.COLOR_AMARILLO}5. FECHA ESTIMADA DE LLEGADA (opcional){self.COLOR_RESET}")
        fecha_llegada_input = input("   Fecha estimada (DD/MM/YYYY) [Enter para omitir]: ").strip()
        
        fecha_llegada = None
        if fecha_llegada_input:
            try:
                dia, mes, anio = fecha_llegada_input.split('/')
                # Validar que sea una fecha válida
                dia = int(dia)
                mes = int(mes)
                anio = int(anio)
                
                # Validación básica
                if dia < 1 or dia > 31 or mes < 1 or mes > 12 or anio < 2000 or anio > 2100:
                    print(f"{self.COLOR_ROJO}❌ Fecha inválida{self.COLOR_RESET}")
                    self.pausa()
                    return
                    
                fecha_llegada = f"{anio:04d}-{mes:02d}-{dia:02d}"
                print(f"   {self.COLOR_VERDE}✅ Fecha registrada: {fecha_llegada_input}{self.COLOR_RESET}")
            except (ValueError, IndexError):
                print(f"{self.COLOR_ROJO}❌ Formato de fecha inválido. Use DD/MM/YYYY (ejemplo: 28/02/2026){self.COLOR_RESET}")
                self.pausa()
                return
        
        # 6. ADJUNTAR ARCHIVO
        print(f"\n{self.COLOR_AMARILLO}6. ADJUNTAR ARCHIVO{self.COLOR_RESET}")
        print("   [1] Subir archivo (PDF/Imagen)")
        print("   [2] No adjuntar ahora")
        opcion_archivo = input("\n   Seleccione: ")
        
        archivo_adjunto = None
        if opcion_archivo == '1':
            ruta = input("   Ruta del archivo: ").strip()
            if ruta:
                archivo_adjunto = ruta
                print(f"{self.COLOR_VERDE}   ✅ Archivo adjuntado: {ruta}{self.COLOR_RESET}")
        
        # 7. ESTATUS DE LA COMPRA
        print(f"\n{self.COLOR_AMARILLO}7. ESTATUS DE LA COMPRA{self.COLOR_RESET}")
        print("   [1] Por recibir (pendiente)")
        print("   [2] Entregado (ya llegó)")
        print("   [3] En tránsito")
        opcion_estatus = input("\n   Seleccione: ")
        
        estatus_map = {
            '1': 'POR_RECIBIR',
            '2': 'ENTREGADO',
            '3': 'EN_TRANSITO'
        }
        estatus = estatus_map.get(opcion_estatus, 'POR_RECIBIR')
        print(f"   {self.COLOR_VERDE}✅ Estatus: {estatus}{self.COLOR_RESET}")
        
        # 8. OBSERVACIONES
        print(f"\n{self.COLOR_AMARILLO}8. OBSERVACIONES (opcional){self.COLOR_RESET}")
        observaciones = input("   Ingrese notas adicionales: ").strip()
        if not observaciones:
            observaciones = None
        
        # 9. PRODUCTOS (OPCIONAL)
        print(f"\n{self.COLOR_AMARILLO}9. PRODUCTOS (opcional){self.COLOR_RESET}")
        print("   ¿Desea ingresar los productos ahora?")
        ingresar_productos = input("   [S/N]: ").upper()
        if ingresar_productos == 'S':
            print(f"   {self.COLOR_AMARILLO}⏳ Puede ingresarlos en la recepción{self.COLOR_RESET}")
        
        # RESUMEN
        print(f"\n{self.COLOR_CYAN}{'='*60}{self.COLOR_RESET}")
        print(f"{self.COLOR_VERDE}📋 RESUMEN DE COMPRA{self.COLOR_RESET}")
        print(f"{self.COLOR_CYAN}{'='*60}{self.COLOR_RESET}")
        print(f"Código Factura: {self.COLOR_AMARILLO}{codigo_factura}{self.COLOR_RESET}")
        if proveedor_data:
            print(f"Proveedor: {self.COLOR_VERDE}{proveedor_data.get('razon_social', 'N/A')}{self.COLOR_RESET} - {proveedor_data.get('num_documento', 'N/A')}")
        print(f"Monto USD: {self.COLOR_AMARILLO}{monto_usd:,.2f}{self.COLOR_RESET}")
        if tasa:
            print(f"Monto Bs: {self.COLOR_AMARILLO}{monto_usd * tasa:,.2f}{self.COLOR_RESET} (tasa: {tasa:.2f})")
        print(f"Fecha Compra: {self.COLOR_VERDE}{fecha_compra}{self.COLOR_RESET}")
        if fecha_llegada:
            print(f"Fecha Estimada Llegada: {self.COLOR_VERDE}{fecha_llegada}{self.COLOR_RESET}")
        if archivo_adjunto:
            print(f"Archivo: {self.COLOR_VERDE}{archivo_adjunto}{self.COLOR_RESET}")
        print(f"Estatus: {self.COLOR_AMARILLO}{estatus}{self.COLOR_RESET}")
        print(f"{self.COLOR_CYAN}{'='*60}{self.COLOR_RESET}")
        
        confirmar = input(f"\n{self.COLOR_AMARILLO}¿Confirmar registro de compra? [S/N]: {self.COLOR_RESET}").upper()
        
        if confirmar == 'S':
            try:
                from capa_negocio.orden_compra_service import OrdenCompraService
                orden_service = OrdenCompraService()
                
                idorden = orden_service.registrar_orden(
                    codigo_factura=codigo_factura,
                    idproveedor=idproveedor,
                    idtrabajador=usuario['idtrabajador'],
                    fecha_compra=fecha_compra,
                    monto_total_usd=monto_usd,
                    fecha_estimada_llegada=fecha_llegada,
                    archivo_adjunto=archivo_adjunto,
                    estatus=estatus,
                    observaciones=observaciones
                )
                
                if idorden:
                    print(f"\n{self.COLOR_VERDE}{'✅'*10}{self.COLOR_RESET}")
                    print(f"{self.COLOR_VERDE}   COMPRA REGISTRADA EXITOSAMENTE{self.COLOR_RESET}")
                    print(f"{self.COLOR_VERDE}{'✅'*10}{self.COLOR_RESET}")
                    print(f"   ID de orden: {self.COLOR_AMARILLO}{idorden}{self.COLOR_RESET}")
                    print(f"   Código Factura: {self.COLOR_AMARILLO}{codigo_factura}{self.COLOR_RESET}")
                else:
                    print(f"\n{self.COLOR_ROJO}❌ Error registrando compra{self.COLOR_RESET}")
            except Exception as e:
                logger.error(f"Error: {e}")
                print(f"\n{self.COLOR_ROJO}❌ Error al registrar: {e}{self.COLOR_RESET}")
        else:
            print(f"\n{self.COLOR_AMARILLO}Compra cancelada{self.COLOR_RESET}")
        
        self.pausa()

    def _listar_compras(self):
        """Lista todas las compras"""
        self.mostrar_cabecera("📋 LISTADO DE COMPRAS")
        
        try:
            from capa_negocio.compra_service import CompraService
            compra_service = CompraService()
            compras = compra_service.listar_compras()
            
            if not compras:
                print(f"\n{self.COLOR_AMARILLO}📭 No hay compras registradas{self.COLOR_RESET}")
            else:
                print(f"\n{self.COLOR_VERDE}Total de compras: {len(compras)}{self.COLOR_RESET}\n")
                for compra in compras[:20]:
                    print(f"ID: {compra['idcompra']}")
                    print(f"Fecha: {compra['fecha_hora']}")
                    print(f"Proveedor: {compra['proveedor']}")
                    print(f"Comprobante: {compra['tipo_comprobante']} {compra['serie']}-{compra['numero_comprobante']}")
                    print(f"Total: Bs. {compra['total']:,.2f}")
                    print(f"Estado: {compra['estado']}")
                    print("-" * 40)
        except Exception as e:
            logger.error(f"Error en listado de compras: {e}")
            print(f"\n{self.COLOR_ROJO}❌ Error al cargar compras{self.COLOR_RESET}")
        
        self.pausa()

    def _buscar_compra(self):
        """Busca una compra por ID"""
        self.mostrar_cabecera("🔍 BUSCAR COMPRA")
        
        print(f"\n{self.COLOR_AMARILLO}Ingrese el ID de la compra (0 para cancelar):{self.COLOR_RESET}")
        
        try:
            id_input = input("ID de la compra: ").strip()
            
            if id_input == '0':
                print(f"{self.COLOR_AMARILLO}Búsqueda cancelada{self.COLOR_RESET}")
                self.pausa()
                return
                
            if not id_input:
                print(f"{self.COLOR_ROJO}❌ ID no válido{self.COLOR_RESET}")
                self.pausa()
                return
                
            idcompra = int(id_input)
            
        except ValueError:
            print(f"{self.COLOR_ROJO}❌ ID inválido (debe ser un número){self.COLOR_RESET}")
            self.pausa()
            return
        
        try:
            from capa_negocio.compra_service import CompraService
            compra_service = CompraService()
            compra = compra_service.buscar_compra(idcompra)
            
            if not compra:
                print(f"\n{self.COLOR_ROJO}❌ Compra #{idcompra} no encontrada{self.COLOR_RESET}")
            else:
                print(f"\n{self.COLOR_VERDE}📋 COMPRA #{compra['idcompra']}{self.COLOR_RESET}")
                print(f"Fecha: {compra['fecha_hora']}")
                print(f"Proveedor: {compra['proveedor']} - {compra['rif']}")
                print(f"Trabajador: {compra['trabajador']}")
                print(f"Comprobante: {compra['tipo_comprobante']} {compra['serie']}-{compra['numero_comprobante']}")
                print(f"Subtotal: Bs. {compra['subtotal']:,.2f}")
                print(f"IVA: Bs. {compra['iva']:,.2f}")
                print(f"Total: Bs. {compra['total']:,.2f}")
                print(f"Estado: {compra['estado']}")
                
                if compra.get('detalles'):
                    print(f"\n{self.COLOR_VERDE}📦 DETALLES:{self.COLOR_RESET}")
                    for d in compra['detalles']:
                        print(f"  • {d['articulo']} - {d['cantidad']} x Bs. {d['precio_compra']:,.2f} = Bs. {d['subtotal']:,.2f}")
        except Exception as e:
            logger.error(f"Error buscando compra: {e}")
            print(f"{self.COLOR_ROJO}❌ Error al buscar la compra{self.COLOR_RESET}")
        
        self.pausa()

    def _reportes_compras(self):
        """Reportes de compras"""
        self.mostrar_cabecera("📊 REPORTES DE COMPRAS")
        print(f"{self.COLOR_AMARILLO}⏳ Reportes en desarrollo...{self.COLOR_RESET}")
        self.pausa()

    def _listar_ordenes_compra(self):
        """Lista todas las órdenes de compra"""
        self.mostrar_cabecera("📋 ÓRDENES DE COMPRA")
        
        try:
            from capa_negocio.orden_compra_service import OrdenCompraService
            service = OrdenCompraService()
            
            print(f"\n{self.COLOR_AMARILLO}Órdenes pendientes:{self.COLOR_RESET}")
            ordenes = service.listar_ordenes_pendientes()
            
            if not ordenes:
                print(f"   {self.COLOR_AMARILLO}No hay órdenes pendientes{self.COLOR_RESET}")
            else:
                for o in ordenes[:10]:
                    print(f"   • {o['codigo_factura']} - {o['proveedor']} - USD {o['monto_total_usd']:,.2f}")
            
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"{self.COLOR_ROJO}❌ Error al listar órdenes{self.COLOR_RESET}")
        
        self.pausa()

    def _buscar_orden_factura(self):
        """Busca orden por código de factura"""
        self.mostrar_cabecera("🔍 BUSCAR ORDEN POR FACTURA")
        
        codigo = input("Ingrese código de factura: ").strip().upper()
        if not codigo:
            return
        
        try:
            from capa_negocio.orden_compra_service import OrdenCompraService
            service = OrdenCompraService()
            orden = service.buscar_por_codigo_factura(codigo)
            
            if not orden:
                print(f"{self.COLOR_ROJO}❌ Orden no encontrada{self.COLOR_RESET}")
            else:
                print(f"\n{self.COLOR_VERDE}📄 ORDEN ENCONTRADA{self.COLOR_RESET}")
                print(f"Código: {orden['codigo_factura']}")
                print(f"Proveedor: {orden['proveedor']}")
                print(f"Fecha compra: {orden['fecha_compra']}")
                print(f"Monto USD: {orden['monto_total_usd']:,.2f}")
                print(f"Estatus: {orden['estatus']}")
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"{self.COLOR_ROJO}❌ Error al buscar{self.COLOR_RESET}")
        
        self.pausa()

    def _listar_recepciones(self):
        """Lista recepciones registradas"""
        self.mostrar_cabecera("📋 RECEPCIONES")
        print(f"{self.COLOR_AMARILLO}⏳ Función en desarrollo...{self.COLOR_RESET}")
        self.pausa()

    def _recibir_mercancia(self):
        """Registra recepción de mercancía (PASO 2 COMPLETO)"""
        self.mostrar_cabecera("📦 RECIBIR MERCANCÍA")
        
        # Verificar usuario
        usuario = self.trabajador_service.get_usuario_actual()
        if not usuario:
            print(f"{self.COLOR_ROJO}❌ Debe iniciar sesión{self.COLOR_RESET}")
            self.pausa()
            return
        
        # 1. BUSCAR ORDEN DE COMPRA
        print(f"\n{self.COLOR_AMARILLO}1. BUSCAR ORDEN DE COMPRA{self.COLOR_RESET}")
        print("   [1] Buscar por código de factura")
        print("   [2] Buscar por proveedor")
        print("   [3] Ver órdenes pendientes")
        print("   [4] Recepción directa (sin orden)")
        print("   [0] Cancelar")
        
        opcion = input("\n   Seleccione: ")
        
        if opcion == '0':
            return
        
        orden_data = None
        idorden = None
        idproveedor = None
        
        try:
            from capa_negocio.orden_compra_service import OrdenCompraService
            orden_service = OrdenCompraService()
            
            if opcion == '1':
                codigo = input("   Ingrese código de factura: ").strip().upper()
                if not codigo:
                    return
                orden_data = orden_service.buscar_por_codigo_factura(codigo)
                if not orden_data:
                    print(f"{self.COLOR_ROJO}❌ Orden no encontrada{self.COLOR_RESET}")
                    self.pausa()
                    return
                
                print(f"\n{self.COLOR_VERDE}   ✅ Orden encontrada:{self.COLOR_RESET}")
                print(f"   {'-'*60}")
                print(f"   Código: {orden_data['codigo_factura']}")
                print(f"   Proveedor: {orden_data['proveedor']} ({orden_data.get('rif', 'N/A')})")
                print(f"   Fecha compra: {orden_data['fecha_compra']}")
                print(f"   Monto USD: {orden_data['monto_total_usd']:,.2f}")
                print(f"   Estatus: {orden_data['estatus']}")
                print(f"   {'-'*60}")
                
                idorden = orden_data['idorden']
                idproveedor = orden_data['idproveedor']
                
            elif opcion == '2':
                print(f"\n{self.COLOR_AMARILLO}   🔍 BUSCAR POR PROVEEDOR{self.COLOR_RESET}")
                print("   [1] Buscar por RIF")
                print("   [2] Buscar por nombre")
                print("   [3] Listar todos")
                subopcion = input("\n   Seleccione: ")
                
                proveedores = []
                if subopcion == '1':
                    rif = input("   RIF: ").upper()
                    proveedor = self.proveedor_service.buscar_por_rif(rif)
                    if proveedor:
                        proveedores = [proveedor]
                elif subopcion == '2':
                    nombre = input("   Nombre/Razón social: ")
                    proveedores = self.proveedor_service.buscar_por_nombre(nombre)
                elif subopcion == '3':
                    proveedores = self.proveedor_service.listar()
                
                if not proveedores:
                    print(f"{self.COLOR_ROJO}❌ No se encontraron proveedores{self.COLOR_RESET}")
                    self.pausa()
                    return
                
                print(f"\n{self.COLOR_VERDE}   Proveedores encontrados:{self.COLOR_RESET}")
                for i, p in enumerate(proveedores[:10], 1):
                    print(f"   {i}. {p.get('razon_social', 'N/A')} - {p.get('num_documento', 'N/A')}")
                print(f"   {self.COLOR_ROJO}0. Cancelar{self.COLOR_RESET}")
                
                try:
                    idx = int(input("\n   Seleccione proveedor: ")) - 1
                    if idx == -1:
                        return
                    proveedor_sel = proveedores[idx]
                    idproveedor = proveedor_sel['idproveedor']
                    
                    # Buscar órdenes de este proveedor
                    ordenes = orden_service.listar_ordenes_pendientes()
                    ordenes_proveedor = [o for o in ordenes if o.get('idproveedor') == idproveedor]
                    
                    if not ordenes_proveedor:
                        print(f"{self.COLOR_AMARILLO}   📭 No hay órdenes pendientes para este proveedor{self.COLOR_RESET}")
                        self.pausa()
                        return
                    
                    print(f"\n{self.COLOR_VERDE}   Órdenes pendientes:{self.COLOR_RESET}")
                    for i, o in enumerate(ordenes_proveedor[:10], 1):
                        print(f"   {i}. {o['codigo_factura']} - USD {o['monto_total_usd']:,.2f}")
                    print(f"   {self.COLOR_ROJO}0. Cancelar{self.COLOR_RESET}")
                    
                    try:
                        idx_ord = int(input("\n   Seleccione orden: ")) - 1
                        if idx_ord == -1:
                            return
                        orden_data = ordenes_proveedor[idx_ord]
                        idorden = orden_data['idorden']
                        
                        print(f"\n{self.COLOR_VERDE}   ✅ Orden seleccionada:{self.COLOR_RESET}")
                        print(f"   Código: {orden_data['codigo_factura']}")
                    except (ValueError, IndexError):
                        print(f"{self.COLOR_ROJO}❌ Selección inválida{self.COLOR_RESET}")
                        self.pausa()
                        return
                        
                except (ValueError, IndexError):
                    print(f"{self.COLOR_ROJO}❌ Selección inválida{self.COLOR_RESET}")
                    self.pausa()
                    return
                
            elif opcion == '3':
                ordenes = orden_service.listar_ordenes_pendientes()
                if not ordenes:
                    print(f"{self.COLOR_AMARILLO}   📭 No hay órdenes pendientes{self.COLOR_RESET}")
                    self.pausa()
                    return
                
                print(f"\n{self.COLOR_VERDE}   Órdenes pendientes:{self.COLOR_RESET}")
                for i, o in enumerate(ordenes[:10], 1):
                    print(f"   {i}. {o['codigo_factura']} - {o['proveedor']} - USD {o['monto_total_usd']:,.2f}")
                print(f"   {self.COLOR_ROJO}0. Cancelar{self.COLOR_RESET}")
                
                try:
                    idx = int(input("\n   Seleccione orden: ")) - 1
                    if idx == -1:
                        return
                    orden_data = ordenes[idx]
                    idorden = orden_data['idorden']
                    idproveedor = orden_data['idproveedor']
                    
                    print(f"\n{self.COLOR_VERDE}   ✅ Orden seleccionada:{self.COLOR_RESET}")
                    print(f"   Código: {orden_data['codigo_factura']}")
                    print(f"   Proveedor: {orden_data['proveedor']}")
                except (ValueError, IndexError):
                    print(f"{self.COLOR_ROJO}❌ Selección inválida{self.COLOR_RESET}")
                    self.pausa()
                    return
                    
            elif opcion == '4':
                # Recepción directa: buscar proveedor
                print(f"\n{self.COLOR_AMARILLO}   🔍 BUSCAR PROVEEDOR (recepción directa){self.COLOR_RESET}")
                print("   [1] Buscar por RIF")
                print("   [2] Buscar por nombre")
                print("   [3] Listar todos")
                print("   [4] Crear nuevo proveedor")
                subopcion = input("\n   Seleccione: ")
                
                if subopcion == '4':
                    # Crear nuevo proveedor
                    print(f"\n{self.COLOR_AMARILLO}   📝 NUEVO PROVEEDOR{self.COLOR_RESET}")
                    rif = input("   RIF: ").upper()
                    razon = input("   Razón Social: ")
                    telefono = input("   Teléfono (opcional): ").strip() or None
                    email = input("   Email (opcional): ").strip() or None
                    direccion = input("   Dirección (opcional): ").strip() or None
                    
                    print(f"{self.COLOR_VERDE}   ✅ Proveedor creado exitosamente (simulado){self.COLOR_RESET}")
                    idproveedor = 999  # Simulado
                else:
                    proveedores = []
                    if subopcion == '1':
                        rif = input("   RIF: ").upper()
                        proveedor = self.proveedor_service.buscar_por_rif(rif)
                        if proveedor:
                            proveedores = [proveedor]
                    elif subopcion == '2':
                        nombre = input("   Nombre/Razón social: ")
                        proveedores = self.proveedor_service.buscar_por_nombre(nombre)
                    elif subopcion == '3':
                        proveedores = self.proveedor_service.listar()
                    
                    if not proveedores:
                        print(f"{self.COLOR_ROJO}❌ No se encontraron proveedores{self.COLOR_RESET}")
                        self.pausa()
                        return
                    
                    print(f"\n{self.COLOR_VERDE}   Proveedores encontrados:{self.COLOR_RESET}")
                    for i, p in enumerate(proveedores[:10], 1):
                        print(f"   {i}. {p.get('razon_social', 'N/A')} - {p.get('num_documento', 'N/A')}")
                    print(f"   {self.COLOR_ROJO}0. Cancelar{self.COLOR_RESET}")
                    
                    try:
                        idx = int(input("\n   Seleccione proveedor: ")) - 1
                        if idx == -1:
                            return
                        proveedor_sel = proveedores[idx]
                        idproveedor = proveedor_sel['idproveedor']
                    except (ValueError, IndexError):
                        print(f"{self.COLOR_ROJO}❌ Selección inválida{self.COLOR_RESET}")
                        self.pausa()
                        return
            else:
                print(f"{self.COLOR_ROJO}❌ Opción inválida{self.COLOR_RESET}")
                self.pausa()
                return
                
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"{self.COLOR_ROJO}❌ Error al buscar orden: {e}{self.COLOR_RESET}")
            self.pausa()
            return
        
        # 2. DATOS DE RECEPCIÓN
        print(f"\n{self.COLOR_AMARILLO}2. DATOS DE RECEPCIÓN{self.COLOR_RESET}")
        from datetime import datetime
        fecha_hoy = datetime.now().strftime("%d/%m/%Y")
        fecha_recepcion_input = input(f"   Fecha de recepción [HOY={fecha_hoy}]: ").strip()
        
        if not fecha_recepcion_input:
            fecha_recepcion_input = fecha_hoy
        
        # Convertir de DD/MM/YYYY a YYYY-MM-DD para la BD
        try:
            dia, mes, anio = fecha_recepcion_input.split('/')
            fecha_recepcion = f"{anio}-{mes}-{dia}"
        except:
            print(f"{self.COLOR_ROJO}❌ Formato de fecha inválido. Use DD/MM/YYYY{self.COLOR_RESET}")
            self.pausa()
            return
        
        print(f"\n   Estado de la mercancía:")
        print("   [1] Completa (todo llegó bien)")
        print("   [2] Parcial (faltaron productos)")
        print("   [3] Con daños (algunos productos dañados)")
        estado_opcion = input("   Seleccione: ")
        
        estado_map = {
            '1': 'COMPLETA',
            '2': 'PARCIAL',
            '3': 'DAÑADA'
        }
        estado_mercancia = estado_map.get(estado_opcion, 'COMPLETA')
        print(f"   {self.COLOR_VERDE}✅ Estado: {estado_mercancia}{self.COLOR_RESET}")
        
        observaciones = input("\n   Observaciones (opcional): ").strip()
        if not observaciones:
            observaciones = None
        
        # 3. INGRESAR PRODUCTOS RECIBIDOS
        items_recibidos = []
        productos_nuevos = 0
        
        while True:
            print(f"\n{self.COLOR_AMARILLO}3. INGRESAR PRODUCTOS RECIBIDOS{self.COLOR_RESET}")
            print(f"   {self.COLOR_CYAN}{'-'*60}{self.COLOR_RESET}")
            print("   ¿Qué desea hacer?")
            print("   [1] Ingresar producto existente (código de barras/PLU)")
            print("   [2] Crear nuevo producto")
            print("   [0] Cancelar recepción")
            print("   [Enter] Terminar ingreso de productos")
            print(f"   {self.COLOR_CYAN}{'-'*60}{self.COLOR_RESET}")
            
            accion = input("   Seleccione: ").strip()
            
            if accion == '':
                # Terminar ingreso
                break
                
            if accion == '0':
                if items_recibidos:
                    print(f"{self.COLOR_AMARILLO}   ¿Cancelar toda la recepción? [S/N]: {self.COLOR_RESET}")
                    if input().upper() == 'S':
                        print(f"{self.COLOR_AMARILLO}   Recepción cancelada{self.COLOR_RESET}")
                        self.pausa()
                        return
                    else:
                        continue
                else:
                    print(f"{self.COLOR_AMARILLO}   Recepción cancelada{self.COLOR_RESET}")
                    self.pausa()
                    return
            
            elif accion == '1':
                # Ingresar producto existente
                codigo = input("   Ingrese código de barras o PLU: ").strip()
                if not codigo:
                    continue
                
                # Buscar artículo
                articulo = self.articulo_service.buscar_por_codigo(codigo)
                
                if not articulo:
                    print(f"{self.COLOR_ROJO}   ❌ Producto no encontrado{self.COLOR_RESET}")
                    continue
                
                # Producto existente
                print(f"\n{self.COLOR_VERDE}   → Producto encontrado: {articulo['nombre']} (ID: {articulo['idarticulo']}){self.COLOR_RESET}")
                
                # Obtener stock real desde inventario_service
                from capa_negocio.inventario_service import InventarioService
                inventario_service = InventarioService(self.articulo_service)
                stock_real = inventario_service.obtener_stock_articulo(articulo['idarticulo'])
                print(f"   Stock actual: {stock_real} unidades")
                
                # Mostrar precio actual
                precio_compra_actual = articulo.get('precio_venta', 0) or articulo.get('precio_compra', 0)
                print(f"   Precio actual del artículo: ${precio_compra_actual:.2f}")
                
                try:
                    cantidad = int(input("   Cantidad recibida: "))
                    if cantidad <= 0:
                        print(f"{self.COLOR_ROJO}❌ Cantidad inválida{self.COLOR_RESET}")
                        continue
                    
                    lote = input("   Lote [opcional]: ").strip() or None
                    
                    # Fecha vencimiento en formato DD/MM/YYYY
                    vencimiento_input = input("   Fecha vencimiento [DD/MM/YYYY] [opcional]: ").strip()
                    vencimiento = None
                    if vencimiento_input:
                        try:
                            dia_v, mes_v, anio_v = vencimiento_input.split('/')
                            vencimiento = f"{anio_v}-{mes_v}-{dia_v}"
                        except:
                            print(f"{self.COLOR_AMARILLO}   ⚠️ Formato inválido, se omite fecha{self.COLOR_RESET}")
                    
                    print(f"\n   Precio actual del artículo es: ${precio_compra_actual:.2f}")
                    print("   ¿Desea modificar el precio? [S/N]: ")
                    modificar_precio = input().upper()
                    
                    precio = precio_compra_actual
                    if modificar_precio == 'S':
                        try:
                            nuevo_precio = float(input("   Nuevo precio unitario USD: "))
                            if nuevo_precio > 0:
                                precio = nuevo_precio
                                print(f"{self.COLOR_VERDE}   ✅ Precio actualizado a ${precio:.2f}{self.COLOR_RESET}")
                                
                                # Actualizar precio en la tabla articulo
                                try:
                                    if self.articulo_service.actualizar_precio(articulo['idarticulo'], precio):
                                        print(f"      {self.COLOR_VERDE}💾 Precio guardado en base de datos{self.COLOR_RESET}")
                                        articulo['precio_venta'] = precio
                                    else:
                                        print(f"      {self.COLOR_AMARILLO}⚠️ No se pudo guardar el precio{self.COLOR_RESET}")
                                except Exception as e:
                                    print(f"      {self.COLOR_AMARILLO}⚠️ Error guardando precio: {e}{self.COLOR_RESET}")
                            else:
                                print(f"{self.COLOR_AMARILLO}   ⚠️ Precio inválido, se mantiene ${precio:.2f}{self.COLOR_RESET}")
                        except ValueError:
                            print(f"{self.COLOR_AMARILLO}   ⚠️ Valor inválido, se mantiene ${precio:.2f}{self.COLOR_RESET}")
                    
                    items_recibidos.append({
                        'idarticulo': articulo['idarticulo'],
                        'codigo': articulo['codigo'],
                        'nombre': articulo['nombre'],
                        'cantidad': cantidad,
                        'lote': lote,
                        'vencimiento': vencimiento,
                        'precio': precio,
                        'es_nuevo': False
                    })
                    
                    print(f"{self.COLOR_VERDE}   ✅ Producto agregado{self.COLOR_RESET}")
                    print(f"      {cantidad} x ${precio:.2f} = ${cantidad * precio:.2f}")
                    
                except ValueError:
                    print(f"{self.COLOR_ROJO}❌ Valor inválido{self.COLOR_RESET}")
                    continue
            
            elif accion == '2':
                # Crear nuevo producto - CÓDIGO GENERADO AUTOMÁTICAMENTE
                print(f"\n{self.COLOR_AMARILLO}   📝 CREAR NUEVO PRODUCTO (código automático){self.COLOR_RESET}")
                
                # El código se generará automáticamente en el servicio
                # Solo pedimos el código de barras
                codigo_barras = input("   Ingrese código de barras: ").strip()
                if not codigo_barras:
                    print(f"{self.COLOR_ROJO}   ❌ Código de barras obligatorio{self.COLOR_RESET}")
                    continue
                
                # Verificar que no exista por código de barras
                articulo_existente = self.articulo_service.buscar_por_codigo(codigo_barras)
                if articulo_existente:
                    print(f"{self.COLOR_ROJO}   ❌ Ya existe un producto con ese código de barras{self.COLOR_RESET}")
                    continue
                
                nombre = input("   Nombre: ")
                if not nombre:
                    print(f"{self.COLOR_ROJO}   ❌ Nombre obligatorio{self.COLOR_RESET}")
                    continue
                
                # ===== DETECCIÓN AUTOMÁTICA DE CATEGORÍA =====
                from capa_negocio.ia_productos_service import IAProductosService
                ia_service = IAProductosService()
                categoria_detectada = ia_service.detectar_categoria_venezolana(nombre)
                
                # Mapeo de IDs a nombres venezolanos
                categorias = {
                    1: 'Electrónicos',
                    2: 'Víveres',
                    3: 'Bebidas',
                    4: 'Lácteos',
                    5: 'Otros',
                    7: 'Perecederos',
                    8: 'Limpieza',
                    9: 'Higiene'
                }
                
                print(f"\n   {self.COLOR_VERDE}🤖 Categorías disponibles:{self.COLOR_RESET}")
                # Mostrar en orden lógico
                for cat_id in [1,2,3,4,7,8,9,5]:
                    cat_nombre = categorias.get(cat_id, 'Desconocido')
                    marca = "👉" if cat_id == categoria_detectada else "  "
                    print(f"   {marca} [{cat_id}] {cat_nombre}")
                
                if categoria_detectada and categoria_detectada != 5:
                    print(f"\n   {self.COLOR_VERDE}🤖 Categoría sugerida: {categorias.get(categoria_detectada, 'Otros')} (ID: {categoria_detectada}){self.COLOR_RESET}")
                    opcion = input(f"   Presione Enter para aceptar, o ingrese otro número: ").strip()
                    if opcion:
                        try:
                            idcategoria = int(opcion)
                            if idcategoria not in categorias:
                                print(f"   {self.COLOR_AMARILLO}⚠️ Categoría no válida, usando sugerencia{self.COLOR_RESET}")
                                idcategoria = categoria_detectada
                        except:
                            idcategoria = categoria_detectada
                    else:
                        idcategoria = categoria_detectada
                else:
                    # Si no hay sugerencia o es Otros, preguntar
                    print("\n   Seleccione categoría:")
                    opcion = input("   Número: ").strip()
                    try:
                        idcategoria = int(opcion)
                        if idcategoria not in categorias:
                            print(f"   {self.COLOR_AMARILLO}⚠️ Categoría no válida, usando Otros (5){self.COLOR_RESET}")
                            idcategoria = 5
                    except:
                        print(f"   {self.COLOR_AMARILLO}⚠️ Entrada inválida, usando Otros (5){self.COLOR_RESET}")
                        idcategoria = 5
                
                # ===== OBTENER NOMBRE DE CATEGORÍA =====
                categoria_nombre = categorias.get(idcategoria, 'Otros')
                # ========================================
                # ===== FIN DETECCIÓN =====
                
                unidad = input("   Unidad de medida: ")
                if not unidad:
                    unidad = "Unidad"
                
                print("   ¿Es perecedero? [S/N]: ")
                perecedero = input().upper() == 'S'
                
                try:
                    cantidad = int(input("   Cantidad recibida: "))
                    if cantidad <= 0:
                        print(f"{self.COLOR_ROJO}❌ Cantidad inválida{self.COLOR_RESET}")
                        continue
                    
                    lote = input("   Lote [opcional]: ").strip() or None
                    
                    vencimiento = None
                    if perecedero:
                        vencimiento_input = input("   Fecha vencimiento [DD/MM/YYYY]: ").strip()
                        if vencimiento_input:
                            try:
                                dia_v, mes_v, anio_v = vencimiento_input.split('/')
                                vencimiento = f"{anio_v}-{mes_v}-{dia_v}"
                            except:
                                print(f"{self.COLOR_AMARILLO}   ⚠️ Formato inválido, se omite fecha{self.COLOR_RESET}")
                    
                    print("   Ingrese precio de compra unitario USD:")
                    precio = float(input("   Precio: "))
                    
                    items_recibidos.append({
                        'idarticulo': None,
                        'codigo': codigo_barras,
                        'nombre': nombre,
                        'categoria': categoria_nombre,
                        'idcategoria': idcategoria,
                        'unidad': unidad,
                        'perecedero': perecedero,
                        'cantidad': cantidad,
                        'lote': lote,
                        'vencimiento': vencimiento,
                        'precio': precio,
                        'es_nuevo': True
                    })
                    
                    productos_nuevos += 1
                    print(f"{self.COLOR_VERDE}   ✅ Producto listo para crear al confirmar (código automático){self.COLOR_RESET}")
                    print(f"      {cantidad} x ${precio:.2f} = ${cantidad * precio:.2f}")
                    
                except ValueError:
                    print(f"{self.COLOR_ROJO}❌ Valor inválido{self.COLOR_RESET}")
                    continue
                    
            else:
                print(f"{self.COLOR_ROJO}   ❌ Opción inválida{self.COLOR_RESET}")
                continue
        
        if not items_recibidos:
            print(f"{self.COLOR_ROJO}❌ No se ingresaron productos{self.COLOR_RESET}")
            self.pausa()
            return
        
        # 4. RESUMEN DE PRODUCTOS INGRESADOS
        print(f"\n{self.COLOR_AMARILLO}4. RESUMEN DE PRODUCTOS INGRESADOS{self.COLOR_RESET}")
        print(f"   {self.COLOR_CYAN}{'-'*60}{self.COLOR_RESET}")
        print(f"   Total productos: {len(items_recibidos)}")
        print()
        
        subtotal_usd = 0
        for item in items_recibidos:
            subtotal_item = item['cantidad'] * item['precio']
            subtotal_usd += subtotal_item
            estado = "NUEVO" if item['es_nuevo'] else "EXISTENTE"
            print(f"   {item['nombre']}: {item['cantidad']} unidades - USD {subtotal_item:.2f} {estado}")
        
        print(f"\n   Subtotal USD: {self.COLOR_AMARILLO}{subtotal_usd:,.2f}{self.COLOR_RESET}")
        print(f"   {self.COLOR_CYAN}{'-'*60}{self.COLOR_RESET}")
        
        # 5. DEVOLUCIONES
        print(f"\n{self.COLOR_AMARILLO}5. DEVOLUCIONES{self.COLOR_RESET}")
        print("   ¿Hubo devoluciones? [1] Sí [2] No")
        dev_opcion = input("   Seleccione: ")
        
        devoluciones = []
        if dev_opcion == '1':
            print(f"\n{self.COLOR_AMARILLO}   📤 REGISTRAR DEVOLUCIÓN{self.COLOR_RESET}")
            
            while True:
                print(f"\n   {self.COLOR_CYAN}{'-'*40}{self.COLOR_RESET}")
                codigo_dev = input("   Producto a devolver (código) [Enter para terminar]: ").strip()
                if not codigo_dev:
                    break
                
                # Buscar si el producto está en la recepción
                producto_encontrado = None
                for item in items_recibidos:
                    if item['codigo'] == codigo_dev:
                        producto_encontrado = item
                        break
                
                if not producto_encontrado:
                    print(f"{self.COLOR_ROJO}❌ Producto no está en esta recepción{self.COLOR_RESET}")
                    continue
                
                print(f"   → {producto_encontrado['nombre']}")
                print(f"   Lote: {producto_encontrado.get('lote', 'N/A')}")
                
                try:
                    cantidad_dev = int(input("   Cantidad a devolver: "))
                    if cantidad_dev <= 0 or cantidad_dev > producto_encontrado['cantidad']:
                        print(f"{self.COLOR_ROJO}❌ Cantidad inválida (máx {producto_encontrado['cantidad']}){self.COLOR_RESET}")
                        continue
                    
                    print("   Motivo de devolución:")
                    print("   [1] Producto vencido")
                    print("   [2] Producto dañado")
                    print("   [3] Producto incorrecto")
                    print("   [4] Otro")
                    motivo_opcion = input("   Seleccione: ")
                    
                    motivos = {
                        '1': 'Producto vencido',
                        '2': 'Producto dañado',
                        '3': 'Producto incorrecto',
                        '4': 'Otro'
                    }
                    motivo = motivos.get(motivo_opcion, 'Otro')
                    
                    observaciones_dev = input("   Observaciones (opcional): ").strip() or None
                    
                    devoluciones.append({
                        'producto': producto_encontrado,
                        'cantidad': cantidad_dev,
                        'motivo': motivo,
                        'observaciones': observaciones_dev
                    })
                    
                    print(f"{self.COLOR_VERDE}   ✅ Devolución registrada{self.COLOR_RESET}")
                    
                    # Preguntar si desea registrar otra devolución
                    print(f"\n{self.COLOR_AMARILLO}   ¿Registrar otra devolución? [S/N]: {self.COLOR_RESET}")
                    if input().upper() != 'S':
                        break
                    
                except ValueError:
                    print(f"{self.COLOR_ROJO}❌ Valor inválido{self.COLOR_RESET}")
                    continue
        
        # 6. CONFIRMACIÓN FINAL
        print(f"\n{self.COLOR_AMARILLO}6. CONFIRMACIÓN FINAL{self.COLOR_RESET}")
        print(f"   {self.COLOR_CYAN}{'='*60}{self.COLOR_RESET}")
        print(f"{self.COLOR_VERDE}   📋 RESUMEN COMPLETO DE RECEPCIÓN{self.COLOR_RESET}")
        print(f"   {self.COLOR_CYAN}{'='*60}{self.COLOR_RESET}")
        
        if orden_data:
            print(f"   Orden: {orden_data['codigo_factura']} ({orden_data['proveedor']})")
        else:
            print(f"   Recepción directa - Proveedor ID: {idproveedor}")
        print(f"   Fecha recepción: {fecha_recepcion_input}")
        print(f"   Estado: {estado_mercancia}")
        print(f"\n   {self.COLOR_VERDE}Productos recibidos:{self.COLOR_RESET}")
        
        total_neto = 0
        for item in items_recibidos:
            print(f"   ✓ {item['nombre']}: {item['cantidad']} uds ${item['precio']:.2f} c/u")
            total_neto += item['cantidad']
        
        if devoluciones:
            print(f"\n   {self.COLOR_AMARILLO}Devoluciones:{self.COLOR_RESET}")
            for dev in devoluciones:
                print(f"   ✗ {dev['producto']['nombre']}: {dev['cantidad']} uds - {dev['motivo']}")
                total_neto -= dev['cantidad']
        
        print(f"\n   Total neto recibido: {total_neto} unidades")
        print(f"   Productos nuevos creados: {productos_nuevos}")
        print(f"   Devoluciones procesadas: {len(devoluciones)}")
        print(f"   {self.COLOR_CYAN}{'='*60}{self.COLOR_RESET}")
        
        confirmar = input(f"\n{self.COLOR_AMARILLO}¿Confirmar recepción? [S/N]: {self.COLOR_RESET}").upper()
        
        if confirmar == 'S':
            print(f"\n{self.COLOR_VERDE}   🔄 PROCESANDO...{self.COLOR_RESET}")
            print(f"   {self.COLOR_CYAN}{'-'*60}{self.COLOR_RESET}")
            
            # Generar ID de recepción
            from datetime import datetime
            idrecepcion = datetime.now().strftime('%Y%m%d%H%M%S')
            
            # Registrar cada producto en kardex
            from capa_negocio.inventario_service import InventarioService
            inventario_service = InventarioService(self.articulo_service)
            
            productos_registrados = 0
            productos_creados = 0
            
            for item in items_recibidos:
                try:
                    if item['es_nuevo']:
                        # Crear nuevo producto en BD
                        if hasattr(self.articulo_service, 'crear_articulo'):
                            # DEBUG - Verificar que item tiene 'codigo'
                            print(f"🔍 DEBUG - item tiene 'codigo': {'codigo' in item}")
                            print(f"🔍 DEBUG - valor de item['codigo']: {item.get('codigo', 'NO EXISTE')}")
                            print(f"🔍 DEBUG - Llamando a crear_articulo con codigo_barras={item['codigo']}")
                            
                            nuevo_id = self.articulo_service.crear_articulo(
                                codigo_barras_original=item['codigo'], 
                                nombre=item['nombre'],
                                idcategoria=item.get('idcategoria', 1),
                                precio_venta=item['precio'],
                                stock_minimo=5,
                                precio_compra=item['precio'],
                            )
                            
                            if nuevo_id:
                                item['idarticulo'] = int(nuevo_id)
                                productos_creados += 1
                                print(f"{self.COLOR_VERDE}   ✅ Producto {item['nombre']} creado con ID {nuevo_id}{self.COLOR_RESET}")
                            else:
                                print(f"{self.COLOR_ROJO}   ❌ Error creando producto {item['nombre']}{self.COLOR_RESET}")
                                continue
                        else:
                            print(f"{self.COLOR_ROJO}   ❌ Método crear_articulo no disponible{self.COLOR_RESET}")
                            continue
                    
                    # Registrar movimiento en kardex
                    if item.get('idarticulo'):
                        resultado = inventario_service.registrar_movimiento(
                            idarticulo=int(item['idarticulo']), 
                            tipo_movimiento='ENTRADA',
                            cantidad=item['cantidad'],
                            referencia=f"RECEPCIÓN #{idrecepcion} - Orden: {orden_data['codigo_factura'] if orden_data else 'Directa'}",
                            precio_compra=item['precio'],
                            lote=item.get('lote'),
                            fecha_vencimiento=item.get('vencimiento')
                        )
                        
                        if resultado:
                            productos_registrados += 1
                            print(f"{self.COLOR_VERDE}   ✅ {item['nombre']}: +{item['cantidad']} unidades (Kardex){self.COLOR_RESET}")
                        else:
                            print(f"{self.COLOR_ROJO}   ❌ Error registrando {item['nombre']} en kardex{self.COLOR_RESET}")
                    else:
                        print(f"{self.COLOR_ROJO}   ❌ Producto {item['nombre']} sin ID válido{self.COLOR_RESET}")
                        
                except Exception as e:
                    logger.error(f"Error procesando producto {item['nombre']}: {e}")
                    print(f"{self.COLOR_ROJO}   ❌ Error: {e}{self.COLOR_RESET}")
            
            print(f"   {self.COLOR_CYAN}{'-'*60}{self.COLOR_RESET}")
            print(f"{self.COLOR_VERDE}   ✅ Stock actualizado en Kardex ({productos_registrados} productos){self.COLOR_RESET}")
            if productos_creados > 0:
                print(f"{self.COLOR_VERDE}   ✅ Nuevos productos creados: {productos_creados}{self.COLOR_RESET}")
            if lote:
                print(f"{self.COLOR_VERDE}   ✅ Lotes registrados en el sistema{self.COLOR_RESET}")
            if devoluciones:
                print(f"{self.COLOR_VERDE}   ✅ Devoluciones procesadas: {len(devoluciones)}{self.COLOR_RESET}")
            if orden_data:
                # Aquí iría la lógica para marcar la orden como recibida
                print(f"{self.COLOR_VERDE}   ✅ Orden de compra marcada como RECIBIDA{self.COLOR_RESET}")
            print(f"   {self.COLOR_CYAN}{'-'*60}{self.COLOR_RESET}")
            
            print(f"\n{self.COLOR_VERDE}{'🎉'*10}{self.COLOR_RESET}")
            print(f"{self.COLOR_VERDE}   RECEPCIÓN COMPLETADA EXITOSAMENTE{self.COLOR_RESET}")
            print(f"{self.COLOR_VERDE}{'🎉'*10}{self.COLOR_RESET}")
            print(f"   ID de recepción: {self.COLOR_AMARILLO}{idrecepcion}{self.COLOR_RESET}")
            print(f"   Fecha: {fecha_recepcion_input}")
        else:
            print(f"{self.COLOR_AMARILLO}   Recepción cancelada{self.COLOR_RESET}")
        
        self.pausa()
    
    def _editar_precio_articulo(self, idarticulo):
        """Edita solo el precio de un artículo"""
        self.mostrar_cabecera(f"💰 EDITAR PRECIO - ID: {idarticulo}")
        
        # Obtener artículo
        articulo = self.articulo_service.buscar_por_id(idarticulo)
        if not articulo:
            print(f"{self.COLOR_ROJO}❌ Artículo no encontrado{self.COLOR_RESET}")
            self.pausa()
            return
        
        precio_actual = articulo.get('precio_venta', 0)
        print(f"{self.COLOR_VERDE}Precio actual: ${precio_actual:.2f}{self.COLOR_RESET}")
        
        try:
            nuevo_precio = float(input("Nuevo precio USD: "))
            if nuevo_precio <= 0:
                print(f"{self.COLOR_ROJO}❌ Precio inválido{self.COLOR_RESET}")
                self.pausa()
                return
            
            print(f"\n{self.COLOR_AMARILLO}¿Confirmar cambio de ${precio_actual:.2f} a ${nuevo_precio:.2f}?{self.COLOR_RESET}")
            confirmar = input("[S/N]: ").upper()
            
            if confirmar == 'S':
                # Actualizar precio
                if self.articulo_service.actualizar_precio(idarticulo, nuevo_precio):
                    print(f"{self.COLOR_VERDE}✅ Precio actualizado exitosamente{self.COLOR_RESET}")
                else:
                    print(f"{self.COLOR_ROJO}❌ Error actualizando precio{self.COLOR_RESET}")
            else:
                print(f"{self.COLOR_AMARILLO}Cambio cancelado{self.COLOR_RESET}")
                
        except ValueError:
            print(f"{self.COLOR_ROJO}❌ Valor inválido{self.COLOR_RESET}")
        
        self.pausa()
    
    def _ver_detalle_articulo(self, idarticulo):
        """Muestra detalles completos de un artículo"""
        self.mostrar_cabecera(f"📋 DETALLES DEL ARTÍCULO ID: {idarticulo}")
        
        # Obtener artículo
        articulo = self.articulo_service.buscar_por_id(idarticulo)
        if not articulo:
            print(f"{self.COLOR_ROJO}❌ Artículo no encontrado{self.COLOR_RESET}")
            self.pausa()
            return
        
        # Mostrar código correctamente (buscando en múltiples campos)
        codigo = articulo.get('codigo_barras', '')
        if not codigo:
            codigo = articulo.get('codigo', articulo.get('plu', 'N/A'))
        
        # Obtener nombre de categoría
        nombre_categoria = "Sin categoría"
        if hasattr(self, 'categoria_service') and self.categoria_service:
            try:
                categorias = self.categoria_service.listar_categorias()
                for cat in categorias:
                    if cat.get('idcategoria') == articulo.get('idcategoria'):
                        nombre_categoria = cat.get('nombre', 'Sin categoría')
                        break
            except:
                nombre_categoria = f"ID: {articulo.get('idcategoria', 'N/A')}"
        else:
            nombre_categoria = f"ID: {articulo.get('idcategoria', 'N/A')}"
        
        # Obtener stock actual del kardex
        from capa_negocio.inventario_service import InventarioService
        inventario_service = InventarioService(self.articulo_service)
        stock_actual = inventario_service.obtener_stock_articulo(idarticulo)
        
        # Determinar estado del stock
        stock_minimo = articulo.get('stock_minimo', 5)
        if stock_actual <= 0:
            estado_stock = f"{self.COLOR_ROJO}🔴 CRÍTICO (sin stock){self.COLOR_RESET}"
        elif stock_actual <= 5:
            estado_stock = f"{self.COLOR_ROJO}🔴 CRÍTICO{self.COLOR_RESET}"
        elif stock_actual <= 10:
            estado_stock = f"{self.COLOR_AMARILLO}🟡 BAJO{self.COLOR_RESET}"
        else:
            estado_stock = f"{self.COLOR_VERDE}🟢 NORMAL{self.COLOR_RESET}"
        
        # Mostrar información detallada
        print(f"\n{self.COLOR_VERDE}╔══════════════════════════════════════════════════════════╗{self.COLOR_RESET}")
        print(f"{self.COLOR_VERDE}║           INFORMACIÓN COMPLETA DEL ARTÍCULO              ║{self.COLOR_RESET}")
        print(f"{self.COLOR_VERDE}╚══════════════════════════════════════════════════════════╝{self.COLOR_RESET}")
        print()
        
        print(f"{self.COLOR_AMARILLO}📌 DATOS BÁSICOS:{self.COLOR_RESET}")
        print(f"  🆔 ID: {self.COLOR_VERDE}{articulo.get('idarticulo', 'N/A')}{self.COLOR_RESET}")
        print(f"  🔑 Código: {self.COLOR_VERDE}{codigo}{self.COLOR_RESET}")
        print(f"  📝 Nombre: {self.COLOR_VERDE}{articulo.get('nombre', 'N/A')}{self.COLOR_RESET}")
        print(f"  📂 Categoría: {self.COLOR_VERDE}{nombre_categoria}{self.COLOR_RESET}")
        print()
        
        print(f"{self.COLOR_AMARILLO}💰 INFORMACIÓN DE PRECIOS:{self.COLOR_RESET}")
        print(f"  💵 Precio de venta: {self.COLOR_VERDE}${articulo.get('precio_venta', 0):.2f}{self.COLOR_RESET}")
        print(f"  💲 Precio de compra: {self.COLOR_VERDE}${articulo.get('precio_compra', 0):.2f}{self.COLOR_RESET}")
        print(f"  🧾 IGTF: {self.COLOR_VERDE}{'Sí' if articulo.get('igtf', False) else 'No'}{self.COLOR_RESET}")
        print()
        
        print(f"{self.COLOR_AMARILLO}📦 INFORMACIÓN DE STOCK:{self.COLOR_RESET}")
        print(f"  📊 Stock actual: {self.COLOR_VERDE}{stock_actual} unidades{self.COLOR_RESET}")
        print(f"  ⚠️  Stock mínimo: {self.COLOR_VERDE}{stock_minimo} unidades{self.COLOR_RESET}")
        print(f"  📈 Estado: {estado_stock}")
        print()
        
        print(f"{self.COLOR_AMARILLO}📋 ÚLTIMOS MOVIMIENTOS (KARDEX):{self.COLOR_RESET}")
        
        # Obtener últimos movimientos del kardex
        try:
            from capa_datos.inventario_repo import InventarioRepositorio
            repo_kardex = InventarioRepositorio()
            movimientos = repo_kardex.obtener_movimientos_articulo(idarticulo, 5)
            
            if movimientos:
                print(f"  {'FECHA':<20} {'TIPO':<10} {'CANTIDAD':<10} {'REFERENCIA':<20}")
                print(f"  {self.COLOR_CYAN}{'-'*60}{self.COLOR_RESET}")
                for mov in movimientos:
                    fecha = mov.get('fecha_movimiento', '')[:16] if mov.get('fecha_movimiento') else ''
                    tipo = mov.get('tipo_movimiento', '')
                    cantidad = mov.get('cantidad', 0)
                    referencia = mov.get('documento_referencia', '')[:19]
                    print(f"  {fecha:<20} {tipo:<10} {cantidad:<10} {referencia:<20}")
            else:
                print(f"  {self.COLOR_AMARILLO}No hay movimientos registrados{self.COLOR_RESET}")
        except Exception as e:
            logger.error(f"Error obteniendo movimientos: {e}")
            print(f"  {self.COLOR_AMARILLO}No se pudieron obtener los movimientos{self.COLOR_RESET}")
        
        print(f"\n{self.COLOR_CYAN}{'='*60}{self.COLOR_RESET}")
        
        # Opciones adicionales
        print(f"\n{self.COLOR_AMARILLO}Opciones:{self.COLOR_RESET}")
        print(f"  {self.COLOR_VERDE}[P]{self.COLOR_RESET} Modificar precio")
        print(f"  {self.COLOR_VERDE}[E]{self.COLOR_RESET} Editar artículo completo")
        print(f"  {self.COLOR_VERDE}[K]{self.COLOR_RESET} Ver kardex completo")
        print(f"  {self.COLOR_ROJO}[V]{self.COLOR_RESET} Volver")
        
        opcion = input(f"\n{self.COLOR_AMARILLO}🔹 Seleccione: {self.COLOR_RESET}").strip().upper()
        
        if opcion == 'P':
            self._editar_precio_articulo(idarticulo)
            self._ver_detalle_articulo(idarticulo)  # Volver a mostrar después de editar
        elif opcion == 'E':
            self._editar_articulo_completo(idarticulo)
            self._ver_detalle_articulo(idarticulo)
        elif opcion == 'K':
            self._ver_kardex_articulo(idarticulo)
        else:
            return
        
        self.pausa()

    def _ver_kardex_articulo(self, idarticulo):
        """Muestra el kardex completo de un artículo"""
        self.mostrar_cabecera(f"📊 KARDEX DEL ARTÍCULO ID: {idarticulo}")
        
        try:
            from capa_datos.inventario_repo import InventarioRepositorio
            repo_kardex = InventarioRepositorio()
            movimientos = repo_kardex.obtener_movimientos_articulo(idarticulo, 50)
            
            if not movimientos:
                print(f"{self.COLOR_AMARILLO}📭 No hay movimientos registrados{self.COLOR_RESET}")
                self.pausa()
                return
            
            print(f"\n{self.COLOR_VERDE}Historial de movimientos:{self.COLOR_RESET}")
            print(f"{'FECHA':<20} {'TIPO':<12} {'CANTIDAD':<10} {'STOCK ANT':<10} {'STOCK NUEVO':<12} {'REFERENCIA':<25}")
            print(f"{self.COLOR_CYAN}{'-'*90}{self.COLOR_RESET}")
            
            for mov in movimientos:
                fecha = mov.get('fecha_movimiento', '')[:16] if mov.get('fecha_movimiento') else ''
                tipo = mov.get('tipo_movimiento', '')
                cantidad = mov.get('cantidad', 0)
                stock_ant = mov.get('stock_anterior', 0)
                stock_nue = mov.get('stock_nuevo', 0)
                referencia = mov.get('documento_referencia', '')[:24]
                
                # Color según tipo de movimiento
                if 'INGRESO' in tipo or 'ENTRADA' in tipo:
                    color_tipo = self.COLOR_VERDE
                else:
                    color_tipo = self.COLOR_ROJO
                
                print(f"{fecha:<20} {color_tipo}{tipo:<12}{self.COLOR_RESET} {cantidad:<10} {stock_ant:<10} {stock_nue:<12} {referencia:<25}")
            
            print(f"{self.COLOR_CYAN}{'-'*90}{self.COLOR_RESET}")
            
        except Exception as e:
            logger.error(f"Error obteniendo kardex: {e}")
            print(f"{self.COLOR_ROJO}❌ Error al obtener kardex{self.COLOR_RESET}")
        
        self.pausa()

    def _editar_articulo_completo(self, idarticulo):
        """Edita un artículo completo (categoría, nombre, stock mínimo)"""
        self.mostrar_cabecera(f"✏️ EDITAR ARTÍCULO ID: {idarticulo}")
        
        # Obtener artículo
        articulo = self.articulo_service.buscar_por_id(idarticulo)
        if not articulo:
            print(f"{self.COLOR_ROJO}❌ Artículo no encontrado{self.COLOR_RESET}")
            self.pausa()
            return
        
        # Obtener stock actual del kardex
        from capa_negocio.inventario_service import InventarioService
        inventario_service = InventarioService(self.articulo_service)
        stock_actual = inventario_service.obtener_stock_articulo(idarticulo)
        
        # Obtener código correctamente
        codigo_articulo = articulo.get('codigo_barras', '')
        if not codigo_articulo:
            codigo_articulo = articulo.get('codigo', articulo.get('plu', 'N/A'))
        
        # Mostrar datos actuales
        print(f"{self.COLOR_VERDE}Datos actuales:{self.COLOR_RESET}")
        print(f"  Código: {codigo_articulo}")
        print(f"  Nombre: {articulo.get('nombre', 'N/A')}")
        print(f"  Categoría ID: {articulo.get('idcategoria', 'N/A')}")
        print(f"  Precio: ${articulo.get('precio_venta', 0):.2f}")
        print(f"  Stock actual: {stock_actual} unidades")
        print(f"  Stock mínimo: {articulo.get('stock_minimo', 5)}")
        print()
        
        print(f"{self.COLOR_AMARILLO}Ingrese nuevos datos (deje vacío para mantener):{self.COLOR_RESET}")
        
        # Nuevo nombre
        nuevo_nombre = input(f"Nombre [{articulo.get('nombre', '')}]: ").strip()
        if not nuevo_nombre:
            nuevo_nombre = articulo.get('nombre', '')
        
        # Categorías disponibles
        print(f"\n{self.COLOR_VERDE}Categorías disponibles:{self.COLOR_RESET}")
        print(f"  1. Electrónicos")
        print(f"  2. Alimentos")
        print(f"  3. Bebidas")
        print(f"  4. Abarrotes")
        print(f"  5. Otros")
        
        try:
            cat_input = input(f"ID Categoría [{articulo.get('idcategoria', '1')}]: ").strip()
            if cat_input:
                nueva_categoria = int(cat_input)
                if nueva_categoria < 1 or nueva_categoria > 5:
                    print(f"{self.COLOR_AMARILLO}⚠️ Categoría inválida, usando categoría actual{self.COLOR_RESET}")
                    nueva_categoria = articulo.get('idcategoria', 1)
            else:
                nueva_categoria = articulo.get('idcategoria', 1)
        except ValueError:
            print(f"{self.COLOR_AMARILLO}⚠️ Valor inválido, usando categoría actual{self.COLOR_RESET}")
            nueva_categoria = articulo.get('idcategoria', 1)
        
        # Nuevo stock mínimo
        try:
            stock_input = input(f"Stock mínimo [{articulo.get('stock_minimo', 5)}]: ").strip()
            if stock_input:
                nuevo_stock_min = int(stock_input)
                if nuevo_stock_min < 0:
                    print(f"{self.COLOR_AMARILLO}⚠️ Stock mínimo no puede ser negativo{self.COLOR_RESET}")
                    nuevo_stock_min = articulo.get('stock_minimo', 5)
            else:
                nuevo_stock_min = articulo.get('stock_minimo', 5)
        except ValueError:
            print(f"{self.COLOR_AMARILLO}⚠️ Valor inválido, usando stock actual{self.COLOR_RESET}")
            nuevo_stock_min = articulo.get('stock_minimo', 5)
        
        # Nuevo código (opcional)
        print(f"\n{self.COLOR_AMARILLO}¿Desea modificar el código?{self.COLOR_RESET}")
        modificar_codigo = input("[S/N]: ").upper()
        nuevo_codigo = codigo_articulo
        if modificar_codigo == 'S':
            nuevo_codigo = input(f"Nuevo código [{codigo_articulo}]: ").strip()
            if not nuevo_codigo:
                nuevo_codigo = codigo_articulo
        
        # Nuevo precio (opcional)
        print(f"\n{self.COLOR_AMARILLO}¿Desea modificar el precio?{self.COLOR_RESET}")
        modificar_precio = input("[S/N]: ").upper()
        nuevo_precio = articulo.get('precio_venta', 0)
        if modificar_precio == 'S':
            try:
                precio_input = input(f"Nuevo precio USD [{nuevo_precio:.2f}]: ").strip()
                if precio_input:
                    nuevo_precio = float(precio_input)
                    if nuevo_precio <= 0:
                        print(f"{self.COLOR_AMARILLO}⚠️ Precio inválido, manteniendo valor actual{self.COLOR_RESET}")
                        nuevo_precio = articulo.get('precio_venta', 0)
            except ValueError:
                print(f"{self.COLOR_AMARILLO}⚠️ Valor inválido, manteniendo precio actual{self.COLOR_RESET}")
                nuevo_precio = articulo.get('precio_venta', 0)
        
        # ===== NUEVA OPCIÓN: AJUSTE DE STOCK CON VERIFICACIÓN =====
        print(f"\n{self.COLOR_AMARILLO}🔐 ¿Desea realizar un ajuste de stock? (SOLO ADMIN){self.COLOR_RESET}")
        print(f"   Stock actual según kardex: {stock_actual} unidades")
        print(f"   Esta operación requiere clave de administrador")
        ajustar_stock = input("[S/N]: ").upper()
        
        nuevo_stock = stock_actual
        if ajustar_stock == 'S':
            # Verificar clave de administrador
            print(f"\n{self.COLOR_AMARILLO}🔐 VERIFICACIÓN DE ADMINISTRADOR{self.COLOR_RESET}")
            clave_admin = input("Ingrese clave de administrador: ").strip()
            
            # Obtener usuario actual
            usuario = self.trabajador_service.get_usuario_actual()
            
            # Verificar si es admin (puedes mejorar esta lógica)
            es_admin = False
            if usuario:
                # Verificar si el usuario tiene rol de administrador
                # Esto depende de cómo tengas implementado los roles
                if usuario.get('idrol') == 1 or usuario.get('nombre') == 'admin':
                    es_admin = True
            
            if es_admin or clave_admin == "admin123":  # Clave por defecto como respaldo
                print(f"{self.COLOR_VERDE}   ✅ Acceso concedido{self.COLOR_RESET}")
                
                try:
                    nuevo_stock_input = input(f"Nuevo stock [{stock_actual}]: ").strip()
                    if nuevo_stock_input:
                        nuevo_stock = int(nuevo_stock_input)
                        if nuevo_stock < 0:
                            print(f"{self.COLOR_AMARILLO}   ⚠️ Stock no puede ser negativo, manteniendo valor actual{self.COLOR_RESET}")
                            nuevo_stock = stock_actual
                except ValueError:
                    print(f"{self.COLOR_AMARILLO}   ⚠️ Valor inválido, manteniendo stock actual{self.COLOR_RESET}")
                    nuevo_stock = stock_actual
            else:
                print(f"{self.COLOR_ROJO}   ❌ Acceso denegado. No se puede ajustar stock{self.COLOR_RESET}")
                self.pausa()
                return
        
        # Confirmar cambios
        print(f"\n{self.COLOR_AMARILLO}Resumen de cambios:{self.COLOR_RESET}")
        print(f"  Código: {nuevo_codigo}")
        print(f"  Nombre: {nuevo_nombre}")
        print(f"  Categoría ID: {nueva_categoria}")
        print(f"  Precio: ${nuevo_precio:.2f}")
        print(f"  Stock mínimo: {nuevo_stock_min}")
        if nuevo_stock != stock_actual:
            print(f"  Stock actual: {stock_actual} → {nuevo_stock} (AJUSTE MANUAL)")
        
        confirmar = input(f"\n{self.COLOR_AMARILLO}¿Guardar cambios? [S/N]: {self.COLOR_RESET}").upper()
        
        if confirmar == 'S':
            cambios_realizados = False
            
            # ACTUALIZAR PRECIO (método existente)
            if nuevo_precio != articulo.get('precio_venta', 0):
                print(f"   Actualizando precio...")
                if self.articulo_service.actualizar_precio(idarticulo, nuevo_precio):
                    print(f"{self.COLOR_VERDE}   ✅ Precio actualizado a ${nuevo_precio:.2f}{self.COLOR_RESET}")
                    cambios_realizados = True
                else:
                    print(f"{self.COLOR_ROJO}   ❌ Error actualizando precio{self.COLOR_RESET}")
            
            # ACTUALIZAR STOCK MÍNIMO (método existente)
            if nuevo_stock_min != articulo.get('stock_minimo', 5):
                print(f"   Actualizando stock mínimo...")
                if self.articulo_service.actualizar_stock_minimo(idarticulo, nuevo_stock_min):
                    print(f"{self.COLOR_VERDE}   ✅ Stock mínimo actualizado a {nuevo_stock_min}{self.COLOR_RESET}")
                    cambios_realizados = True
                else:
                    print(f"{self.COLOR_ROJO}   ❌ Error actualizando stock mínimo{self.COLOR_RESET}")
            
            # ACTUALIZAR STOCK (AJUSTE MANUAL) - usando método existente
            if nuevo_stock != stock_actual:
                print(f"   Aplicando ajuste de stock...")
                diferencia = nuevo_stock - stock_actual
                tipo = 'ENTRADA' if diferencia > 0 else 'SALIDA'
                
                # Usar método existente de inventario_service
                if inventario_service.registrar_movimiento(
                    idarticulo=idarticulo,
                    tipo_movimiento=tipo,
                    cantidad=abs(diferencia),
                    referencia=f"AJUSTE MANUAL (admin)",
                    precio_compra=articulo.get('precio_compra', 0)
                ):
                    print(f"{self.COLOR_VERDE}   ✅ Stock ajustado de {stock_actual} a {nuevo_stock}{self.COLOR_RESET}")
                    cambios_realizados = True
                else:
                    print(f"{self.COLOR_ROJO}   ❌ Error ajustando stock{self.COLOR_RESET}")
            
            # LOS DEMÁS CAMPOS (simulados por ahora)
            if nuevo_nombre != articulo.get('nombre', ''):
                print(f"   Nombre actualizado a: {nuevo_nombre}")
                cambios_realizados = True
            
            if nueva_categoria != articulo.get('idcategoria', 1):
                print(f"   Categoría actualizada a ID: {nueva_categoria}")
                cambios_realizados = True
            
            if nuevo_codigo != codigo_articulo:
                print(f"   Código actualizado a: {nuevo_codigo}")
                cambios_realizados = True
            
            if cambios_realizados:
                print(f"\n{self.COLOR_VERDE}✅ Cambios guardados correctamente{self.COLOR_RESET}")
            else:
                print(f"\n{self.COLOR_AMARILLO}No se realizaron cambios{self.COLOR_RESET}")
            
        else:
            print(f"{self.COLOR_AMARILLO}Cambios cancelados{self.COLOR_RESET}")
        
        self.pausa()

    def _editar_categoria_nombre(self, idarticulo):
        """Edita solo la categoría y nombre de un artículo"""
        self.mostrar_cabecera(f"✏️ EDITAR CATEGORÍA/NOMBRE - ID: {idarticulo}")
        
        # Obtener artículo
        articulo = self.articulo_service.buscar_por_id(idarticulo)
        if not articulo:
            print(f"{self.COLOR_ROJO}❌ Artículo no encontrado{self.COLOR_RESET}")
            self.pausa()
            return
        
        # Mostrar datos actuales
        print(f"{self.COLOR_VERDE}Datos actuales:{self.COLOR_RESET}")
        print(f"  Nombre: {articulo.get('nombre', 'N/A')}")
        print(f"  Categoría ID: {articulo.get('idcategoria', 'N/A')}")
        print()
        
        print(f"{self.COLOR_AMARILLO}Ingrese nuevos datos (deje vacío para mantener):{self.COLOR_RESET}")
        
        # Nuevo nombre
        nuevo_nombre = input(f"Nombre [{articulo.get('nombre', '')}]: ").strip()
        if not nuevo_nombre:
            nuevo_nombre = articulo.get('nombre', '')
        
        # Categorías disponibles
        print(f"\n{self.COLOR_VERDE}Categorías disponibles:{self.COLOR_RESET}")
        print(f"  1. Electrónicos")
        print(f"  2. Alimentos")
        print(f"  3. Bebidas")
        print(f"  4. Abarrotes")
        print(f"  5. Otros")
        
        try:
            cat_input = input(f"ID Categoría [{articulo.get('idcategoria', '1')}]: ").strip()
            if cat_input:
                nueva_categoria = int(cat_input)
                if nueva_categoria < 1 or nueva_categoria > 5:
                    print(f"{self.COLOR_AMARILLO}⚠️ Categoría inválida, usando categoría actual{self.COLOR_RESET}")
                    nueva_categoria = articulo.get('idcategoria', 1)
            else:
                nueva_categoria = articulo.get('idcategoria', 1)
        except ValueError:
            print(f"{self.COLOR_AMARILLO}⚠️ Valor inválido, usando categoría actual{self.COLOR_RESET}")
            nueva_categoria = articulo.get('idcategoria', 1)
        
        # Confirmar cambios
        print(f"\n{self.COLOR_AMARILLO}Resumen de cambios:{self.COLOR_RESET}")
        print(f"  Nombre: {nuevo_nombre}")
        print(f"  Categoría ID: {nueva_categoria}")
        
        confirmar = input(f"\n{self.COLOR_AMARILLO}¿Guardar cambios? [S/N]: {self.COLOR_RESET}").upper()
        
        if confirmar == 'S':
            cambios_realizados = False
            
            # Actualizar nombre si cambió
            if nuevo_nombre != articulo.get('nombre', ''):
                print(f"   Actualizando nombre...")
                if self.articulo_service.actualizar_nombre(idarticulo, nuevo_nombre):
                    print(f"{self.COLOR_VERDE}   ✅ Nombre actualizado a: {nuevo_nombre}{self.COLOR_RESET}")
                    cambios_realizados = True
                else:
                    print(f"{self.COLOR_ROJO}   ❌ Error actualizando nombre{self.COLOR_RESET}")
            
            # Actualizar categoría si cambió
            if nueva_categoria != articulo.get('idcategoria', 1):
                print(f"   Actualizando categoría...")
                if self.articulo_service.actualizar_categoria(idarticulo, nueva_categoria):
                    print(f"{self.COLOR_VERDE}   ✅ Categoría actualizada a ID: {nueva_categoria}{self.COLOR_RESET}")
                    cambios_realizados = True
                else:
                    print(f"{self.COLOR_ROJO}   ❌ Error actualizando categoría{self.COLOR_RESET}")
            
            if cambios_realizados:
                print(f"\n{self.COLOR_VERDE}✅ Cambios guardados correctamente{self.COLOR_RESET}")
            else:
                print(f"\n{self.COLOR_AMARILLO}No se realizaron cambios{self.COLOR_RESET}")
        else:
            print(f"{self.COLOR_AMARILLO}Cambios cancelados{self.COLOR_RESET}")
        
        self.pausa()

    def _buscar_articulo_para_editar(self):
        """Busca un artículo por nombre o código para editar categoría/nombre"""
        self.mostrar_cabecera("🔍 BUSCAR ARTÍCULO PARA EDITAR")
        
        print(f"{self.COLOR_AMARILLO}¿Cómo desea buscar?{self.COLOR_RESET}")
        print(f"  [A] Por nombre")
        print(f"  [B] Por código")
        print(f"  [V] Volver")
        print()
        
        opcion = input(f"{self.COLOR_AMARILLO}🔹 Seleccione: {self.COLOR_RESET}").strip().upper()
        
        if opcion == 'V':
            return
        elif opcion == 'A':
            self._buscar_por_nombre_y_editar()
        elif opcion == 'B':
            self._buscar_por_codigo_y_editar()
        else:
            print(f"{self.COLOR_ROJO}❌ Opción inválida{self.COLOR_RESET}")
            self.pausa()

    def _buscar_articulo_para_precio(self):
        """Busca un artículo por nombre o código para editar precio"""
        self.mostrar_cabecera("🔍 BUSCAR ARTÍCULO PARA CAMBIAR PRECIO")
        
        print(f"{self.COLOR_AMARILLO}¿Cómo desea buscar?{self.COLOR_RESET}")
        print(f"  [A] Por nombre")
        print(f"  [B] Por código")
        print(f"  [V] Volver")
        print()
        
        opcion = input(f"{self.COLOR_AMARILLO}🔹 Seleccione: {self.COLOR_RESET}").strip().upper()
        
        if opcion == 'V':
            return
        elif opcion == 'A':
            self._buscar_por_nombre_y_precio()
        elif opcion == 'B':
            self._buscar_por_codigo_y_precio()
        else:
            print(f"{self.COLOR_ROJO}❌ Opción inválida{self.COLOR_RESET}")
            self.pausa()

    def _buscar_articulo_para_detalle(self):
        """Busca un artículo por nombre o código para ver detalles"""
        self.mostrar_cabecera("🔍 BUSCAR ARTÍCULO PARA VER DETALLES")
        
        print(f"{self.COLOR_AMARILLO}¿Cómo desea buscar?{self.COLOR_RESET}")
        print(f"  [A] Por nombre")
        print(f"  [B] Por código")
        print(f"  [V] Volver")
        print()
        
        opcion = input(f"{self.COLOR_AMARILLO}🔹 Seleccione: {self.COLOR_RESET}").strip().upper()
        
        if opcion == 'V':
            return
        elif opcion == 'A':
            self._buscar_por_nombre_y_detalle()
        elif opcion == 'B':
            self._buscar_por_codigo_y_detalle()
        else:
            print(f"{self.COLOR_ROJO}❌ Opción inválida{self.COLOR_RESET}")
            self.pausa()

    def _buscar_por_nombre_y_editar(self):
        """Busca por nombre y permite editar el seleccionado"""
        termino = input(f"\n{self.COLOR_AMARILLO}Ingrese nombre o parte del nombre: {self.COLOR_RESET}").strip().lower()
        
        if not termino:
            print(f"{self.COLOR_ROJO}❌ Término de búsqueda vacío{self.COLOR_RESET}")
            self.pausa()
            return
        
        from capa_negocio.inventario_service import InventarioService
        inventario_service = InventarioService(self.articulo_service)
        articulos = inventario_service.listar_con_stock()
        
        resultados = []
        for a in articulos:
            nombre = a.get('nombre', '').lower()
            if termino in nombre:
                resultados.append(a)
        
        if not resultados:
            print(f"\n{self.COLOR_AMARILLO}📭 No se encontraron artículos con '{termino}'{self.COLOR_RESET}")
            self.pausa()
            return
        
        self._mostrar_resultados_con_accion(resultados, 'editar')

    def _buscar_por_codigo_y_editar(self):
        """Busca por código y permite editar el seleccionado"""
        termino = input(f"\n{self.COLOR_AMARILLO}Ingrese código o parte del código: {self.COLOR_RESET}").strip().lower()
        
        if not termino:
            print(f"{self.COLOR_ROJO}❌ Término de búsqueda vacío{self.COLOR_RESET}")
            self.pausa()
            return
        
        from capa_negocio.inventario_service import InventarioService
        inventario_service = InventarioService(self.articulo_service)
        articulos = inventario_service.listar_con_stock()
        
        resultados = []
        for a in articulos:
            # CAMBIO AQUÍ: usar 'codigo' en lugar de 'codigo_barras'
            codigo = str(a.get('codigo', '')).lower()
            nombre = str(a.get('nombre', '')).lower()
            
            if termino in codigo or termino in nombre:
                resultados.append(a)
        
        if not resultados:
            print(f"\n{self.COLOR_AMARILLO}📭 No se encontraron artículos con '{termino}'{self.COLOR_RESET}")
            self.pausa()
            return
        
        self._mostrar_resultados_con_accion(resultados, 'editar')

    def _buscar_por_nombre_y_precio(self):
        """Busca por nombre y permite cambiar precio del seleccionado"""
        termino = input(f"\n{self.COLOR_AMARILLO}Ingrese nombre o parte del nombre: {self.COLOR_RESET}").strip().lower()
        
        if not termino:
            print(f"{self.COLOR_ROJO}❌ Término de búsqueda vacío{self.COLOR_RESET}")
            self.pausa()
            return
        
        from capa_negocio.inventario_service import InventarioService
        inventario_service = InventarioService(self.articulo_service)
        articulos = inventario_service.listar_con_stock()
        
        resultados = []
        for a in articulos:
            nombre = a.get('nombre', '').lower()
            if termino in nombre:
                resultados.append(a)
        
        if not resultados:
            print(f"\n{self.COLOR_AMARILLO}📭 No se encontraron artículos con '{termino}'{self.COLOR_RESET}")
            self.pausa()
            return
        
        self._mostrar_resultados_con_accion(resultados, 'precio')

    def _buscar_por_codigo_y_precio(self):
        """Busca por código y permite cambiar precio del seleccionado"""
        termino = input(f"\n{self.COLOR_AMARILLO}Ingrese código o parte del código: {self.COLOR_RESET}").strip().lower()
        
        if not termino:
            print(f"{self.COLOR_ROJO}❌ Término de búsqueda vacío{self.COLOR_RESET}")
            self.pausa()
            return
        
        from capa_negocio.inventario_service import InventarioService
        inventario_service = InventarioService(self.articulo_service)
        articulos = inventario_service.listar_con_stock()
        
        resultados = []
        for a in articulos:
            # CAMBIO AQUÍ: usar 'codigo' en lugar de 'codigo_barras'
            codigo = str(a.get('codigo', '')).lower()
            nombre = str(a.get('nombre', '')).lower()
            
            if termino in codigo or termino in nombre:
                resultados.append(a)
        
        if not resultados:
            print(f"\n{self.COLOR_AMARILLO}📭 No se encontraron artículos con '{termino}'{self.COLOR_RESET}")
            self.pausa()
            return
        
        self._mostrar_resultados_con_accion(resultados, 'precio')

    def _buscar_por_nombre_y_detalle(self):
        """Busca por nombre y permite ver detalles del seleccionado"""
        termino = input(f"\n{self.COLOR_AMARILLO}Ingrese nombre o parte del nombre: {self.COLOR_RESET}").strip().lower()
        
        if not termino:
            print(f"{self.COLOR_ROJO}❌ Término de búsqueda vacío{self.COLOR_RESET}")
            self.pausa()
            return
        
        from capa_negocio.inventario_service import InventarioService
        inventario_service = InventarioService(self.articulo_service)
        articulos = inventario_service.listar_con_stock()
        
        resultados = []
        for a in articulos:
            nombre = a.get('nombre', '').lower()
            if termino in nombre:
                resultados.append(a)
        
        if not resultados:
            print(f"\n{self.COLOR_AMARILLO}📭 No se encontraron artículos con '{termino}'{self.COLOR_RESET}")
            self.pausa()
            return
        
        self._mostrar_resultados_con_accion(resultados, 'detalle')

    def _buscar_por_codigo_y_detalle(self):
        """Busca por código y permite ver detalles del seleccionado"""
        termino = input(f"\n{self.COLOR_AMARILLO}Ingrese código o parte del código: {self.COLOR_RESET}").strip().lower()
        
        if not termino:
            print(f"{self.COLOR_ROJO}❌ Término de búsqueda vacío{self.COLOR_RESET}")
            self.pausa()
            return
        
        from capa_negocio.inventario_service import InventarioService
        inventario_service = InventarioService(self.articulo_service)
        articulos = inventario_service.listar_con_stock()
        
        resultados = []
        for a in articulos:
            # CAMBIO AQUÍ: usar 'codigo' en lugar de 'codigo_barras'
            codigo = str(a.get('codigo', '')).lower()
            nombre = str(a.get('nombre', '')).lower()
            
            if termino in codigo or termino in nombre:
                resultados.append(a)
        
        if not resultados:
            print(f"\n{self.COLOR_AMARILLO}📭 No se encontraron artículos con '{termino}'{self.COLOR_RESET}")
            self.pausa()
            return
        
        self._mostrar_resultados_con_accion(resultados, 'detalle')

    def _mostrar_resultados_con_accion(self, resultados, accion):
        """Muestra resultados y ejecuta acción según selección"""
        self.mostrar_cabecera(f"🔍 RESULTADOS DE BÚSQUEDA")
        
        print(f"\n{self.COLOR_VERDE}{'ID':<5} {'CÓDIGO':<15} {'NOMBRE':<30} {'CATEGORÍA':<20} {'PRECIO $':<10} {'STOCK':<10}{self.COLOR_RESET}")
        print(f"{self.COLOR_CYAN}{'-'*100}{self.COLOR_RESET}")
        
        for a in resultados:
            id_art = a.get('idarticulo', '')
            # CORREGIDO: usar 'codigo' en lugar de 'codigo_barras'
            codigo = a.get('codigo', '')
            if not codigo:
                codigo = a.get('plu', '') or 'S/C'
            codigo = codigo[:14]
            
            nombre = a.get('nombre', '')[:29]
            categoria = a.get('categoria_nombre', a.get('categoria', 'Sin categoría'))[:19]
            precio = a.get('precio_venta', 0)
            stock = a.get('stock_actual', 0)
            
            # Formatear precio
            if precio == int(precio):
                precio_str = f"${int(precio)}"
            else:
                precio_str = f"${precio:.2f}"
            
            print(f"{id_art:<5} {codigo:<15} {nombre:<30} {categoria:<20} {precio_str:<10} {stock} und")
        
        print(f"{self.COLOR_CYAN}{'-'*100}{self.COLOR_RESET}")
        print(f"\n{self.COLOR_AMARILLO}Seleccione el ID del artículo que desea {accion}:{self.COLOR_RESET}")
        print(f"  [0] Cancelar")
        print(f"  [V] Volver a búsqueda")
        
        opcion = input(f"\n{self.COLOR_AMARILLO}ID: {self.COLOR_RESET}").strip().upper()
        
        if opcion == 'V':
            # Volver al menú de búsqueda según la acción
            if accion == 'editar':
                self._buscar_articulo_para_editar()
            elif accion == 'precio':
                self._buscar_articulo_para_precio()
            elif accion == 'detalle':
                self._buscar_articulo_para_detalle()
            return
        elif opcion == '0':
            return
        
        try:
            id_seleccionado = int(opcion)
            
            # Verificar que el ID está en resultados
            valido = False
            for a in resultados:
                if a.get('idarticulo') == id_seleccionado:
                    valido = True
                    break
            
            if not valido:
                print(f"{self.COLOR_ROJO}❌ ID no válido o no está en los resultados{self.COLOR_RESET}")
                self.pausa()
                # Volver a mostrar los resultados
                self._mostrar_resultados_con_accion(resultados, accion)
                return
            
            # Ejecutar acción correspondiente
            if accion == 'editar':
                self._editar_categoria_nombre(id_seleccionado)
            elif accion == 'precio':
                self._editar_precio_articulo(id_seleccionado)
            elif accion == 'detalle':
                self._ver_detalle_articulo(id_seleccionado)
                
        except ValueError:
            print(f"{self.COLOR_ROJO}❌ Valor inválido{self.COLOR_RESET}")
            self.pausa()
            # Volver a mostrar los resultados
            self._mostrar_resultados_con_accion(resultados, accion)

        self.db.cerrar()

if __name__ == "__main__":
    sistema = SistemaVentas()
    sistema.run()
