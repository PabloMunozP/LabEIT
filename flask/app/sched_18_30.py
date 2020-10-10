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


# Envío de notificaciones vía correo electrónico
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

    except Exception as e:
        print(e)

# ============= Funciones programadas ======================
# Función para eliminar detalles de solicitudes aprobados que hayan cumplido con la fecha de vencimiento
# Revisión a las 18:30 todos los días


def eliminar_detalles_vencidos():
    fecha_actual = datetime.now().replace(microsecond=0)
    # Se eliminan los detalles que se encuentren vencidos y en estado de 'por retirar'
    sql_query = """
        DELETE FROM
            Detalle_solicitud
                WHERE datediff(fecha_vencimiento,%s) <= -1
                AND estado = 1
     """
    cursor.execute(sql_query, (fecha_actual,))

    # Se eliminan los encabezados de solicitud que no presenten ningún detalle
    sql_query = """
        DELETE FROM
            Solicitud
                WHERE (SELECT COUNT(*)
                        FROM Detalle_solicitud
                            WHERE id_solicitud = Solicitud.id) = 0
     """
    cursor.execute(sql_query)

# Función para revisar solicitudes atrasadas y realizar sanciones de forma automática
# Revisión a las 18:30 todos los días


def revisar_solicitudes_atrasadas():
    fecha_actual = datetime.now().replace(microsecond=0)
    sql_query = """
        SELECT Detalle_solicitud.*,Solicitud.rut_alumno,Usuario.email AS email_usuario,CONCAT(Usuario.nombres,' ',Usuario.apellidos) AS nombre_usuario
            FROM Detalle_solicitud,Solicitud,Usuario
                WHERE Detalle_solicitud.id_solicitud = Solicitud.id
                AND Solicitud.rut_alumno = Usuario.rut
                AND (Detalle_solicitud.estado = 2 OR Detalle_solicitud.estado = 3)
                AND datediff(Detalle_solicitud.fecha_termino,%s) <= 0
    """
    cursor.execute(sql_query, (fecha_actual,))
    lista_detalles_con_atraso = cursor.fetchall()

    # Diccionario para almacenar personas que recibirán correo por sanción nueva
    # La llave corresponde al RUT y se almacena una tupla (nombre_usuario,email_usuario) para posteriormente enviar los correos
    usuarios_sancionados = {}

    for detalle_solicitud in lista_detalles_con_atraso:
        # Se verifica si se encuentra registrada una sanción
        # En caso de que se encuentre registrada, se aumenta su multa
        # En caso contrario, se registra una nueva sanción

        sql_query = """
            SELECT *
                FROM Sanciones
                    WHERE rut_alumno = %s
                    AND activa = 1
        """
        cursor.execute(sql_query, (detalle_solicitud["rut_alumno"],))
        sancion = cursor.fetchone()

        if sancion:
            sql_query = """
                UPDATE Sanciones
                    SET cantidad_dias = cantidad_dias + 5,fecha_actualizacion = %s
                        WHERE id = %s
            """
            cursor.execute(sql_query, (fecha_actual, sancion["id"]))
        else:
            sql_query = """
                SELECT id,cantidad_dias
                    FROM Sanciones
                        WHERE rut_alumno = %s
                        AND activa = 0
            """
            cursor.execute(sql_query, (detalle_solicitud["rut_alumno"],))
            sancion_inactiva = cursor.fetchone()

            if sancion_inactiva:
                # +5 días de la sanción actual
                cantidad_dias = sancion_inactiva["cantidad_dias"] + 5
                # Se elimina la sanción inactiva, y se añade el tiempo restante a la nueva
                # sanción a crear
                sql_query = """
                    DELETE FROM
                        Sanciones
                            WHERE id = %s
                """
                cursor.execute(sql_query, (sancion_inactiva["id"],))
            else:
                cantidad_dias = 5

            sql_query = """
                INSERT INTO Sanciones (rut_alumno,cantidad_dias,activa,fecha_registro,fecha_actualizacion)
                    VALUES (%s,%s,1,%s,%s)
            """
            cursor.execute(
                sql_query, (detalle_solicitud["rut_alumno"], cantidad_dias, fecha_actual, fecha_actual))

            # En caso de que no se haya agregado el usuario al diccionario de sancionados, se agrega
            if detalle_solicitud["rut_alumno"] not in usuarios_sancionados.keys():
                usuarios_sancionados[detalle_solicitud["rut_alumno"]] = (
                    detalle_solicitud["nombre_usuario"], detalle_solicitud["email_usuario"])

        # Se modifica el estado de la sanción, en caso de que esté 'en posesión'
        if detalle_solicitud["estado"] == 2:
            sql_query = """
                UPDATE Detalle_solicitud
                    SET estado = 3
                        WHERE id = %s
            """
            cursor.execute(sql_query, (detalle_solicitud["id"],))

        # Se activa la sanción en el registro de la tabla de Detalle de solicitud
        if detalle_solicitud["sancion_activa"] != 1:
            sql_query = """
                UPDATE Detalle_solicitud
                    SET sancion_activa = 1
                        WHERE id = %s
            """
            cursor.execute(sql_query, (detalle_solicitud["id"],))

    # Se envían los correos a los usuarios que han recibido una nueva sanción
    for rut_usuario in usuarios_sancionados.keys():
        direccion_template = os.path.normpath(os.path.join(os.getcwd(
        ), "app/templates/vistas_gestion_solicitudes_prestamos/templates_mail/notificacion_sancion.html"))
        archivo_html = open(direccion_template, encoding="utf-8").read()

        # Se reemplazan los datos correspondientes en el archivo html
        nombre_usuario = usuarios_sancionados[rut_usuario][0]
        correo_usuario = usuarios_sancionados[rut_usuario][1]
        archivo_html = archivo_html.replace(
            "%nombre_usuario%", str(nombre_usuario))
        enviar_correo_notificacion(
            archivo_html, "[LabEIT] Notificación de sanción", correo_usuario)


def descontar_dias_sanciones():
    # Se descuentan los días de sanción de las sanciones inactivas
    sql_query = """
        UPDATE Sanciones
            SET cantidad_dias = cantidad_dias - 1
                WHERE activa = 0
    """
    cursor.execute(sql_query)

    # Se elimina el registro en caso de alcanzar 0 días
    sql_query = """
        DELETE FROM Sanciones
            WHERE cantidad_dias <= 0
    """
    cursor.execute(sql_query)

def revisar_18_30():
    # Eliminación de solicitudes vencidas
    eliminar_detalles_vencidos()

    # Revisión de solicitudes atrasadas y sanciones
    revisar_solicitudes_atrasadas()

    # Se descuentan los días de sanciones de las sanciones inactivas
    descontar_dias_sanciones()

if __name__ == "__main__":
    # Se ejecutan las funciones establecidas para las 18:30 (crontab)
    revisar_18_30()
    # Se cierra la conexión con la base de datos
    cursor.close()
    db.close()
