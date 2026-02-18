import sys
import tty
import termios

def leer_con_mascara(mascara):
    """
    Lee entrada del usuario aplicando una máscara.
    Ejemplo: leer_con_mascara("DD/MM/YYYY")
    """
    import sys
    import tty
    import termios
    
    print(f"\r{mascara}", end='', flush=True)
    
    pos = 0
    resultado = list(mascara)
    lugares = [i for i, char in enumerate(mascara) if char in ('D', 'M', 'Y')]
    
    # Guardar configuración original de la terminal
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    
    try:
        # Configurar terminal para modo raw
        tty.setraw(sys.stdin.fileno())
        
        while pos < len(lugares):
            char = sys.stdin.read(1)
            
            if ord(char) == 3:  # Ctrl+C
                raise KeyboardInterrupt
            elif ord(char) == 127 or ord(char) == 8:  # Backspace
                if pos > 0:
                    pos -= 1
                    resultado[lugares[pos]] = mascara[lugares[pos]]
                    print(f"\r{''.join(resultado)}", end='', flush=True)
            elif char.isdigit():
                if pos < len(lugares):
                    resultado[lugares[pos]] = char
                    pos += 1
                    print(f"\r{''.join(resultado)}", end='', flush=True)
    finally:
        # Restaurar configuración original
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        print()
    
    # Extraer las partes de la fecha
    partes = ''.join(resultado).split('/')
    if len(partes) == 3:
        return f"{partes[0]}/{partes[1]}/{partes[2]}"
    return ''.join(resultado)
