import mysql.connector
from email import encoders
import os
import time
import json
import requests
import smtplib
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from flask_apscheduler import APScheduler
from werkzeug.utils import secure_filename
from email.mime.multipart import MIMEMultipart

# ============================= Conexión a base de datos
db = mysql.connector.connect(user="root",
                             passwd="@ProdLabEIT2020",
                             host="localhost",
                             port="3306",
                             database="LabEITDB",
                             autocommit=True)
cursor = db.cursor(dictionary=True, buffered=True)
cursor.execute("SET NAMES utf8mb4;")
# ===================================================

# Función para eliminar mensajes administrativos que cumplan con la fecha de eliminación indicada
# Revisión a las 23:59 todos los días


def revisar_mensajes_administrativos():
    fecha_actual = datetime.now().replace(microsecond=0)
    sql_query = """
        DELETE FROM
            Mensaje_administrativo
                WHERE datediff(fecha_eliminacion,%s) <= 0
    """
    cursor.execute(sql_query, (fecha_actual,))

# Función para eliminar tokens de passwords que hayan vencido (máx 1 día para usarlo)
# Revisión a las 23:59 todos los días


def revisar_tokens_password():
    fecha_actual = datetime.now().replace(microsecond=0)

    sql_query = """
        DELETE FROM
            Token_recuperacion_password
                WHERE datediff(fecha_registro,%s) <= -1
    """
    cursor.execute(sql_query, (fecha_actual,))

# Función para revisar los bloqueos de ip y eliminarlos en caso de que se cumplan las condiciones
# (Se desbloquea al finalizar el día en el que fue bloqueado)
# Revisión a las 23:59 todos los días


def revisar_bloqueos_ips():
    fecha_actual = datetime.now().replace(microsecond=0)

    sql_query = """
        DELETE FROM
            Bloqueos_IP
                WHERE datediff(fecha_bloqueo,%s) <= 0
    """
    cursor.execute(sql_query, (fecha_actual,))
  

def revisar_23_59():
    # Eliminación de mensajes administrativos
    revisar_mensajes_administrativos()

    # Eliminación de tokens de password
    revisar_tokens_password()

    # Revisar bloqueos de IPs
    revisar_bloqueos_ips()

if __name__ == "__main__":
    # Se ejecutan las funciones establecidas para las 18:30 (crontab)
    revisar_23_59()
    # Se cierra la conexión con la base de datos
    cursor.close()
    db.close()