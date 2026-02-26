"""
Utilidades para el sistema de ventas
"""
import random
import string

def generar_codigo_profesional():
    """
    Genera un código profesional único de formato LNNNN
    Ejemplo: A3829, M7401, C2918, F4512
    
    Returns:
        str: Código de 5 caracteres (1 letra + 4 números)
    """
    # Letra aleatoria (A-Z)
    letra = random.choice(string.ascii_uppercase)
    
    # 4 números aleatorios
    numeros = ''.join([str(random.randint(0, 9)) for _ in range(4)])
    
    return f"{letra}{numeros}"

def generar_codigo_unico_existente(codigos_existentes):
    """
    Genera un código único que no esté en la lista de existentes
    
    Args:
        codigos_existentes: Lista de códigos ya usados
        
    Returns:
        str: Código único
    """
    while True:
        codigo = generar_codigo_profesional()
        if codigo not in codigos_existentes:
            return codigo
