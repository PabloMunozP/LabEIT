from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify
from config import db,cursor
import os,time,bcrypt,random
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment
from uuid import uuid4 # Token

mod = Blueprint("rutas_seba",__name__)

def redirect_url(default='index'): # Redireccionamiento desde donde vino la request
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

@mod.route("/crear",methods=["GET"])
def crear_usuario():
    pass_ = "labeit2020"
    hashpass = bcrypt.hashpw(pass_.encode(encoding="UTF-8"), bcrypt.gensalt())
    sql_query = """
        INSERT INTO Usuario (rut,nombres,apellidos,contraseña)
            VALUES (%s,%s,%s,%s)
    """
    cursor.execute(sql_query,("19889608K","Sebastián Ignacio","Toro Severino",hashpass.decode("UTF-8")))

    return redirect(redirect_url())

# Vista principal de la plataforma.
# En caso de estar autenticado, redirecciona dentro del sistema.
# En caso contrario, se mantiene en el login.
@mod.route("/",methods=["GET"])
def principal():
    if "usuario" not in session.keys():
        return render_template("/vistas_exteriores/login.html")
    else:
        return redirect('/perfil')

# Luego de ingresar los datos en el formulario del login, se reciben para la autenticación.
@mod.route("/iniciar_sesion",methods=["POST"])
def iniciar_sesion():
    datos_solicitante = request.form.to_dict() # Se obtienen los datos del formulario
    datos_solicitante["rut"] = datos_solicitante["rut"]
    datos_solicitante["password"] = datos_solicitante["password"]

    # Se obtienen los datos del colaborador (contraseña --> hash de contraseña)
    sql_query = """
        SELECT rut,nombres,apellidos,id_credencial,email,contraseña
            FROM Usuario
                WHERE rut = %s
    """
    cursor.execute(sql_query,(datos_solicitante["rut"],))
    # Se obtienen los datos asociados al rut ingresado en el formulario
    datos_usuario_registrado = cursor.fetchone()

    # Si no se obtiene un registro, entonces el rut no se encuentra registrado en el sistema
    if datos_usuario_registrado is None:
        flash("credenciales-invalidas") # Se notifica al front-end acerca del error para alertar al usuario
        return redirect(url_for("rutas_seba.principal"))

    # En caso de que la cuenta exista, se comprueban las contraseñas
    # Se codifica la password ingresada en el formulario para comparación de hash
    datos_solicitante["password"] = datos_solicitante["password"].encode(encoding="UTF-8")

    # Si las contraseñas no coinciden, entonces se devuelve al login y se notifica el error
    if not bcrypt.checkpw(datos_solicitante["password"],datos_usuario_registrado["contraseña"].encode(encoding="UTF-8")):
        flash("credenciales-invalidas") # Se notifica al front-end acerca del error para alertar al usuario
        return redirect(url_for("rutas_seba.principal"))

    # En caso de que se compruebe la validez de la contraseña, se crea la sesión
    # Adicionalmente, se redirecciona al perfil de usuario
    session["usuario"] = {} # Creación de sesión para usuario
    for atributo in datos_usuario_registrado.keys():
        session["usuario"][str(atributo)] = datos_usuario_registrado[str(atributo)]

    # Se verifica si el usuario presenta sanciones
    sql_query = """
        SELECT *
            FROM Sanciones
                WHERE rut_alumno = %s
                AND activa = 1
    """
    cursor.execute(sql_query,(session["usuario"]["rut"],))
    sancion_usuario = cursor.fetchone()

    if sancion_usuario is not None:
        session["usuario"]["sancionado"] = True
    else: # Si no se recibe nada de la consulta, no tiene sanciones
        session["usuario"]["sancionado"] = False

    return redirect('/perfil')

# Vista para recuperación de contraseña.
@mod.route("/recuperacion_password",methods=["GET"])
def recuperacion_password():
    return render_template("/vistas_exteriores/recuperacion_password.html")

@mod.route("/enviar_recuperacion_password",methods=["POST"])
def enviar_recuperacion_password():

    # Se obtienen los datos del formulario
    datos_recuperacion = request.form.to_dict()
    datos_recuperacion["identificacion_usuario"] = datos_recuperacion["identificacion_usuario"]

    # Se revisa si el RUT o correo coincide con el registro de usuarios
    sql_query = """
        SELECT rut,nombres,email
            FROM Usuario
                WHERE rut = %s
                OR email = %s
    """
    cursor.execute(sql_query,(datos_recuperacion["identificacion_usuario"],datos_recuperacion["identificacion_usuario"]))
    datos_usuario = cursor.fetchone()

    # Si el correo o el rut no se encuentran registrados, se alerta al usuario
    if datos_usuario is None:
        flash("recuperacion-invalida") # Se notifica al front-end acerca del error para alertar al usuario
        return redirect(url_for("rutas_seba.recuperacion_password"))

    # En caso de existir registro, se envía el correo de recuperación y se alerta al usuario

    # Se abre el template HTML correspondiente al restablecimiento de contraseña
    direccion_template = os.path.normpath(os.path.join(os.getcwd(), "app/templates/vistas_exteriores/recuperacion_password_mail.html"))
    html_restablecimiento = open(direccion_template,encoding="utf-8").read()

    # Se crea el token único para restablecimiento de contraseña
    token = str(uuid4())

    # Se eliminan los registros de token asociados al rut del usuario en caso de existir
    sql_query = """
        DELETE FROM Token_recuperacion_password
            WHERE rut_usuario = %s
    """
    cursor.execute(sql_query,(datos_usuario["rut"],))

    # Se reemplazan los datos del usuario en el template a enviar vía correo
    html_restablecimiento = html_restablecimiento.replace("%nombre_usuario%",datos_usuario["nombres"])
    html_restablecimiento = html_restablecimiento.replace("%codigo_restablecimiento%",str(random.randint(0,1000)))
    html_restablecimiento = html_restablecimiento.replace("%token_restablecimiento%",token)

    # Se crea el mensaje
    correo = MIMEText(html_restablecimiento,"html")
    correo.set_charset("utf-8")
    correo["From"] = "labeit.udp@gmail.com"
    correo["To"] = datos_usuario["email"]
    correo["Subject"] = "Recuperación de contraseña - LabEIT UDP"

    try:
        server = smtplib.SMTP("smtp.gmail.com",587)
        server.starttls()
        server.login("labeit.udp@gmail.com","LabEIT_UDP_2020")
        str_correo = correo.as_string()
        server.sendmail("labeit.udp@gmail.com",datos_usuario["email"],str_correo)
        server.close()
        # Se registra el token en la base de datos según el RUT del usuario
        sql_query = """
            INSERT INTO Token_recuperacion_password
                (token,rut_usuario)
                    VALUES (%s,%s)
        """
        cursor.execute(sql_query,(str(token),datos_usuario["rut"]))
        flash("correo-recuperacion-exito") # Notificación de éxito al enviar el correo

    except Exception as e:
        print(e)
        flash("correo-recuperacion-fallido") # Notificación de fallo al enviar el correo

    return redirect(url_for("rutas_seba.recuperacion_password"))

# Se redirecciona al formulario con el token respectivo al recuperar contraseña
@mod.route("/restablecer_password/<string:token>",methods=["GET"])
def restablecer_password(token):

    # Se verifica si el token se encuentra registrado
    # En caso de que esté registrado, se permite el acceso al formulario
    # En caso contrario, se redirecciona a la sección de recuperar contraseña

    sql_query = """
        SELECT token_id,rut_usuario
            FROM Token_recuperacion_password
                WHERE token = %s
    """
    cursor.execute(sql_query,(token,))
    registro_token = cursor.fetchone()

    # En caso de que el token sea inválido, se redirecciona a la sección de recuperación de contraseña
    if registro_token is None:
        return redirect(url_for("rutas_seba.recuperacion_password"))

    # Se obtiene el nombre del usuario
    sql_query = """
        SELECT nombres,apellidos
            FROM Usuario
                WHERE rut = %s
    """
    cursor.execute(sql_query,(registro_token["rut_usuario"],))
    registro_nombre_usuario = cursor.fetchone()

    if registro_nombre_usuario is not None:
        registro_token["nombres_usuario"] = registro_nombre_usuario["nombres"]
        registro_token["apellidos_usuario"] = registro_nombre_usuario["apellidos"]
    else:
        registro_token["nombres_usuario"] = ""
        registro_token["apellidos_usuario"] = ""

    return render_template("/vistas_exteriores/formulario_restablecer_password.html",
        registro_token = registro_token)

@mod.route("/recuperacion/modificar_password",methods=["POST"])
def modificar_password_recuperacion():
    datos_formulario = request.form.to_dict()

    # Se obtiene la identificación del usuario mediante el ID de token
    sql_query = """
        SELECT rut_usuario
            FROM Token_recuperacion_password
                WHERE token_id = %s
    """
    cursor.execute(sql_query,(int(datos_formulario["token_id"]),))
    datos_usuario = cursor.fetchone()

    # Si se ha obtenido un registro, se obtiene el rut
    if datos_usuario is not None:
        rut_usuario = datos_usuario["rut_usuario"]
    else:
        # No existe un rut de usuario asociado al token (posible error)
        # Se notifica al usuario y se redirecciona
        flash("error-id-token")
        return redirect(url_for("rutas_seba.principal"))

    # ------------------------------------ El registro de ID de token y usuario existe
    # Se comprueba que ambas contraseñas (nueva y confirmación) coincidan
    if datos_formulario["nueva_contraseña"] != datos_formulario["confirmacion_contraseña"]:
        # Si no coindicen, se notifica y se retorna al formulario desde donde vino
        flash("contraseñas-no-coinciden")
        return redirect(redirect_url())

    # Si coindicen, se elimina la confirmación
    del datos_formulario["confirmacion_contraseña"]

    # Se realiza la encriptación de la nueva contraseña para guardar en base de datos
    hashpass = bcrypt.hashpw(datos_formulario["nueva_contraseña"].encode(encoding="UTF-8"), bcrypt.gensalt())

    # Se almacena la nueva contraseña en la base de datos
    sql_query = """
        UPDATE Usuario
            SET contraseña = %s
                WHERE rut = %s
    """
    cursor.execute(sql_query,(hashpass.decode("UTF-8"),rut_usuario))

    # Se elimina el token generado de la base de datos
    sql_query = """
        DELETE FROM Token_recuperacion_password
            WHERE token_id = %s
    """
    cursor.execute(sql_query,(int(datos_formulario["token_id"]),))

    flash("contraseña-actualizada") # Se notifica el éxito al modificar la contraseña
    return redirect(url_for("rutas_seba.principal")) # Se redirecciona al login

@mod.route("/cerrar_sesion",methods=["GET"])
def cerrar_sesion():
    if "usuario" not in session.keys():
        return redirect(redirect_url())

    # Se elimina al usuario de la sesión
    del session["usuario"]

    # Se redirecciona al login una vez eliminada la sesión de usuario
    return redirect("/")


# ================================== GESTIÓN DE SOLICITUDES DE PRÉSTAMOS
@mod.route("/gestion_solicitudes_prestamos",methods=["GET"])
def gestion_solicitudes_prestamos():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3: # El usuario debe ser un administrador (Credencial = 3)
        return redirect("/")

    return render_template("/vistas_gestion_solicitudes_prestamos/gestion_solicitudes.html")

@mod.route("/gestion_solicitudes_prestamos/detalle_solicitud/<string:id_detalle_solicitud>",methods=["GET"])
def detalle_solicitud(id_detalle_solicitud):
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3: # El usuario debe ser un administrador (Credencial = 3)
        return redirect("/")

    return render_template("/vistas_gestion_solicitudes_prestamos/detalle_solicitud.html")
