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

    def detectar_categoria_motos(self, nombre: str) -> Optional[Dict]:
        """
        Detecta si el producto pertenece a la categoría de motos
        y devuelve el ID de categoría (101-111) e impuesto (siempre 2 - General)
        """
        if not nombre:
            return None
        
        nombre_upper = nombre.upper()
        
        # Reglas para cada categoría de motos
        reglas_motos = [
            # (palabras clave, idcategoria, nombre_categoria)
            (['PISTON', 'ANILLO', 'CIGUEÑAL', 'VALVULA', 'EMPACADURA'], 101, 'Motor'),
            (['CADENA', 'PIÑON', 'CORONA', 'CORREA', 'EMBRAGUE'], 102, 'Transmisión'),
            (['PASTILLA', 'BANDA', 'DISCO FRENO', 'GUAYA', 'FRENO'], 103, 'Frenos'),
            (['AMORTIGUADOR', 'BARRA', 'RODAMIENTO', 'SUSPENSION'], 104, 'Suspensión'),
            (['BATERIA', 'BUJIA', 'CDI', 'REGULADOR', 'BOMBILLO', 'BOYA'], 105, 'Eléctrico'),
            (['ACEITE 2T', 'ACEITE 4T', 'LIGA FRENO', 'LUBRICANTE', 'ACEITE MOTOR'], 106, 'Lubricantes'),
            (['FILTRO ACEITE', 'FILTRO AIRE', 'FILTRO GASOLINA'], 107, 'Filtros'),
            (['CAUCHO', 'LLANTA', 'TRIPA', 'NEUMATICO', 'CAMARA'], 108, 'Cauchos'),
            (['CASCO', 'GUANTE', 'CHAQUETA', 'MALETERO', 'CALCOMANIA', 'PEGATINA'], 109, 'Accesorios'),
            (['HERRAMIENTA', 'LLAVE', 'DESARMADOR', 'ALICATE', 'JUEGO LLAVES'], 110, 'Herramientas'),
            (['SERVICIO', 'MANO OBRA', 'REPARACION', 'CAMBIO ACEITE', 'ENTONACION'], 111, 'Servicios')
        ]
        
        # Buscar coincidencias
        for palabras, cat_id, cat_nombre in reglas_motos:
            if any(palabra in nombre_upper for palabra in palabras):
                return {
                    'idcategoria': cat_id,
                    'nombre_categoria': cat_nombre,
                    'id_impuesto': 2,  # Siempre General (G) para motos
                    'confianza': 0.90,
                    'tipo': 'MOTOS',
                    'palabra_encontrada': [p for p in palabras if p in nombre_upper][0]
                }
        
        return None
    
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
        """
        Analiza el nombre del producto y sugiere el impuesto y categoría
        Primero intenta con motos, luego con supermercado
        """
        if not nombre:
            return None
        
        # 1. Intentar detectar si es producto de motos
        resultado_motos = self.detectar_categoria_motos(nombre)
        if resultado_motos:
            logger.info(f"🏍️ Producto de motos detectado: {resultado_motos['nombre_categoria']}")
            return resultado_motos
            # 2. Detectar chucherías y snacks
        nombre_upper = nombre.upper()
        
        # ===== CHUCHERÍAS =====
        # Papitas y snacks salados
        if any(p in nombre_upper for p in ['PAPITA', 'DORITO', 'SNACK', 'BOTANA', 'CHIPS', 'PLATANUT', 'RUFLE']):
            return {
                'idcategoria': 2,
                'id_impuesto': 2,
                'confianza': 0.90,
                'tipo': 'SUPERMERCADO',
                'categoria_nombre': 'Víveres',
                'producto_tipo': 'snack_salado'
            }
        
        # Chocolates y bombones
        if any(p in nombre_upper for p in ['CHOCOLATE', 'BOMBON', 'BOMBÓN', 'CONFITE']):
            return {
                'idcategoria': 2,
                'id_impuesto': 2,
                'confianza': 0.90,
                'tipo': 'SUPERMERCADO',
                'categoria_nombre': 'Víveres',
                'producto_tipo': 'chocolate'
            }
        
        # Caramelos y gomitas
        if any(p in nombre_upper for p in ['CARAMELO', 'CHUPETA', 'GOMITA', 'MELOCHA']):
            return {
                'idcategoria': 2,
                'id_impuesto': 2,
                'confianza': 0.90,
                'tipo': 'SUPERMERCADO',
                'categoria_nombre': 'Víveres',
                'producto_tipo': 'caramelo'
            }
        
        # Galletas
        if any(p in nombre_upper for p in ['GALLETA', 'WAFFER', 'ORE0', 'CLUB SOCIAL', 'MARIAS']):
            return {
                'idcategoria': 2,
                'id_impuesto': 2,
                'confianza': 0.90,
                'tipo': 'SUPERMERCADO',
                'categoria_nombre': 'Víveres',
                'producto_tipo': 'galleta'
            }
        
        # Términos generales para chucherías
        if any(p in nombre_upper for p in ['CHUCHERIA', 'GOLOSINA']):
            return {
                'idcategoria': 2,
                'id_impuesto': 2,
                'confianza': 0.85,
                'tipo': 'SUPERMERCADO',
                'categoria_nombre': 'Víveres'
            }
        # ===== BEBIDAS PROCESADAS =====
        # Maltas
        if any(p in nombre_upper for p in ['MALTA', 'MALTIN', 'POLAR', 'REGIONAL']):
            return {
                'idcategoria': 3,
                'id_impuesto': 2,
                'confianza': 0.90,
                'tipo': 'SUPERMERCADO',
                'categoria_nombre': 'Bebidas',
                'producto_tipo': 'malta'
            }
        
        # Jugos pasteurizados
        if any(p in nombre_upper for p in ['JUGO', 'NECTAR', 'PASTEURIZADO', 'DEL VALLE', 'TROPICAL']):
            return {
                'idcategoria': 3,
                'id_impuesto': 2,
                'confianza': 0.90,
                'tipo': 'SUPERMERCADO',
                'categoria_nombre': 'Bebidas',
                'producto_tipo': 'jugo'
            }
        
        # Bebidas energéticas
        if any(p in nombre_upper for p in ['ENERGETICA', 'RED BULL', 'VIVE 100']):
            return {
                'idcategoria': 3,
                'id_impuesto': 2,
                'confianza': 0.90,
                'tipo': 'SUPERMERCADO',
                'categoria_nombre': 'Bebidas',
                'producto_tipo': 'energetica'
            }
        
        # Bebidas isotónicas
        if any(p in nombre_upper for p in ['ISOTONICO', 'SPORADE', 'GATORADE']):
            return {
                'idcategoria': 3,
                'id_impuesto': 2,
                'confianza': 0.90,
                'tipo': 'SUPERMERCADO',
                'categoria_nombre': 'Bebidas',
                'producto_tipo': 'isotonica'
            }
        # ===== ENLATADOS Y SALSAS =====
        # Atún y pescados enlatados
        if any(p in nombre_upper for p in ['ATUN', 'ATÚN', 'SARDINA', 'PESCADO ENLATADO']):
            return {
                'idcategoria': 2,
                'id_impuesto': 2,
                'confianza': 0.90,
                'tipo': 'SUPERMERCADO',
                'categoria_nombre': 'Víveres',
                'producto_tipo': 'enlatado_pescado'
            }
        
        # Salsas y condimentos
        if any(p in nombre_upper for p in ['MAYONESA', 'KETCHUP', 'SALSA', 'TÁRTARA', 'CEASAR']):
            return {
                'idcategoria': 2,
                'id_impuesto': 2,
                'confianza': 0.90,
                'tipo': 'SUPERMERCADO',
                'categoria_nombre': 'Víveres',
                'producto_tipo': 'salsa'
            }
        
        # Términos generales para enlatados
        if any(p in nombre_upper for p in ['ENLATADO', 'LATA', 'CONSERVA']):
            return {
                'idcategoria': 2,
                'id_impuesto': 2,
                'confianza': 0.85,
                'tipo': 'SUPERMERCADO',
                'categoria_nombre': 'Víveres'
            }
        # ===== EMBUTIDOS Y FIAMBRES =====
        # Embutidos básicos (EXENTOS)
        if any(p in nombre_upper for p in ['JAMON', 'JAMÓN', 'SALCHICHA', 'MORTADELA', 'CHORIZO', 'LONGANIZA']):
            return {
                'idcategoria': 7,
                'id_impuesto': 1,  # Exento
                'confianza': 0.90,
                'tipo': 'SUPERMERCADO',
                'categoria_nombre': 'Perecederos',
                'producto_tipo': 'embutido_basico'
            }
        
        # Embutidos procesados/importados (GENERALES)
        if any(p in nombre_upper for p in ['PEPPERONI', 'SALAMI', 'JAMON YORK', 'JAMÓN YORK']):
            return {
                'idcategoria': 7,
                'id_impuesto': 2,  # General
                'confianza': 0.90,
                'tipo': 'SUPERMERCADO',
                'categoria_nombre': 'Perecederos',
                'producto_tipo': 'embutido_procesado'
            }
        # ===== QUESOS =====
        # Quesos procesados/importados (GENERAL)
        if any(p in nombre_upper for p in ['QUESO AMARILLO', 'QUESO CHEDDAR', 'QUESO PARMESANO', 'QUESO DE UNTAR', 'QUESO CREMA']):
            return {
                'idcategoria': 4,
                'id_impuesto': 2,  # General
                'confianza': 0.90,
                'tipo': 'SUPERMERCADO',
                'categoria_nombre': 'Lácteos',
                'producto_tipo': 'queso_procesado'
            }
        
        # Quesos nacionales/frescos (EXENTOS)
        if any(p in nombre_upper for p in ['QUESO BLANCO', 'QUESO FRESCO', 'QUESO PAISA', 'QUESO GUAYANÉS']):
            return {
                'idcategoria': 4,
                'id_impuesto': 1,  # Exento
                'confianza': 0.90,
                'tipo': 'SUPERMERCADO',
                'categoria_nombre': 'Lácteos',
                'producto_tipo': 'queso_fresco'
            }
        # ===== CAFÉ =====
        # Café natural (EXENTO)
        if any(p in nombre_upper for p in ['CAFE', 'CAFÉ', 'CAFE MOLIDO', 'CAFÉ MOLIDO', 'CAFE GRANO', 'CAFÉ GRANO']):
            # Verificar que no sea instantáneo
            if 'INSTANTANEO' not in nombre_upper and 'INSTANTÁNEO' not in nombre_upper and 'NESCAFE' not in nombre_upper:
                return {
                    'idcategoria': 2,
                    'id_impuesto': 1,  # Exento
                    'confianza': 0.90,
                    'tipo': 'SUPERMERCADO',
                    'categoria_nombre': 'Víveres',
                    'producto_tipo': 'cafe_natural'
                }
        
        # Café instantáneo/procesado (GENERAL)
        if any(p in nombre_upper for p in ['CAFE INSTANTANEO', 'CAFÉ INSTANTÁNEO', 'NESCAFE', 'CAPUCCINO']):
            return {
                'idcategoria': 2,
                'id_impuesto': 2,  # General
                'confianza': 0.90,
                'tipo': 'SUPERMERCADO',
                'categoria_nombre': 'Víveres',
                'producto_tipo': 'cafe_instantaneo'
            }
        
        # 3. Si no es moto ni chuchería, usar la lógica existente de supermercado
        nombre_lower = nombre.lower()
        
        # Buscar por marca (prioridad alta)
        for marca, impuesto in self.marcas_conocidas.items():
            if marca in nombre_lower:
                return {
                    'id_impuesto': impuesto,
                    'confianza': 0.95,
                    'metodo': 'marca',
                    'palabra': marca
                }
        
        # Buscar por palabra clave
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
