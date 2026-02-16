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
        
        # Asignar rol_service a trabajador_service
        self.trabajador_service.rol_service = self.rol_service
        
        # Inicializar servicio de email
        self.email_service = EmailService(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            email_remitente="TU_CORREO@gmail.com",  # ← CAMBIA ESTO
            password="TU_CONTRASEÑA_DE_APLICACION"  # ← CAMBIA ESTO
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
        """Login normal con usuario y contraseña"""
        usuario = input("Usuario: ")
        password = input("Contraseña: ")
        
        if self.trabajador_service.login(usuario, password):
            print("✅ Sesión iniciada correctamente")
        else:
            print("❌ Error al iniciar sesión")
        
        self.pausa()
    
    def _recuperar_contraseña(self):
        """Proceso de recuperación de contraseña"""
        self.mostrar_cabecera("RECUPERAR CONTRASEÑA")
        
        email = input("Ingrese su email registrado: ")
        
        # Buscar usuario por email
        usuario = self.trabajador_service.buscar_por_email(email)
        
        if not usuario:
            print("❌ No existe un usuario con ese email")
            self.pausa()
            return
        
        # Generar y enviar código
        codigo = self.email_service.generar_codigo()
        
        if self.email_service.enviar_codigo_recuperacion(email, codigo):
            print(f"✅ Se ha enviado un código a {email}")
            print()
            
            # Solicitar código
            codigo_ingresado = input("Ingrese el código recibido: ")
            
            if self.email_service.verificar_codigo(email, codigo_ingresado):
                print("✅ Código verificado correctamente")
                print()
                
                # Solicitar nueva contraseña
                nueva_pass = input("Ingrese nueva contraseña (mínimo 6 caracteres): ")
                confirmar = input("Confirme nueva contraseña: ")
                
                if nueva_pass == confirmar and len(nueva_pass) >= 6:
                    if self.trabajador_service.actualizar_password(email, nueva_pass):
                        print("✅ Contraseña actualizada correctamente")
                        print("🔐 Ya puede iniciar sesión con su nueva contraseña")
                    else:
                        print("❌ Error al actualizar la contraseña")
                else:
                    print("❌ Las contraseñas no coinciden o son muy cortas")
            else:
                print("❌ Código incorrecto o expirado")
        else:
            print("❌ Error al enviar el código. Intente más tarde")
        
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
    
    def run(self):
        """Ejecuta el sistema"""
        if not self.conectar_db():
            return
        
        while True:
            opcion = self.mostrar_menu_principal()
            
            if opcion == '1':
                self.menu_categorias()
            elif opcion == '2':
                print("🔧 Módulo de artículos en desarrollo")
                self.pausa()
            elif opcion == '3':
                print("🔧 Módulo de proveedores en desarrollo")
                self.pausa()
            elif opcion == '4':
                print("🔧 Módulo de ventas en desarrollo")
                self.pausa()
            elif opcion == '5':
                print("🔧 Módulo de inventario en desarrollo")
                self.pausa()
            elif opcion == '6':
                print("🔧 Módulo de reportes en desarrollo")
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
