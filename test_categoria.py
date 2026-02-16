#!/usr/bin/env python3
"""
Pruebas para el módulo de categorías
"""
from capa_datos.conexion import ConexionDB
from capa_datos.categoria_repo import CategoriaRepositorio
from capa_negocio.categoria_service import CategoriaService

def probar_categorias():
    """Prueba todas las operaciones de categoría"""
    print("🔍 Probando módulo de categorías...")
    
    db = ConexionDB()
    conn = db.conectar()
    
    if not conn:
        print("❌ No se pudo conectar")
        return
    
    try:
        repo = CategoriaRepositorio(conn)
        service = CategoriaService(repo)
        
        # 1. Listar
        print("\n1. Listando categorías:")
        categorias = service.listar_categorias()
        for cat in categorias:
            print(f"   - {cat}")
        
        # 2. Insertar
        print("\n2. Insertando categoría de prueba:")
        if service.crear_categoria("Prueba", "Categoría de prueba"):
            print("   ✅ Insertada")
        else:
            print("   ❌ Falló inserción")
        
        # 3. Listar nuevamente
        print("\n3. Listando después de insertar:")
        categorias = service.listar_categorias()
        for cat in categorias:
            print(f"   - {cat}")
    
    finally:
        db.cerrar()

if __name__ == "__main__":
    probar_categorias()
