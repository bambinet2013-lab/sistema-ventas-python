import smtplib
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email.utils import formataddr
from loguru import logger

class EmailService:
    """Servicio para envío de correos electrónicos"""
    
    def __init__(self, smtp_server="smtp.gmail.com", smtp_port=587, 
                 email_remitente="tu_correo@gmail.com", password="tu_contraseña"):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.email_remitente = email_remitente
        self.password = password
        self.codigos_recuperacion = {}  # Para compatibilidad
    
    def generar_codigo(self, longitud=6):
        """Genera un código aleatorio de recuperación (para compatibilidad)"""
        return ''.join(random.choices(string.digits, k=longitud))
    
    def enviar_enlace_magico(self, email_destino, token, nombre_usuario):
        """Envía un enlace mágico para recuperación de contraseña"""
        try:
            # Crear mensaje con codificación UTF-8
            mensaje = MIMEMultipart('alternative')
            mensaje['From'] = formataddr((str(Header('Sistema Ventas', 'utf-8')), self.email_remitente))
            mensaje['To'] = email_destino
            mensaje['Subject'] = Header('🔐 Recuperación de contraseña - Sistema de Ventas', 'utf-8')
            
            # Versión texto plano (para clientes que no soportan HTML)
            texto_plano = f"""
Recuperación de Contraseña - Sistema de Ventas

Hola {nombre_usuario},

Has solicitado restablecer tu contraseña.

Tu token de recuperación es: {token}

Este token expirará en 30 minutos.

Instrucciones:
1. Vuelve al programa
2. Selecciona opción "Recuperar contraseña"
3. Elige "Ingresar token manual"
4. Copia y pega este token
5. Establece tu nueva contraseña

Si no solicitaste esto, ignora este mensaje.

Sistema de Ventas
"""
            
            # Versión HTML
            html = f"""
            <html>
                <head>
                    <meta charset="UTF-8">
                </head>
                <body style="font-family: Arial, sans-serif; padding: 20px; max-width: 600px;">
                    <h2 style="color: #4CAF50;">Recuperación de Contraseña</h2>
                    <p>Hola <strong>{nombre_usuario}</strong>,</p>
                    <p>Recibimos una solicitud para restablecer tu contraseña.</p>
                    
                    <div style="background-color: #f5f5f5; padding: 20px; border-radius: 10px; margin: 20px 0; text-align: center;">
                        <p style="font-size: 16px; margin-bottom: 20px;">Tu token de recuperación es:</p>
                        <div style="background-color: #333; color: #fff; padding: 15px; font-family: monospace; font-size: 18px; letter-spacing: 2px; border-radius: 5px;">
                            {token}
                        </div>
                        <p style="margin-top: 20px; font-size: 14px; color: #666;">
                            ⏰ Este token expirará en <strong>30 minutos</strong>.
                        </p>
                    </div>
                    
                    <div style="background-color: #fff3cd; border: 1px solid #ffeeba; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p style="margin: 0; color: #856404;">
                            <strong>📝 Instrucciones:</strong><br>
                            1. Vuelve al programa<br>
                            2. Selecciona opción "Recuperar contraseña"<br>
                            3. Elige "Ingresar token manual"<br>
                            4. Copia y pega el token de arriba<br>
                            5. Establece tu nueva contraseña
                        </p>
                    </div>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p style="margin: 0; font-size: 13px;">
                            <strong>¿No solicitaste esto?</strong><br>
                            Si no solicitaste restablecer tu contraseña, ignora este correo. 
                            Tu cuenta permanece segura.
                        </p>
                    </div>
                    
                    <hr style="border: none; border-top: 1px solid #eee;">
                    <p style="color: #999; font-size: 12px;">
                        Sistema de Ventas - 3 Capas<br>
                        Si tienes problemas, contacta al administrador.
                    </p>
                </body>
            </html>
            """
            
            # Adjuntar versiones con UTF-8 explícito
            mensaje.attach(MIMEText(texto_plano, 'plain', 'utf-8'))
            mensaje.attach(MIMEText(html, 'html', 'utf-8'))
            
            # Enviar correo
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_remitente, self.password)
            server.send_message(mensaje)
            server.quit()
            
            logger.success(f"📧 Enlace mágico enviado a {email_destino}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al enviar enlace: {e}")
            return False
    
    def enviar_codigo_recuperacion(self, email_destino, codigo):
        """Versión antigua para compatibilidad"""
        return self.enviar_enlace_magico(email_destino, codigo, "Usuario")
