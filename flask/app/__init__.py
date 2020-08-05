from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify
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

def enviar_correo_notificacion(archivo,str_para,str_asunto,correo_usuario): # Envío de correo (notificaciones de solicitudes de préstamo)
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

# ============= Configuraciones para funciones con timer ======================
#def verificar_fechas_vencimiento_solicitudes():
    # Función para verificar la fecha de vencimiento de una solicitud, una vez aprobada
    #print("verificar_fechas_vencimiento_solicitudes")

def revisar_atrasos_prestamos():
    # Se revisan los préstamos que presenten atrasos para realizar las sanciones.
    # En caso de presentar anteriormente un atraso activo, se suma a la sanción.
    sql_query = """
        SELECT Detalle_solicitud.*,Solicitud.rut_alumno,Equipo.marca,Equipo.modelo,Equipo.codigo AS codigo_equipo
            FROM Detalle_solicitud,Solicitud,Equipo
                WHERE Solicitud.id = Detalle_solicitud.id_solicitud
                AND Detalle_solicitud.id_equipo = Equipo.id
                AND Detalle_solicitud.estado = 2
    """
    cursor.execute(sql_query)
    lista_prestamos = cursor.fetchall()

    fecha_actual = datetime.now().date()

    #for prestamo in lista_prestamos:



            # Se notifica al usuario vía correo electrónico sobre la sanción
            #direccion_template = os.path.normpath(os.path.join(os.getcwd(), "app/templates/vistas_gestion_solicitudes_prestamos/templates_mail/informe_sancion.html"))
            #archivo_html = open(direccion_template,encoding="utf-8").read()

            # Se reemplazan los datos correspondientes en el archivo html
            #archivo_html = archivo_html.replace("%id_solicitud%",str(prestamo["id_solicitud"]))
            #archivo_html = archivo_html.replace("%id_detalle%",str(prestamo["id"]))
            #archivo_html = archivo_html.replace("%equipo_prestado%",prestamo["marca"]+" "+prestamo["modelo"])
            #archivo_html = archivo_html.replace("%codigo_equipo%",str(prestamo["codigo_equipo"]))
            #archivo_html = archivo_html.replace("%codigo_sufijo%",str(prestamo["codigo_sufijo_equipo"]))
            #archivo_html = archivo_html.replace("%fecha_inicio_prestamo%",str(prestamo["fecha_inicio"]))
            #archivo_html = archivo_html.replace("%fecha_termino_prestamo%",str(prestamo["fecha_termino"]))
            #archivo_html = archivo_html.replace("%dias_sancion%",str(dias_sancion))

            #enviar_correo_notificacion(archivo_html,datos_usuario["email"],"Alerta de sanción",datos_usuario["email"])

    # Se revisan las solicitudes que ya presentaban atrasos ...


def revisar_solicitudes_vencidas():
    # Se revisan las solicitudes que han sido aprobadas, pero que no se han retirado a tiempo.
    # En caso de que se cumpla la fecha de vencimiento de la solicitud, se elimina automáticamente.

    # Se obtiene la fecha actual según la aplicación
    fecha_actual = datetime.now().date()

    sql_query = """
        SELECT id,id_solicitud,fecha_vencimiento
            FROM Detalle_solicitud
                WHERE estado = 1
                AND fecha_vencimiento <= %s
    """
    cursor.execute(sql_query,(fecha_actual,))
    lista_detalles_solicitud = cursor.fetchall()

    for detalle_solicitud in lista_detalles_solicitud:
        # Se comprueba si se debe eliminar el encabezado de la solicitud,
        # en caso de que la solicitud sólo tenga un detalle.
        eliminar_encabezado = False

        sql_query = """
            SELECT COUNT(*) AS cantidad_detalles
                FROM Detalle_solicitud
                    WHERE id_solicitud = %s
        """
        cursor.execute(sql_query,(detalle_solicitud["id_solicitud"],))
        cantidad_detalles = cursor.fetchone()["cantidad_detalles"]

        if cantidad_detalles == 1:
            # Si la cantidad de detalles es 1, significa que sólo está el detalle vencido
            # Por lo tanto, además de eliminar el detalle de solicitud, se elimina el encabezado
            eliminar_encabezado = True

        # Se elimina el detalle de solicitud vencido
        sql_query = """
            DELETE FROM
                Detalle_solicitud
                    WHERE id = %s
        """
        cursor.execute(sql_query,(detalle_solicitud["id"],))

        # Se elimina el encabezado, según las condiciones
        if eliminar_encabezado:
            sql_query = """
                DELETE FROM
                    Solicitud
                        WHERE id = %s
            """
            cursor.execute(sql_query,(detalle_solicitud["id_solicitud"],))

#sched = APScheduler()
#sched.add_job(id="revisar_atrasos_prestamos",func=revisar_atrasos_prestamos,trigger='interval',seconds=10)
#sched.add_job(id="revisar_solicitudes_vencidas",func=revisar_solicitudes_vencidas,trigger='interval',seconds=60)
#sched.start()
# ============================================================================

# Define the WSGI application object
app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

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
    return render_template('/vistas_errores/404_externo.html'), 404

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
    return s.replace("\n", "<br />")
@app.template_filter('rem_com') # Permite reemplazar comillas simples (Error JS al pasar un input con '' a JS)
def rem_com(s):
    s = s.replace("'","\\'")
    s = s.replace('"','\\"')
    return s
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
    app.permanent_session_lifetime = timedelta(minutes=120)


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
