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

    for prestamo in lista_prestamos:
        delta_dias = fecha_actual - prestamo["fecha_termino"]

        # Si existe uno o más días de atraso según la fecha de término, se registra la sanción.
        if delta_dias.days >= 1:
            # Se obtienen los datos del usuario registrado en el préstamo
            sql_query = """
                SELECT Usuario.nombres,Usuario.email,Usuario.rut
                    FROM Usuario,Solicitud
                        WHERE Solicitud.rut_alumno = Usuario.rut
                        AND Solicitud.id = %s
            """
            cursor.execute(sql_query,(prestamo["id_solicitud"],))
            datos_usuario = cursor.fetchone()

            # Se registra la sanción
            sql_query = """
                INSERT INTO Sanciones (rut_alumno,cantidad_dias,fecha_inicio,activa)
                    VALUES (%s,%s,%s,%s)
            """

            dias_sancion = 2*delta_dias.days
            cursor.execute(sql_query,(prestamo["rut_alumno"],dias_sancion,str(datetime.now()),1))

            # Se modifica el estado del detalle de solicitud correspondiente
            sql_query = """
                UPDATE Detalle_solicitud
                    SET estado = 3,fecha_sancion = %s
                        WHERE id = %s
            """
            cursor.execute(sql_query,(prestamo["id"],datetime.now().date()))

            # Se notifica al usuario vía correo electrónico sobre la sanción
            # Se abre el template HTML correspondiente al rechazo de solicitud
            direccion_template = os.path.normpath(os.path.join(os.getcwd(), "app/templates/vistas_gestion_solicitudes_prestamos/templates_mail/informe_sancion.html"))
            archivo_html = open(direccion_template,encoding="utf-8").read()

            # Se reemplazan los datos correspondientes en el archivo html
            archivo_html = archivo_html.replace("%id_solicitud%",str(prestamo["id_solicitud"]))
            archivo_html = archivo_html.replace("%id_detalle%",str(prestamo["id"]))
            archivo_html = archivo_html.replace("%equipo_prestado%",prestamo["marca"]+" "+prestamo["modelo"])
            archivo_html = archivo_html.replace("%codigo_equipo%",str(prestamo["codigo_equipo"]))
            archivo_html = archivo_html.replace("%codigo_sufijo%",str(prestamo["codigo_sufijo_equipo"]))
            archivo_html = archivo_html.replace("%fecha_inicio_prestamo%",str(prestamo["fecha_inicio"]))
            archivo_html = archivo_html.replace("%fecha_termino_prestamo%",str(prestamo["fecha_termino"]))
            archivo_html = archivo_html.replace("%dias_sancion%",str(dias_sancion))

            enviar_correo_notificacion(archivo_html,datos_usuario["email"],"Alerta de sanción",datos_usuario["email"])

    # Se revisan las solicitudes que ya presentaban atrasos ...

#sched = APScheduler()
#sched.add_job(id="revisar_atrasos_prestamos",func=revisar_atrasos_prestamos,trigger='interval',seconds=30)
#sched.start()
# ============================================================================

# Define the WSGI application object
app = Flask(__name__)

# Blueprints (Routes)
from app.routes.rutas_seba import mod
from app.routes.rutas_pablo import mod
from app.routes.rutas_victor import mod
from app.routes.rutas_nico import mod
from app.routes.rutas_lorenzo import mod
from app.routes.rutas_cony import mod
app.register_blueprint(routes.rutas_seba.mod)
app.register_blueprint(routes.rutas_pablo.mod)
app.register_blueprint(routes.rutas_victor.mod)
app.register_blueprint(routes.rutas_nico.mod)
app.register_blueprint(routes.rutas_lorenzo.mod)
app.register_blueprint(routes.rutas_cony.mod)
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

# --------- Functiones útiles ------------------------------------------------

def allowed_file(filename): # Función para determinar si la extensión del archivo corresponde a una que esté permitida.
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# -------------------------------------------------------------------------------------------
