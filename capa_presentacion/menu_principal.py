#!/usr/bin/env python3
"""
Menú principal del sistema de ventas (Interfaz de consola)
"""
import os
import sys
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

from capa_presentacion.decoradores import requiere_permiso

from loguru import logger

# Configurar logger
logger.remove()
logger.add(sys.stderr, format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

class SistemaVentas:
    """Clase principal del sistema"""
    
    def __init__(self):
        self.db = ConexionDB()
        self.conn = None
        self.trabajador_service = None
        self.categoria_service = None
        self.cliente_service = None
        self.articulo_service = None
        self.venta_service = None
        self.rol_service = None
        self.email_service = None
        self.usuario_admin_service = None
        self.token_service = None
    
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
        venta_repo = VentaRepositorio(self.conn)
        rol_repo = RolRepositorio(self.conn)
        usuario_admin_repo = UsuarioAdminRepositorio(self.conn)
        
        # Inicializar servicios
        self.trabajador_service = TrabajadorService(trabajador_repo)
        self.categoria_service = CategoriaService(categoria_repo)
        self.cliente_service = ClienteService(cliente_repo)
        self.articulo_service = ArticuloService(articulo_repo, self.categoria_service)
        self.venta_service = VentaService(
            venta_repo, 
            self.cliente_service, 
            self.trabajador_service, 
            self.articulo_service
        )
        self.rol_service = RolService(rol_repo)
        self.usuario_admin_service = UsuarioAdminService(usuario_admin_repo, self.rol_service)
        self.token_service = TokenService(self.conn)
        
        # Asignar rol_service a trabajador_service
        self.trabajador_service.rol_service = self.rol_service
        
        # Inicializar servicio de email
        self.email_service = EmailService(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            email_remitente="carlosberenguel554@gmail.com",  # ← CAMBIA ESTO
            password="fhnh tiax mfus fmok"  # ← CAMBIA ESTO
        )
        
        return True
    
    def limpiar_pantalla(self):
        """Limpia la pantalla de la consola"""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def pausa(self):
        """Pausa la ejecución hasta que el usuario presione Enter"""
        input("\n🔹 Presione Enter para continuar...")
    
    def mostrar_cabecera(self, titulo):
        """Muestra una cabecera formateada"""
        self.limpiar_pantalla()
        print("=" * 60)
        print(f"{titulo:^60}")
        print("=" * 60)
        print()
    
    def mostrar_menu_principal(self):
        """Muestra el menú principal con opciones según permisos"""
        self.mostrar_cabecera("SISTEMA DE VENTAS - 3 CAPAS")
        
        usuario = self.trabajador_service.get_usuario_actual()
        if usuario:
            # Mostrar información del usuario y su rol
            rol_nombre = "Sin rol"
            if usuario.get('idrol'):
                rol = self.rol_service.repositorio.obtener_rol(usuario['idrol'])
                if rol:
                    rol_nombre = rol['nombre']
            
            print(f"👤 Usuario: {usuario['nombre']} {usuario['apellidos']} [{rol_nombre}]")
            print(f"🔑 Permisos: {len(self.rol_service.get_permisos_usuario())} activos")
            print()
        
        # Opciones visibles según permisos
        opciones = []
        
        if not usuario or self.rol_service.tiene_permiso('clientes_ver'):
            opciones.append(("1", "Gestión de Clientes"))
        if not usuario or self.rol_service.tiene_permiso('articulos_ver'):
            opciones.append(("2", "Gestión de Artículos"))
        if not usuario or self.rol_service.tiene_permiso('proveedores_ver'):
            opciones.append(("3", "Gestión de Proveedores"))
        if not usuario or self.rol_service.tiene_permiso('ventas_ver'):
            opciones.append(("4", "Gestión de Ventas"))
        if not usuario or self.rol_service.tiene_permiso('inventario_ver'):
            opciones.append(("5", "Gestión de Inventario"))
        if not usuario or self.rol_service.tiene_permiso('reportes_ventas'):
            opciones.append(("6", "Reportes"))
        if usuario and self.rol_service.tiene_permiso('usuarios_ver'):
            opciones.append(("7", "Administración de Usuarios"))
        
        for num, desc in opciones:
            print(f"{num}. {desc}")
        
        print("8. Cerrar Sesión" if usuario else "8. Iniciar Sesión")
        print("0. Salir")
        print()
        
        return input("🔹 Seleccione una opción: ").strip()
    
    def menu_login(self):
        """Menú de inicio de sesión con opción de recuperación"""
        while True:
            self.mostrar_cabecera("INICIAR SESIÓN")
            
            print("1. Iniciar sesión")
            print("2. ¿Olvidaste tu contraseña?")
            print("0. Volver")
            print()
            
            opcion = input("🔹 Seleccione una opción: ").strip()
            
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
            print("✅ Sesión iniciada correctamente")
        else:
            print("❌ Email o contraseña incorrectos")
        
        self.pausa()
    
    def _recuperar_contraseña(self):
        """Proceso de recuperación con enlace mágico"""
        while True:
            self.mostrar_cabecera("RECUPERAR CONTRASEÑA")
            
            print("1. Solicitar enlace mágico por email")
            print("2. Ya tengo un token, ingresar manualmente")
            print("0. Volver")
            print()
            
            opcion = input("🔹 Seleccione una opción: ").strip()
            
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
        
        # Buscar usuario por email
        usuario = self.trabajador_service.buscar_por_email(email)
        
        if not usuario:
            print("❌ No existe un usuario con ese email")
            self.pausa()
            return
        
        print(f"\n👤 Usuario encontrado: {usuario['nombre']} {usuario['apellidos']}")
        print(f"📧 Email: {usuario['email']}")
        print()
        
        # Generar token
        token = self.token_service.crear_token(usuario['idtrabajador'])
        
        if token:
            # Enviar por correo
            if self.email_service.enviar_enlace_magico(
                email, token, usuario['nombre']
            ):
                print(f"✅ Se ha enviado un enlace mágico a:")
                print(f"   {email}")
                print(f"\n📧 Revisa tu bandeja de entrada (y carpeta SPAM)")
                print(f"⏰ El enlace expirará en 30 minutos")
                print(f"\n📝 Si no recibes el correo, usa la opción 2 para ingresar manualmente:")
                print(f"   Token: {token}")
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
        
        # Verificar token
        idtrabajador = self.token_service.verificar_token(token)
        
        if idtrabajador:
            usuario = self.trabajador_service.obtener_por_id(idtrabajador)
            print(f"\n✅ Token válido para: {usuario['nombre']} {usuario['apellidos']}")
            
            # Solicitar nueva contraseña (con mensajes claros)
            print("\n" + "="*50)
            print("🔑 CAMBIO DE CONTRASEÑA")
            print("="*50)
            print()
            
            # Desactivar logger temporalmente para evitar interferencias
            logger.remove()
            logger.add(lambda msg: None)  # Logger silencioso
            
            try:
                nueva_pass = input("➤ Ingrese NUEVA contraseña (mínimo 6 caracteres): ")
                confirmar = input("➤ Confirme la NUEVA contraseña: ")
            finally:
                # Restaurar logger
                logger.remove()
                logger.add(sys.stderr, format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
            
            if nueva_pass == confirmar and len(nueva_pass) >= 6:
                if self.trabajador_service.actualizar_password(usuario['email'], nueva_pass):
                    # Marcar token como usado
                    self.token_service.marcar_token_usado(token)
                    print("\n✅ Contraseña actualizada correctamente")
                    print("🔐 Ya puede iniciar sesión con su nueva contraseña")
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
            
            opcion = input("🔹 Seleccione una opción: ").strip()
            
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
                print(f"{u['idtrabajador']:<5} {u['usuario']:<15} {u['nombre'] + ' ' + u['apellidos']:<25} {u['email']:<30} {rol:<15}")
        
        self.pausa()
    
    def _crear_usuario(self):
        """Crea un nuevo usuario"""
        self.mostrar_cabecera("CREAR NUEVO USUARIO")
        
        print("📝 Complete los datos del nuevo usuario:")
        print()
        
        nombre = input("Nombre: ")
        apellidos = input("Apellidos: ")
        sexo = input("Sexo (M/F/O): ").upper()
        fecha_nac = input("Fecha de nacimiento (YYYY-MM-DD): ")
        num_doc = input("Número de documento: ")
        usuario = input("Nombre de usuario: ")
        password = input("Contraseña (mínimo 6 caracteres): ")
        email = input("Email: ")
        telefono = input("Teléfono (opcional): ") or None
        direccion = input("Dirección (opcional): ") or None
        
        # Mostrar roles disponibles
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
        
        if self.usuario_admin_service.crear_usuario(
            nombre, apellidos, sexo, fecha_nac, num_doc,
            usuario, password, email, idrol, direccion, telefono
        ):
            print("✅ Usuario creado exitosamente")
        else:
            print("❌ Error al crear el usuario")
        
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
                print(f"📌 Fecha Nac.: {usuario['fecha_nacimiento']}")
                print(f"📌 Documento: {usuario['num_documento']}")
                print(f"📌 Usuario: {usuario['usuario']}")
                print(f"📌 Email: {usuario['email']}")
                print(f"📌 Teléfono: {usuario.get('telefono', 'No registrado')}")
                print(f"📌 Dirección: {usuario.get('direccion', 'No registrada')}")
                print(f"📌 Rol: {usuario.get('rol_nombre')} (ID: {usuario['idrol']})")
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
            
            print(f"\nEditando a: {usuario['nombre']} {usuario['apellidos']}")
            print("(Deje en blanco para mantener el valor actual)")
            print()
            
            nombre = input(f"Nombre [{usuario['nombre']}]: ") or usuario['nombre']
            apellidos = input(f"Apellidos [{usuario['apellidos']}]: ") or usuario['apellidos']
            sexo = input(f"Sexo [{usuario['sexo']}]: ").upper() or usuario['sexo']
            fecha_nac = input(f"Fecha Nac. [{usuario['fecha_nacimiento']}]: ") or usuario['fecha_nacimiento']
            num_doc = input(f"Documento [{usuario['num_documento']}]: ") or usuario['num_documento']
            username = input(f"Usuario [{usuario['usuario']}]: ") or usuario['usuario']
            email = input(f"Email [{usuario['email']}]: ") or usuario['email']
            telefono = input(f"Teléfono [{usuario.get('telefono', '')}]: ") or usuario.get('telefono')
            direccion = input(f"Dirección [{usuario.get('direccion', '')}]: ") or usuario.get('direccion')
            
            # Cambiar contraseña?
            cambiar_pass = input("¿Cambiar contraseña? (s/N): ").lower()
            nueva_pass = None
            if cambiar_pass == 's':
                nueva_pass = input("Nueva contraseña: ")
                confirmar = input("Confirmar contraseña: ")
                if nueva_pass != confirmar:
                    print("❌ Las contraseñas no coinciden")
                    self.pausa()
                    return
            
            # Mostrar roles disponibles
            print("\nRoles disponibles:")
            roles = self.rol_service.listar_roles()
            for r in roles:
                print(f"  {r['idrol']}. {r['nombre']}")
            
            try:
                idrol = int(input(f"\nID del rol [{usuario['idrol']}]: ") or usuario['idrol'])
            except:
                idrol = usuario['idrol']
            
            if self.usuario_admin_service.actualizar_usuario(
                iduser, nombre, apellidos, sexo, fecha_nac, num_doc,
                username, email, idrol, direccion, telefono, nueva_pass
            ):
                print("✅ Usuario actualizado correctamente")
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
            
            # No permitir eliminarse a sí mismo
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
            
            print(f"\n¿Está seguro de eliminar a {usuario['nombre']} {usuario['apellidos']}?")
            confirmacion = input("Esta acción no se puede deshacer (escriba 'ELIMINAR' para confirmar): ")
            
            if confirmacion == 'ELIMINAR':
                if self.usuario_admin_service.eliminar_usuario(iduser):
                    print("✅ Usuario eliminado correctamente")
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
            
            opcion = input("🔹 Seleccione una opción: ").strip()
            
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
            
            print(f"\n📌 Datos actuales:")
            print(f"   Nombre: {categoria['nombre']}")
            print(f"   Descripción: {categoria['descripcion'] or 'Sin descripción'}")
            print()
            
            nombre = input("Nuevo nombre (Enter para mantener): ") or categoria['nombre']
            descripcion = input("Nueva descripción (Enter para mantener): ") or categoria['descripcion']
            
            if self.categoria_service.actualizar(idcategoria, nombre, descripcion):
                print("✅ Categoría actualizada exitosamente")
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
            
            confirmacion = input(f"¿Está seguro de eliminar la categoría {idcategoria}? (s/N): ")
            if confirmacion.lower() == 's':
                if self.categoria_service.eliminar(idcategoria):
                    print("✅ Categoría eliminada exitosamente")
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
            
            opcion = input("🔹 Seleccione una opción: ").strip()
            
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
            print(f"{'ID':<5} {'NOMBRE':<25} {'DOCUMENTO':<15} {'TELÉFONO':<12} {'EMAIL':<25}")
            print("-" * 82)
            for c in clientes:
                nombre_completo = f"{c['nombre']} {c['apellidos']}"
                print(f"{c['idcliente']:<5} {nombre_completo:<25} {c['num_documento']:<15} {c.get('telefono', ''):<12} {c.get('email', ''):<25}")
        
        self.pausa()
    
    @requiere_permiso('clientes_crear')
    def _crear_cliente(self):
        """Crea un nuevo cliente"""
        self.mostrar_cabecera("CREAR CLIENTE")
        
        print("📝 Complete los datos del cliente:")
        print()
        
        nombre = input("Nombre: ")
        apellidos = input("Apellidos: ")
        sexo = input("Sexo (M/F/O): ").upper()
        fecha_nac = input("Fecha de nacimiento (YYYY-MM-DD): ")
        tipo_doc = input("Tipo de documento (DNI/RUC/PASAPORTE): ").upper()
        num_doc = input("Número de documento: ")
        direccion = input("Dirección (opcional): ") or None
        telefono = input("Teléfono (opcional): ") or None
        email = input("Email (opcional): ") or None
        
        if self.cliente_service.crear(
            nombre, apellidos, fecha_nac, tipo_doc, num_doc,
            sexo, direccion, telefono, email
        ):
            print("✅ Cliente creado exitosamente")
        else:
            print("❌ Error al crear el cliente")
        
        self.pausa()
    
    @requiere_permiso('clientes_ver')
    def _buscar_cliente(self):
        """Busca un cliente por ID o documento"""
        self.mostrar_cabecera("BUSCAR CLIENTE")
        
        print("1. Buscar por ID")
        print("2. Buscar por documento")
        opcion = input("🔹 Seleccione: ").strip()
        
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
            doc = input("Número de documento: ")
            cliente = self.cliente_service.buscar_por_documento(doc)
            if cliente:
                # Obtener datos completos
                cliente = self.cliente_service.obtener_por_id(cliente['idcliente'])
                self._mostrar_detalle_cliente(cliente)
            else:
                print(f"❌ No existe cliente con documento {doc}")
        
        self.pausa()
    
    def _mostrar_detalle_cliente(self, c):
        """Muestra detalles completos de un cliente"""
        print(f"\n📌 ID: {c['idcliente']}")
        print(f"📌 Nombre: {c['nombre']} {c['apellidos']}")
        print(f"📌 Sexo: {c.get('sexo', 'No especificado')}")
        print(f"📌 Fecha Nac.: {c['fecha_nacimiento']}")
        print(f"📌 Documento: {c['tipo_documento']} - {c['num_documento']}")
        print(f"📌 Dirección: {c.get('direccion', 'No registrada')}")
        print(f"📌 Teléfono: {c.get('telefono', 'No registrado')}")
        print(f"📌 Email: {c.get('email', 'No registrado')}")
    
    @requiere_permiso('clientes_editar')
    def _editar_cliente(self):
        """Edita un cliente existente"""
        self.mostrar_cabecera("EDITAR CLIENTE")
        
        try:
            idcliente = int(input("ID del cliente a editar: "))
            cliente = self.cliente_service.obtener_por_id(idcliente)
            
            if not cliente:
                print(f"❌ No existe cliente con ID {idcliente}")
                self.pausa()
                return
            
            print(f"\nEditando a: {cliente['nombre']} {cliente['apellidos']}")
            print("(Deje en blanco para mantener el valor actual)")
            print()
            
            nombre = input(f"Nombre [{cliente['nombre']}]: ") or cliente['nombre']
            apellidos = input(f"Apellidos [{cliente['apellidos']}]: ") or cliente['apellidos']
            sexo = input(f"Sexo [{cliente['sexo']}]: ").upper() or cliente['sexo']
            fecha_nac = input(f"Fecha Nac. [{cliente['fecha_nacimiento']}]: ") or cliente['fecha_nacimiento']
            tipo_doc = input(f"Tipo documento [{cliente['tipo_documento']}]: ").upper() or cliente['tipo_documento']
            num_doc = input(f"Número documento [{cliente['num_documento']}]: ") or cliente['num_documento']
            direccion = input(f"Dirección [{cliente.get('direccion', '')}]: ") or cliente.get('direccion')
            telefono = input(f"Teléfono [{cliente.get('telefono', '')}]: ") or cliente.get('telefono')
            email = input(f"Email [{cliente.get('email', '')}]: ") or cliente.get('email')
            
            if self.cliente_service.actualizar(
                idcliente, nombre, apellidos, fecha_nac, tipo_doc, num_doc,
                sexo, direccion, telefono, email
            ):
                print("✅ Cliente actualizado correctamente")
            else:
                print("❌ Error al actualizar el cliente")
        
        except Exception as e:
            print(f"❌ Error: {e}")
        
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
            
            print(f"\n¿Está seguro de eliminar a {cliente['nombre']} {cliente['apellidos']}?")
            confirmacion = input("Esta acción no se puede deshacer (escriba 'ELIMINAR' para confirmar): ")
            
            if confirmacion == 'ELIMINAR':
                if self.cliente_service.eliminar(idcliente):
                    print("✅ Cliente eliminado correctamente")
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
            print("2. Buscar artículo")
            print("3. Crear artículo")
            print("4. Editar artículo")
            print("5. Eliminar artículo")
            print("6. Ver stock por lote")
            print("0. Volver")
            print()
            
            opcion = input("🔹 Seleccione una opción: ").strip()
            
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
            elif opcion == '0':
                break
            else:
                print("❌ Opción no válida")
                self.pausa()
    
    @requiere_permiso('articulos_ver')
    def _listar_articulos(self):
        """Lista todos los artículos"""
        self.mostrar_cabecera("LISTADO DE ARTÍCULOS")
        
        articulos = self.articulo_service.listar()
        
        if not articulos:
            print("📭 No hay artículos registrados")
        else:
            print(f"{'ID':<5} {'CÓDIGO':<15} {'NOMBRE':<30} {'CATEGORÍA':<20} {'PRESENTACIÓN':<15}")
            print("-" * 85)
            for a in articulos:
                print(f"{a['idarticulo']:<5} {a['codigo']:<15} {a['nombre']:<30} {a['categoria']:<20} {a['presentacion']:<15}")
        
        self.pausa()
    
    @requiere_permiso('articulos_crear')
    def _crear_articulo(self):
        """Crea un nuevo artículo"""
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
        
        if self.articulo_service.crear(codigo, nombre, idcat, idpres, descripcion):
            print("✅ Artículo creado exitosamente")
        else:
            print("❌ Error al crear el artículo")
        
        self.pausa()
    
    @requiere_permiso('articulos_ver')
    def _buscar_articulo(self):
        """Busca un artículo por ID o código"""
        self.mostrar_cabecera("BUSCAR ARTÍCULO")
        
        print("1. Buscar por ID")
        print("2. Buscar por código")
        opcion = input("🔹 Seleccione: ").strip()
        
        if opcion == '1':
            try:
                idart = int(input("ID del artículo: "))
                art = self.articulo_service.obtener_por_id(idart)
                if art:
                    self._mostrar_detalle_articulo(art)
                else:
                    print(f"❌ No existe artículo con ID {idart}")
            except:
                print("❌ ID inválido")
        
        elif opcion == '2':
            codigo = input("Código del artículo: ")
            art = self.articulo_service.buscar_por_codigo(codigo)
            if art:
                # Obtener datos completos
                art = self.articulo_service.obtener_por_id(art['idarticulo'])
                self._mostrar_detalle_articulo(art)
            else:
                print(f"❌ No existe artículo con código {codigo}")
        
        self.pausa()
    
    def _mostrar_detalle_articulo(self, a):
        """Muestra detalles completos de un artículo"""
        print(f"\n📌 ID: {a['idarticulo']}")
        print(f"📌 Código: {a['codigo']}")
        print(f"📌 Nombre: {a['nombre']}")
        print(f"📌 Categoría: {a['categoria']}")
        print(f"📌 Presentación: {a['presentacion']}")
        print(f"📌 Descripción: {a.get('descripcion', 'Sin descripción')}")
    
    @requiere_permiso('articulos_editar')
    def _editar_articulo(self):
        """Edita un artículo existente"""
        self.mostrar_cabecera("EDITAR ARTÍCULO")
        
        try:
            idart = int(input("ID del artículo a editar: "))
            art = self.articulo_service.obtener_por_id(idart)
            
            if not art:
                print(f"❌ No existe artículo con ID {idart}")
                self.pausa()
                return
            
            print(f"\nEditando: {art['nombre']}")
            print("(Deje en blanco para mantener el valor actual)")
            print()
            
            codigo = input(f"Código [{art['codigo']}]: ") or art['codigo']
            nombre = input(f"Nombre [{art['nombre']}]: ") or art['nombre']
            descripcion = input(f"Descripción [{art.get('descripcion', '')}]: ") or art.get('descripcion')
            
            # Mostrar categorías
            categorias = self.categoria_service.listar()
            print("\nCategorías disponibles:")
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
                print("✅ Artículo actualizado correctamente")
            else:
                print("❌ Error al actualizar el artículo")
        
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
            
            print(f"\n¿Está seguro de eliminar {art['nombre']}?")
            confirmacion = input("Esta acción no se puede deshacer (escriba 'ELIMINAR' para confirmar): ")
            
            if confirmacion == 'ELIMINAR':
                if self.articulo_service.eliminar(idart):
                    print("✅ Artículo eliminado correctamente")
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
            print("🔧 Módulo de lotes en desarrollo")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        self.pausa()
    
    @requiere_permiso('ventas_ver')
    def menu_ventas(self):
        """Menú de gestión de ventas"""
        while True:
            self.mostrar_cabecera("GESTIÓN DE VENTAS")
            print("1. Listar ventas")
            print("2. Registrar venta")
            print("3. Ver detalle de venta")
            print("4. Anular venta")
            print("0. Volver")
            print()
            
            opcion = input("🔹 Seleccione una opción: ").strip()
            
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
    
    @requiere_permiso('ventas_ver')
    def _listar_ventas(self):
        """Lista todas las ventas"""
        self.mostrar_cabecera("LISTADO DE VENTAS")
        
        ventas = self.venta_service.listar()
        
        if not ventas:
            print("📭 No hay ventas registradas")
        else:
            print(f"{'ID':<5} {'FECHA':<12} {'COMPROBANTE':<20} {'CLIENTE':<25} {'ESTADO':<10}")
            print("-" * 72)
            for v in ventas:
                comp = f"{v['tipo_comprobante']} {v['serie']}-{v['numero_comprobante']}"
                print(f"{v['idventa']:<5} {v['fecha']:<12} {comp:<20} {v['cliente']:<25} {v['estado']:<10}")
        
        self.pausa()
    
    @requiere_permiso('ventas_crear')
    def _registrar_venta(self):
        """Registra una nueva venta"""
        self.mostrar_cabecera("REGISTRAR VENTA")
        
        # Seleccionar cliente
        print("Seleccionar cliente:")
        clientes = self.cliente_service.listar()
        for c in clientes[:5]:  # Mostrar solo primeros 5
            print(f"  {c['idcliente']}. {c['nombre']} {c['apellidos']}")
        
        try:
            idcliente = int(input("\nID del cliente: "))
        except:
            print("❌ Cliente inválido")
            self.pausa()
            return
        
        # Datos de la venta
        print("\nTipo de comprobante:")
        print("  1. Factura")
        print("  2. Boleta")
        print("  3. Ticket")
        tipo_map = {'1': 'FACTURA', '2': 'BOLETA', '3': 'TICKET'}
        tipo_op = input("Seleccione: ").strip()
        tipo_comprobante = tipo_map.get(tipo_op, 'BOLETA')
        
        serie = input("Serie (ej. F001): ")
        numero = input("Número: ")
        
        # Detalle de venta
        detalle = []
        while True:
            print("\n--- Agregar producto ---")
            codigo = input("Código del artículo (0 para terminar): ")
            if codigo == '0':
                break
            
            art = self.articulo_service.buscar_por_codigo(codigo)
            if not art:
                print("❌ Artículo no encontrado")
                continue
            
            try:
                cantidad = int(input("Cantidad: "))
                precio = float(input("Precio unitario: "))
            except:
                print("❌ Cantidad o precio inválido")
                continue
            
            detalle.append({
                'idarticulo': art['idarticulo'],
                'cantidad': cantidad,
                'precio_venta': precio
            })
            print(f"✅ {art['nombre']} agregado")
        
        if not detalle:
            print("❌ Debe agregar al menos un producto")
            self.pausa()
            return
        
        # Registrar venta
        usuario = self.trabajador_service.get_usuario_actual()
        idventa = self.venta_service.registrar(
            usuario['idtrabajador'], idcliente, tipo_comprobante,
            serie, numero, 18.0, detalle
        )
        
        if idventa:
            print(f"✅ Venta {idventa} registrada correctamente")
        else:
            print("❌ Error al registrar la venta")
        
        self.pausa()
    
    @requiere_permiso('ventas_ver')
    def _ver_venta(self):
        """Muestra detalle de una venta"""
        self.mostrar_cabecera("DETALLE DE VENTA")
        
        try:
            idventa = int(input("ID de la venta: "))
            venta = self.venta_service.obtener_por_id(idventa)
            
            if not venta:
                print(f"❌ No existe venta con ID {idventa}")
                self.pausa()
                return
            
            print(f"\n📌 Venta N°: {venta['idventa']}")
            print(f"📌 Fecha: {venta['fecha']}")
            print(f"📌 Cliente: {venta['cliente']}")
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
                    print(f"   - {d['articulo']} x{d['cantidad']} @ {d['precio_venta']} = {subtotal:.2f}")
                print(f"\n💰 TOTAL: {total:.2f}")
        
        except Exception as e:
            print(f"❌ Error: {e}")
        
        self.pausa()
    
    @requiere_permiso('ventas_anular')
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
            
            print(f"\nVenta: {venta['idventa']} - {venta['fecha']}")
            print(f"Cliente: {venta['cliente']}")
            total = sum(d['cantidad'] * d['precio_venta'] for d in venta.get('detalle', []))
            print(f"Total: {total:.2f}")
            
            confirmacion = input("\n¿Está seguro de anular esta venta? (s/N): ").lower()
            if confirmacion == 's':
                if self.venta_service.anular(idventa):
                    print("✅ Venta anulada correctamente")
                else:
                    print("❌ Error al anular la venta")
            else:
                print("Operación cancelada")
        
        except Exception as e:
            print(f"❌ Error: {e}")
        
        self.pausa()
    
    def run(self):
        """Ejecuta el sistema"""
        if not self.conectar_db():
            return
        
        while True:
            opcion = self.mostrar_menu_principal()
            
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
                    print("🔧 Módulo de proveedores en desarrollo")
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
                    print("🔧 Módulo de inventario en desarrollo")
                else:
                    print("❌ No tiene permisos para acceder a inventario")
                self.pausa()
            elif opcion == '6':
                if self.rol_service.tiene_permiso('reportes_ventas'):
                    print("🔧 Módulo de reportes en desarrollo")
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
                print("\n👋 ¡Hasta luego!")
                break
            else:
                print("❌ Opción no válida")
                self.pausa()
        
        self.db.cerrar()

if __name__ == "__main__":
    sistema = SistemaVentas()
    sistema.run()
