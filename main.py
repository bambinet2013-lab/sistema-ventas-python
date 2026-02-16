#!/usr/bin/env python3
"""
Sistema de Ventas - Punto de entrada principal
"""
from loguru import logger
from capa_datos.conexion import ConexionDB
from capa_datos.categoria_repo import CategoriaRepositorio
from capa_negocio.categoria_service import CategoriaService

def main():
    """Función principal"""
    logger.add("sistema_ventas.log", rotation="10 MB")
    
    logger.info("🚀 Iniciando Sistema de Ventas Python")
    
    # Conectar a la base de datos
    db = ConexionDB()
    conn = db.conectar()
    
    if not conn:
        logger.error("❌ No se pudo conectar a la base de datos")
        return
    
    try:
        # Ejemplo de uso con categorías
        repo = CategoriaRepositorio(conn)
        service = CategoriaService(repo)
        
        # Listar categorías existentes
        categorias = service.listar_categorias()
        print("\n📋 CATEGORÍAS EXISTENTES:")
        for cat in categorias:
            print(f"  {cat['idcategoria']}: {cat['nombre']}")
        
        # Insertar una categoría de ejemplo
        if not categorias:
            print("\n📝 Insertando categorías de ejemplo...")
            service.crear_categoria("Electrónicos", "Productos electrónicos")
            service.crear_categoria("Ropa", "Prendas de vestir")
            
            # Volver a listar
            categorias = service.listar_categorias()
            print("\n📋 CATEGORÍAS DESPUÉS DE INSERTAR:")
            for cat in categorias:
                print(f"  {cat['idcategoria']}: {cat['nombre']}")
    
    finally:
        # Cerrar conexión
        db.cerrar()
    
    logger.info("✅ Sistema finalizado correctamente")

if __name__ == "__main__":
    main()
