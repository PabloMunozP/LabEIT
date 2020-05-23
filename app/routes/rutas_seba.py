from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify
from config import db,cursor
import os,time,bcrypt,random
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment

def redirect_url(default='index'): # Redireccionamiento desde donde vino la request
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

mod = Blueprint("rutas_seba",__name__)

# Vista principal de la plataforma.
# En caso de estar autenticado, redirecciona dentro del sistema.
# En caso contrario, se mantiene en el login.
@mod.route("/",methods=["GET"])
def principal():
    if "usuario" not in session.keys():
        return render_template("/vistas_exteriores/login.html")
    else:
        return "Autenticado"

# Luego de ingresar los datos en el formulario del login, se reciben para la autenticación.
@mod.route("/iniciar_sesion",methods=["POST"])
def iniciar_sesion():
    datos_usuario = request.form.to_dict() # Se obtienen los datos del formulario

    # Se codifica la password ingresada en el formulario para comparación de hash
    datos_usuario["password"] = datos_usuario["password"].encode(encoding="UTF-8")

    # Se obtienen los datos del colaborador (contraseña --> hash de contraseña)
    sql_query = """
        SELECT rut,id_credencial,email,contraseña
            FROM Usuario
                WHERE rut = '%s'
    """ % (datos_usuario["rut"])
    cursor.execute(sql_query)
    # Se obtienen los datos asociados al rut ingresado en el formulario
    datos_usuario_registrado = cursor.fetchone()

    # Si no se obtiene un registro, entonces el rut no se encuentra registrado en el sistema
    if datos_usuario_registrado is None:
        flash("credenciales-invalidas") # Se notifica al front-end acerca del error para alertar al usuario
        return redirect(url_for("rutas_seba.principal"))

    return "Cuenta existente"

# Vista para recuperación de contraseña.
@mod.route("/recuperacion_password",methods=["GET"])
def recuperacion_password():
    return render_template("/vistas_exteriores/recuperacion_password.html")

@mod.route("/enviar_recuperacion_password",methods=["POST"])
def enviar_recuperacion_password():
    # Se obtienen los datos del formulario
    datos_recuperacion = request.form.to_dict()
    datos_recuperacion["identificacion_usuario"] = db.converter.escape(datos_recuperacion["identificacion_usuario"])

    # Se revisa si el RUT o correo coincide con el registro de usuarios
    sql_query = """
        SELECT nombres,email
            FROM Usuario
                WHERE rut = '%s'
                OR email = '%s'
    """ % (datos_recuperacion["identificacion_usuario"],datos_recuperacion["identificacion_usuario"])
    cursor.execute(sql_query)
    datos_usuario = cursor.fetchone()

    # Si el correo o el rut no se encuentran registrados, se alerta al usuario
    if datos_usuario is None:
        flash("recuperacion-invalida") # Se notifica al front-end acerca del error para alertar al usuario
        return redirect(url_for("rutas_seba.recuperacion_password"))

    # En caso de existir registro, se envía el correo de recuperación y se alerta al usuario

    # Se abre el template HTML correspondiente al restablecimiento de contraseña
    direccion_template = os.path.normpath(os.path.join(os.getcwd(), "app/templates/vistas_exteriores/recuperacion_password_mail.html"))
    html_restablecimiento = open(direccion_template,encoding="utf-8").read()

    # Se crea el mensaje
    correo = MIMEText(html_restablecimiento,"html")
    correo.set_charset("utf-8")
    correo["From"] = "labeit.udp@gmail.com"
    correo["To"] = datos_usuario["email"]
    correo["Subject"] = "Prueba - Sistema LabEIT UDP"

    try:
        server = smtplib.SMTP("smtp.gmail.com",587)
        server.starttls()
        server.login("labeit.udp@gmail.com","LabEIT_UDP_2020")
        str_correo = correo.as_string()
        server.sendmail("labeit.udp@gmail.com",datos_usuario["email"],str_correo)
        server.close()

        return "OK"

    except Exception as e:
        return str(e)

@mod.route("/recuperacion_mail_html",methods=["GET"])
def recuperacion_mail_html():
    return render_template("/vistas_exteriores/recuperacion_password_mail.html")
