import smtplib
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from loguru import logger

class EmailService:
    """Servicio para envío de correos electrónicos"""
    
    def __init__(self, smtp_server="smtp.gmail.com", smtp_port=587, 
                 email_remitente="tu_correo@gmail.com", password="tu_contraseña"):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.email_remitente = email_remitente
        self.password = password
        self.codigos_recuperacion = {}  # Diccionario temporal: {email: codigo}
    
    def generar_codigo(self, longitud=6):
        """Genera un código aleatorio de recuperación"""
        return ''.join(random.choices(string.digits, k=longitud))
    
    def enviar_codigo_recuperacion(self, email_destino, codigo):
        """Envía el código de recuperación por correo"""
        try:
            # Crear mensaje
            mensaje = MIMEMultipart()
            mensaje['From'] = self.email_remitente
            mensaje['To'] = email_destino
            mensaje['Subject'] = "Código de recuperación - Sistema de Ventas"
            
            # Cuerpo del correo
            cuerpo = f"""
            <html>
                <body style="font-family: Arial, sans-serif; padding: 20px;">
                    <h2 style="color: #4CAF50;">Recuperación de Contraseña</h2>
                    <p>Has solicitado restablecer tu contraseña en el Sistema de Ventas.</p>
                    <p>Tu código de verificación es:</p>
                    <h1 style="background-color: #f0f0f0; padding: 15px; text-align: center; 
                               font-size: 36px; letter-spacing: 5px; border-radius: 10px;">
                        {codigo}
                    </h1>
                    <p>Este código expirará en 15 minutos.</p>
                    <p>Si no solicitaste este cambio, ignora este mensaje.</p>
                    <hr>
                    <p style="color: #888; font-size: 12px;">Sistema de Ventas - 3 Capas</p>
                </body>
            </html>
            """
            
            mensaje.attach(MIMEText(cuerpo, 'html'))
            
            # Enviar correo
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_remitente, self.password)
            server.send_message(mensaje)
            server.quit()
            
            # Guardar código temporalmente
            self.codigos_recuperacion[email_destino] = {
                'codigo': codigo,
                'intentos': 0
            }
            
            logger.success(f"✅ Código enviado a {email_destino}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al enviar correo: {e}")
            return False
    
    def verificar_codigo(self, email, codigo_ingresado):
        """Verifica si el código ingresado es correcto"""
        if email in self.codigos_recuperacion:
            datos = self.codigos_recuperacion[email]
            
            # Incrementar intentos
            datos['intentos'] += 1
            
            # Máximo 3 intentos
            if datos['intentos'] > 3:
                del self.codigos_recuperacion[email]
                logger.warning(f"⚠️ Demasiados intentos para {email}")
                return False
            
            # Verificar código
            if datos['codigo'] == codigo_ingresado:
                del self.codigos_recuperacion[email]  # Eliminar código usado
                return True
        
        return False
