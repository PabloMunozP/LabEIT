import smtplib
from flask import flash
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Envío de correo (notificaciones de solicitudes de préstamo)
def enviar_correo_notificacion(archivo, str_asunto, correo_usuario):
    # Se crea el mensaje
    correo = MIMEText(archivo, "html")
    correo.set_charset("utf-8")
    correo["From"] = "labeit.udp@gmail.com"
    correo["To"] = correo_usuario
    correo["Subject"] = str_asunto

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com")
        server.login("labeit.udp@gmail.com", "LabEIT_UDP_2020")
        str_correo = correo.as_string()
        server.sendmail("labeit.udp@gmail.com", correo_usuario, str_correo)
        server.close()
        flash("correo-exito")  # Notificación de éxito al enviar el correo

    except Exception as e:
        print(e)
        flash("correo-fallido")  # Notificación de fallo al enviar el correo