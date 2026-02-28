"""
Servicio de Inteligencia Artificial para clasificación automática de productos
"""
from loguru import logger
from typing import Dict, List, Optional, Tuple
import re

class IAProductosService:
    def __init__(self, repo_reglas=None):
        self.repo_reglas = repo_reglas
        self.reglas_cargadas = False
        self.palabras_clave = {}  # {palabra: id_impuesto}
        self.marcas_conocidas = {} # {marca: id_impuesto}
        self.cargar_reglas_iniciales()
    
    def cargar_reglas_iniciales(self):
        """Carga reglas por defecto en memoria"""
        # Exentos (id_impuesto=1)
        self.palabras_clave = {
            'harina': 1, 'arroz': 1, 'azucar': 1, 'leche': 1, 'huevo': 1,
            'pan': 1, 'pasta': 1, 'carne': 1, 'pollo': 1, 'pescado': 1,
            'fruta': 1, 'verdura': 1, 'legumbre': 1, 'medicina': 1,
            # Generales (id_impuesto=2)
            'mayonesa': 2, 'salsa': 2, 'atun': 2, 'gaseosa': 2, 'refresco': 2,
            'jabon': 2, 'detergente': 2, 'shampoo': 2, 'desodorante': 2,
        }
        
        self.marcas_conocidas = {
            'santoni': 1, 'bondora': 1, 'konfit': 1, 'pampa': 1,
            'ole': 2, 'ronco': 2,
        }
        
        self.reglas_cargadas = True
        logger.info(f"✅ IAProductosService inicializado con {len(self.palabras_clave)} palabras clave")
    
    def analizar_producto(self, nombre: str) -> Optional[Dict]:
        """Analiza el nombre del producto y sugiere el impuesto"""
        if not nombre:
            return None
        
        nombre_lower = nombre.lower()
        
        # 1. Buscar por marca (prioridad alta)
        for marca, impuesto in self.marcas_conocidas.items():
            if marca in nombre_lower:
                return {
                    'id_impuesto': impuesto,
                    'confianza': 0.95,
                    'metodo': 'marca',
                    'palabra': marca
                }
        
        # 2. Buscar por palabra clave
        palabras_encontradas = []
        for palabra, impuesto in self.palabras_clave.items():
            if palabra in nombre_lower:
                palabras_encontradas.append((palabra, impuesto))
        
        if palabras_encontradas:
            votos = {}
            for palabra, impuesto in palabras_encontradas:
                votos[impuesto] = votos.get(impuesto, 0) + 1
            
            impuesto_final = max(votos, key=votos.get)
            confianza = min(0.8 + (votos[impuesto_final] * 0.05), 0.95)
            
            return {
                'id_impuesto': impuesto_final,
                'confianza': confianza,
                'metodo': 'palabras_clave',
                'palabras': [p for p, _ in palabras_encontradas]
            }
        
        return None
    
    def obtener_nombre_impuesto(self, id_impuesto: int) -> str:
        """Obtiene el nombre del impuesto por su ID"""
        mapa = {1: 'Exento', 2: 'General', 3: 'Reducida', 4: 'Adicional'}
        return mapa.get(id_impuesto, 'Desconocido')
    
    def obtener_letra_fiscal(self, id_impuesto: int) -> str:
        """Obtiene la letra fiscal por ID de impuesto"""
        mapa = {1: 'E', 2: 'G', 3: 'R', 4: 'A'}
        return mapa.get(id_impuesto, '?')

    def detectar_categoria_venezolana(self, nombre: str) -> int:
        """
        Detecta la categoría venezolana basada en el nombre del producto
        Usando los IDs REALES de la BD:
        1: Electrónicos
        2: Viveres
        3: Bebidas
        4: Lácteos
        5: Otros
        7: Perecederos
        8: Limpieza
        9: Higiene
        """
        if not nombre:
            return 5  # Otros por defecto
        
        nombre_upper = nombre.upper()
        
        # ELECTRÓNICOS (ID 1)
        if any(palabra in nombre_upper for palabra in ['LAPTOP', 'COMPUTADORA', 'MOUSE', 'TECLADO', 
                                                        'MONITOR', 'CELULAR', 'TELEFONO', 'IMPRESORA']):
            return 1
        
        # VÍVERES (ID 2)
        if any(palabra in nombre_upper for palabra in ['HARINA', 'ARROZ', 'PASTA', 'GRANO', 'LENTEJA', 
                                                        'CARAOTA', 'QUINCHONCHO', 'AZUCAR', 'SAL', 
                                                        'ATUN', 'SARDINA', 'ENLATADO', 'MAYONESA', 
                                                        'SALSA', 'VINAGRE', 'ACEITE', 'CAFE']):
            return 2
        
        # BEBIDAS (ID 3)
        if any(palabra in nombre_upper for palabra in ['REFRESCO', 'GASEOSA', 'JUGO', 'MALTA', 'AGUA',
                                                        'POLAR', 'COCA', 'PEPSI', 'CHINOTO', 'FRESCOLITA']):
            return 3
        
        # LÁCTEOS (ID 4)
        if any(palabra in nombre_upper for palabra in ['LECHE', 'QUESO', 'YOGURT', 'MANTEQUILLA', 
                                                        'MARGARINA', 'KUMIS']):
            return 4
        
        # PERECEDEROS (ID 7)
        if any(palabra in nombre_upper for palabra in ['CARNE', 'POLLO', 'PESCADO', 'RES', 'CERDO',
                                                        'FRUTA', 'VERDURA', 'CEBOLLA', 'TOMATE',
                                                        'PIMENTON', 'Auyama', 'LECHOSA', 'PATILLA',
                                                        'MELON', 'CAMBUR', 'PLATANO']):
            return 7
        
        # LIMPIEZA (ID 8)
        if any(palabra in nombre_upper for palabra in ['JABON', 'DETERGENTE', 'CLORO', 'LIMPIDO',
                                                        'SUAVIZANTE', 'LYSOL', 'FAB', 'ARIEL']):
            return 8
        
        # HIGIENE (ID 9)
        if any(palabra in nombre_upper for palabra in ['SHAMPOO', 'ACONDICIONADOR', 'DESODORANTE',
                                                        'PASTA DENTAL', 'CEPILLO', 'JABON DE BAÑO',
                                                        'PREND', 'COLGATE', 'AXE']):
            return 9
        
        # OTROS (ID 5) - por defecto
        return 5
