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

from capa_negocio.categoria_service import CategoriaService
from capa_negocio.cliente_service import ClienteService
from capa_negocio.articulo_service import ArticuloService
from capa_negocio.trabajador_service import TrabajadorService
from capa_negocio.venta_service import VentaService
from capa_negocio.base_service import BaseService

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
        """Muestra el menú principal"""
        self.mostrar_cabecera("SISTEMA DE VENTAS - 3 CAPAS")
        
        usuario = self.trabajador_service.get_usuario_actual()
        if usuario:
            print(f"👤 Usuario: {usuario['nombre']} {usuario['apellidos']}")
            print()
        
        print("1. Gestión de Categorías")
        print("2. Gestión de Clientes")
        print("3. Gestión de Artículos")
        print("4. Gestión de Ventas")
        print("5. Gestión de Ingresos")
        print("6. Reportes")
        if usuario:
            print("7. Cerrar Sesión")
        else:
            print("7. Iniciar Sesión")
        print("0. Salir")
        print()
        
        return input("🔹 Seleccione una opción: ").strip()
    
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
    
    def menu_login(self):
        """Menú de inicio de sesión"""
        self.mostrar_cabecera("INICIAR SESIÓN")
        
        usuario = input("Usuario: ")
        password = input("Contraseña: ")
        
        if self.trabajador_service.login(usuario, password):
            print("✅ Sesión iniciada correctamente")
        else:
            print("❌ Error al iniciar sesión")
        
        self.pausa()
    
    def menu_logout(self):
        """Cerrar sesión"""
        self.trabajador_service.logout()
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
                print("🔧 Módulo de clientes en desarrollo")
                self.pausa()
            elif opcion == '3':
                print("🔧 Módulo de artículos en desarrollo")
                self.pausa()
            elif opcion == '4':
                print("🔧 Módulo de ventas en desarrollo")
                self.pausa()
            elif opcion == '5':
                print("🔧 Módulo de ingresos en desarrollo")
                self.pausa()
            elif opcion == '6':
                print("🔧 Módulo de reportes en desarrollo")
                self.pausa()
            elif opcion == '7':
                if self.trabajador_service.get_usuario_actual():
                    self.menu_logout()
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
