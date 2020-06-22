from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify
from werkzeug.utils import secure_filename
import mysql.connector
import bcrypt
import time
from datetime import datetime,timedelta
import os
import json,requests

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
