from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify,abort
from werkzeug.utils import secure_filename
from config import db,cursor
import bcrypt
import time
from datetime import datetime,timedelta
import os
import json,requests,smtplib
from flask_apscheduler import APScheduler
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def enviar_correo_notificacion(archivo,str_para,str_asunto,correo_usuario): # Envío de notificaciones vía correo electrónico
    # Se crea el mensaje
    correo = MIMEText(archivo,"html")
    correo.set_charset("utf-8")
    correo["From"] = "labeit.udp@gmail.com"
    correo["To"] = correo_usuario
    correo["Subject"] = str_asunto

    try:
        server = smtplib.SMTP("smtp.gmail.com",587)
        server.starttls()
        server.login("labeit.udp@gmail.com","LabEIT_UDP_2020")
        str_correo = correo.as_string()
        server.sendmail("labeit.udp@gmail.com",correo_usuario,str_correo)
        server.close()

    except Exception as e:
        print(e)

# ============= Funciones programadas ======================

# Función para eliminar mensajes administrativos que cumplan con la fecha de eliminación indicada
# Revisión a las 23:59 todos los días
def revisar_mensajes_administrativos():
    fecha_actual = datetime.now().replace(microsecond=0)
    sql_query = """
        DELETE FROM
            Mensaje_administrativo
                WHERE datediff(fecha_eliminacion,%s) <= 0
    """
    cursor.execute(sql_query,(fecha_actual,))

# Función para eliminar tokens de passwords que hayan vencido (máx 1 día para usarlo)
# Revisión a las 23:59 todos los días
def revisar_tokens_password():
    fecha_actual = datetime.now().replace(microsecond=0)

    sql_query = """
        DELETE FROM
            Token_recuperacion_password
                WHERE datediff(fecha_registro,%s) <= -1
    """
    cursor.execute(sql_query,(fecha_actual,))

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
    cursor.execute(sql_query,(fecha_actual,))

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
    cursor.execute(sql_query,(fecha_actual,))

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
    cursor.execute(sql_query,(fecha_actual,))
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
        cursor.execute(sql_query,(detalle_solicitud["rut_alumno"],))
        sancion = cursor.fetchone()

        if sancion:
            sql_query = """
                UPDATE Sanciones
                    SET cantidad_dias = cantidad_dias + 5,fecha_actualizacion = %s
                        WHERE id = %s
            """
            cursor.execute(sql_query,(fecha_actual,sancion["id"]))
        else:
            sql_query = """
                SELECT id,cantidad_dias
                    FROM Sanciones
                        WHERE rut_alumno = %s
                        AND activa = 0
            """
            cursor.execute(sql_query,(detalle_solicitud["rut_alumno"],))
            sancion_inactiva = cursor.fetchone()

            if sancion_inactiva:
                cantidad_dias = sancion_inactiva["cantidad_dias"] + 5 # +5 días de la sanción actual
                # Se elimina la sanción inactiva, y se añade el tiempo restante a la nueva
                # sanción a crear
                sql_query = """
                    DELETE FROM
                        Sanciones
                            WHERE id = %s
                """
                cursor.execute(sql_query,(sancion_inactiva["id"],))
            else:
                cantidad_dias = 5

            sql_query = """
                INSERT INTO Sanciones (rut_alumno,cantidad_dias,activa,fecha_registro,fecha_actualizacion)
                    VALUES (%s,%s,1,%s,%s)
            """
            cursor.execute(sql_query,(detalle_solicitud["rut_alumno"],cantidad_dias,fecha_actual,fecha_actual))

            # En caso de que no se haya agregado el usuario al diccionario de sancionados, se agrega
            if detalle_solicitud["rut_alumno"] not in usuarios_sancionados.keys():
                usuarios_sancionados[detalle_solicitud["rut_alumno"]] = (detalle_solicitud["nombre_usuario"],detalle_solicitud["email_usuario"])

        # Se modifica el estado de la sanción, en caso de que esté 'en posesión'
        if detalle_solicitud["estado"] == 2:
            sql_query = """
                UPDATE Detalle_solicitud
                    SET estado = 3
                        WHERE id = %s
            """
            cursor.execute(sql_query,(detalle_solicitud["id"],))

        # Se activa la sanción en el registro de la tabla de Detalle de solicitud
        if detalle_solicitud["sancion_activa"] != 1:
            sql_query = """
                UPDATE Detalle_solicitud
                    SET sancion_activa = 1
                        WHERE id = %s
            """
            cursor.execute(sql_query,(detalle_solicitud["id"],))

    # Se envían los correos a los usuarios que han recibido una nueva sanción
    for rut_usuario in usuarios_sancionados.keys():
        direccion_template = os.path.normpath(os.path.join(os.getcwd(), "app/templates/vistas_gestion_solicitudes_prestamos/templates_mail/notificacion_sancion.html"))
        archivo_html = open(direccion_template,encoding="utf-8").read()

        # Se reemplazan los datos correspondientes en el archivo html
        nombre_usuario = usuarios_sancionados[rut_usuario][0]
        correo_usuario = usuarios_sancionados[rut_usuario][1]
        archivo_html = archivo_html.replace("%nombre_usuario%",str(nombre_usuario))
        enviar_correo_notificacion(archivo_html,str(correo_usuario),"[LabEIT] Notificación de sanción",correo_usuario)

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

def revisar_23_59():
    # Eliminación de mensajes administrativos
    revisar_mensajes_administrativos()

    # Eliminación de tokens de password
    revisar_tokens_password()

    # Revisar bloqueos de IPs
    revisar_bloqueos_ips()

def revisar_18_30():
    # Eliminación de solicitudes vencidas
    eliminar_detalles_vencidos()

    # Revisión de solicitudes atrasadas y sanciones
    revisar_solicitudes_atrasadas()

    # Se descuentan los días de sanciones de las sanciones inactivas
    descontar_dias_sanciones()

#sched = APScheduler()
#sched.add_job(id="revisar_23_59",func=revisar_23_59,trigger='cron',hour=23,minute=59)
#sched.add_job(id="revisar_18_30",func=revisar_18_30,trigger='cron',hour=18,minute=30)
#sched.start()
# ============================================================================

# Define the WSGI application object
app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Blueprints (Routes)
from app.routes.rutas_seba import mod
from app.routes.rutas_pablo import mod
from app.routes.rutas_perfil import mod
from app.routes.rutas_nico import mod
from app.routes.rutas_lorenzo import mod
from app.routes.rutas_cony import mod
from app.routes.rutas_aux import mod

app.register_blueprint(routes.rutas_seba.mod)
app.register_blueprint(routes.rutas_pablo.mod)
app.register_blueprint(routes.rutas_perfil.mod)
app.register_blueprint(routes.rutas_nico.mod)
app.register_blueprint(routes.rutas_lorenzo.mod)
app.register_blueprint(routes.rutas_cony.mod)
app.register_blueprint(routes.rutas_aux.mod)
# Configurations
app.config.from_object('config')

# Sample HTTP error handling
@app.errorhandler(404)
def not_found(error):
    return redirect("/")

@app.errorhandler(401)
def not_authorized(error):
    return render_template("/vistas_errores/401_externo.html"), 401

@app.errorhandler(405)
def method_not_allowed(error):
    return render_template("/vistas_errores/405_externo.html"), 405

@app.errorhandler(500)
def internal_server_error(error):
    return render_template("/vistas_errores/500_externo.html"), 500

# ------------------------------------------- TEMPLATE FILTERS
@app.template_filter('nl2br') # Permite cambiar el formato de los saltos de línea en textarea
def nl2br(s):
    s = s.strip()
    s = s.replace("\r","")
    return s.replace("\n", "<br/>")
@app.template_filter('underscore_espacio') # Permite reemplazar espacios por '_'
def underscore_espacio(s):
    return s.replace(" ","_")
@app.template_filter('formato_rut') # Agrega puntos y guión al RUT
def formato_rut(rut_entrada):
    # Transforma 123456789 => 12.345.678-9
    if len(rut_entrada) == 9:
        return ('{d[0]}{d[1]}.{d[2]}{d[3]}{d[4]}.{d[5]}{d[6]}{d[7]}-{d[8]}'.format(d = rut_entrada))
    elif len(rut_entrada) == 8: # 12345678 =>1.234.567-8
        return ('{d[0]}.{d[1]}{d[2]}{d[3]}.{d[4]}{d[5]}{d[6]}-{d[7]}'.format(d = rut_entrada))

    # Transforma 12.345.678-9 => 123456789
    elif len(rut_entrada) == 12:
        return ('{d[0]}{d[1]}{d[3]}{d[4]}{d[5]}{d[7]}{d[8]}{d[9]}{d[11]}'.format(d = rut_entrada))
    else:
        return 'Rut inválido'
# -------------------------------------------

# Timer para sesión activa (Máximo 2 hrs inactivas)
@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=30)

@app.after_request
def add_header(response):
    # response.cache_control.no_store = True
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# --------- Functiones útiles ------------------------------------------------

def allowed_file(filename): # Función para determinar si la extensión del archivo corresponde a una que esté permitida.
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# -------------------------------------------------------------------------------------------
