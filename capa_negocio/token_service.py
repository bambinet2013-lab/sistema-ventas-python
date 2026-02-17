from datetime import datetime, timedelta
import secrets
import hashlib
from loguru import logger

class TokenService:
    """Servicio para gestionar tokens de recuperación"""
    
    def __init__(self, conexion):
        self.conexion = conexion
        self.cursor = conexion.cursor()
    
    def generar_token(self):
        """Genera un token criptográficamente seguro"""
        return secrets.token_urlsafe(32)  # Ej: "x7q9p3m2k1j5h8g4f6d3s9a2w5e7r8t9"
    
    def crear_token(self, idtrabajador):
        """Crea un token único y lo guarda en BD"""
        try:
            # Generar token seguro
            token_raw = self.generar_token()
            
            # Crear hash del token para almacenar (por seguridad)
            token_hash = hashlib.sha256(token_raw.encode()).hexdigest()
            
            # Fecha de expiración (30 minutos)
            expires_at = datetime.now() + timedelta(minutes=30)
            
            # Guardar en BD
            self.cursor.execute("""
                INSERT INTO reset_tokens (idtrabajador, token, expires_at)
                VALUES (?, ?, ?)
            """, (idtrabajador, token_hash, expires_at))
            self.cursor.commit()
            
            logger.info(f"✅ Token creado para trabajador {idtrabajador}")
            
            # Devolver el token original para enviar por email
            return token_raw
            
        except Exception as e:
            logger.error(f"❌ Error al crear token: {e}")
            return None
    
    def verificar_token(self, token_raw):
        """Verifica si un token es válido y devuelve el id del trabajador"""
        try:
            # Calcular hash del token recibido
            token_hash = hashlib.sha256(token_raw.encode()).hexdigest()
            
            # Buscar token en BD
            self.cursor.execute("""
                SELECT idtrabajador, expires_at, used
                FROM reset_tokens
                WHERE token = ? AND used = 0 AND expires_at > GETDATE()
            """, (token_hash,))
            
            resultado = self.cursor.fetchone()
            if resultado:
                idtrabajador = resultado[0]
                
                # Marcar como usado (opcional - lo marcaremos después del cambio)
                # self.cursor.execute("UPDATE reset_tokens SET used = 1 WHERE token = ?", (token_hash,))
                # self.cursor.commit()
                
                logger.info(f"✅ Token válido para trabajador {idtrabajador}")
                return idtrabajador
            
            logger.warning("⚠️ Token inválido o expirado")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error al verificar token: {e}")
            return None
    
    def marcar_token_usado(self, token_raw):
        """Marca un token como usado después de cambiar la contraseña"""
        try:
            token_hash = hashlib.sha256(token_raw.encode()).hexdigest()
            self.cursor.execute("UPDATE reset_tokens SET used = 1 WHERE token = ?", (token_hash,))
            self.cursor.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Error al marcar token como usado: {e}")
            return False
    
    def limpiar_tokens_expirados(self):
        """Elimina tokens expirados de la BD"""
        try:
            self.cursor.execute("DELETE FROM reset_tokens WHERE expires_at < GETDATE()")
            self.cursor.commit()
            logger.info("🧹 Tokens expirados eliminados")
            return True
        except Exception as e:
            logger.error(f"❌ Error al limpiar tokens: {e}")
            return False

