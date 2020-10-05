import os
import time
import bcrypt
from email import encoders
from config import db,cursor
import json,requests,smtplib
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from datetime import datetime,timedelta
from flask_apscheduler import APScheduler
from werkzeug.utils import secure_filename
from email.mime.multipart import MIMEMultipart
from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify,abort

def redirect_url(default='index'): # Redireccionamiento desde donde vino la request
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

# Define the WSGI application object
app = Flask(__name__)

# Se importan funciones desde /routines/sched_functions.py
from app.routines.sched_functions import revisar_18_30,revisar_23_59

# ========== Se inicializan las funciones con el objeto de APScheduler
sched = APScheduler()
sched.add_job(id="revisar_23_59",func=revisar_23_59,trigger='cron',hour=23,minute=59)
sched.add_job(id="revisar_18_30",func=revisar_18_30,trigger='cron',hour=18,minute=30)
sched.start()
# ============================================================================
# Blueprints (Routes)
from app.routes.rutas_modulos_documentacion import mod
from app.routes.rutas_gestion_usuarios import mod
from app.routes.rutas_perfil import mod
from app.routes.rutas_wifi import mod
from app.routes.rutas_gestion_inventario import mod
from app.routes.rutas_wishlist import mod
from app.routes.rutas_cony import mod
from app.routes.rutas_solicitud_circuito import mod
from app.routes.rutas_gestion_solicitudes import mod
from app.routes.rutas_login import mod
from app.routes.rutas_mensajes_administrativos import mod
from app.routes.rutas_estadisticas_solicitudes import mod

app.register_blueprint(routes.rutas_modulos_documentacion.mod)
app.register_blueprint(routes.rutas_gestion_usuarios.mod)
app.register_blueprint(routes.rutas_perfil.mod)
app.register_blueprint(routes.rutas_gestion_inventario.mod)
app.register_blueprint(routes.rutas_wifi.mod)
app.register_blueprint(routes.rutas_wishlist.mod)
app.register_blueprint(routes.rutas_cony.mod)
app.register_blueprint(routes.rutas_solicitud_circuito.mod)
app.register_blueprint(routes.rutas_gestion_solicitudes.mod)
app.register_blueprint(routes.rutas_login.mod)
app.register_blueprint(routes.rutas_mensajes_administrativos.mod)
app.register_blueprint(routes.rutas_estadisticas_solicitudes.mod)

# Configuraciones adicionales desde config.py
app.config.from_object('config')

# Controlador de errores HTTP
@app.errorhandler(404)
def not_found(error):
    return redirect("/")

@app.errorhandler(413)
def too_large_request(error):
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

# ------------------------------------------- Filtros Jinja2 para templates
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

# --------- Funciones útiles ------------------------------------------------
def allowed_file(filename): # Función para determinar si la extensión del archivo corresponde a una que esté permitida.
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
# -------------------------------------------------------------------------------------------
