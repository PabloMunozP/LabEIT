import os,json,time,bcrypt
from uuid import uuid4  # Token
from datetime import datetime, timedelta
from app.utils.email_sender import enviar_correo_notificacion
from config import db, BASE_DIR, ALLOWED_EXTENSIONS, MAX_CONTENT_LENGTH
from flask import Flask, Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, send_file

mod = Blueprint("rutas_login", __name__)

def redirect_url(default='index'):  # Redireccionamiento desde donde vino la request
    return request.args.get('next') or \
        request.referrer or \
        url_for(default)

# Vista principal de la plataforma.
# En caso de estar autenticado, redirecciona dentro del sistema.
# En caso contrario, se mantiene en el login.
@mod.route("/", methods=["GET"])
def principal():
    # Se verifican las IPs bloqueadas
    sql_query = """
        SELECT COUNT(*) AS cantidad_bloqueos
            FROM Bloqueos_IP
                WHERE ip = %s
                AND activo = 1
    """
    #cursor.execute(sql_query, (request.remote_addr,))
    cursor = db.query(sql_query, (request.remote_addr,))
    registro_bloqueo_activo = bool(cursor.fetchone()["cantidad_bloqueos"])

    if registro_bloqueo_activo:
        return render_template("/vistas_errores/403_externo.html"), 403

    if "usuario" not in session.keys():
        # Se crea (en caso de no existir) la cantidad de intentos para ingresar
        if "intentos_login" not in session.keys():
            session["intentos_login"] = 10
        return render_template("/vistas_exteriores/login.html")
    else:
        return redirect('/perfil')

# Luego de ingresar los datos en el formulario del login, se reciben para la autenticación.


@mod.route("/iniciar_sesion", methods=["POST"])
def iniciar_sesion():
    # Se obtienen los datos del formulario
    datos_solicitante = request.form.to_dict()
    datos_solicitante["rut"] = datos_solicitante["rut"]
    datos_solicitante["password"] = datos_solicitante["password"]

    # Se obtienen los datos del colaborador (contraseña --> hash de contraseña)
    sql_query = """
        SELECT rut,nombres,apellidos,id_credencial,email,contraseña,activo
            FROM Usuario
                WHERE rut = %s
    """
    #cursor.execute(sql_query, (datos_solicitante["rut"],))
    cursor = db.query(sql_query, (datos_solicitante["rut"],))
    # Se obtienen los datos asociados al rut ingresado en el formulario
    datos_usuario_registrado = cursor.fetchone()

    # Si no se obtiene un registro, entonces el rut no se encuentra registrado en el sistema
    if datos_usuario_registrado is None:
        # Se notifica al front-end acerca del error para alertar al usuario
        flash("credenciales-invalidas")
        # Se descuenta el intento correspondiente
        session["intentos_login"] -= 1

        if session["intentos_login"] == 1:
            # Se notifica acerca del último intento
            flash("ultimo-intento-login")

        if session["intentos_login"] == 0:
            # Se registra el bloqueo en la base de datos
            fecha_bloqueo = datetime.now()
            sql_query = """
                INSERT INTO Bloqueos_IP (ip,fecha_bloqueo)
                    VALUES (%s,%s)
            """
            #cursor.execute(sql_query, (request.remote_addr, fecha_bloqueo))
            db.query(sql_query, (request.remote_addr, fecha_bloqueo))

            del session["intentos_login"]

        return redirect("/")

    # En caso de que la cuenta exista, se comprueban las contraseñas
    # Se codifica la password ingresada en el formulario para comparación de hash
    datos_solicitante["password"] = datos_solicitante["password"].encode(
        encoding="UTF-8")

    # Si las contraseñas no coinciden, entonces se devuelve al login y se notifica el error
    if not bcrypt.checkpw(datos_solicitante["password"], datos_usuario_registrado["contraseña"].encode(encoding="UTF-8")):
        # Se notifica al front-end acerca del error para alertar al usuario
        flash("credenciales-invalidas")
        # Se descuenta el intento correspondiente
        session["intentos_login"] -= 1

        if session["intentos_login"] == 1:
            # Se notifica acerca del último intento
            flash("ultimo-intento-login")

        if session["intentos_login"] == 0:
            # Se registra el bloqueo en la base de datos
            fecha_bloqueo = datetime.now()
            sql_query = """
                INSERT INTO Bloqueos_IP (ip,fecha_bloqueo)
                    VALUES (%s,%s)
            """
            #cursor.execute(sql_query, (request.remote_addr, fecha_bloqueo))
            db.query(sql_query, (request.remote_addr, fecha_bloqueo))

            del session["intentos_login"]

            # Se notifica el bloqueo de IP y el intento de acceso al correo del usuario
            # al que le pertenece la cuenta

            # Se obtienen los datos de la cuenta del usuario
            sql_query = """
                SELECT nombres,email
                    FROM Usuario
                        WHERE rut = %s
            """
            #cursor.execute(sql_query, (datos_solicitante["rut"],))
            cursor = db.query(sql_query, (datos_solicitante["rut"],))

            datos_usuario_cuenta = cursor.fetchone()

            if datos_usuario_cuenta is not None:
                # Se envía el correo al usuario
                direccion_template = os.path.normpath(os.path.join(os.getcwd(
                ), "app/templates/vistas_exteriores/intento_fuerza_bruta_login_mail.html"))
                archivo_html = open(direccion_template,
                                    encoding="utf-8").read()

                # Se reemplazan los datos
                archivo_html = archivo_html.replace(
                    "%nombre_usuario%", datos_usuario_cuenta["nombres"])
                archivo_html = archivo_html.replace(
                    "%request_ip%", request.remote_addr)

                fecha_intento_acceso = datetime.now().replace(
                    microsecond=0).strftime("%d-%m-%Y %H:%M:%S")
                archivo_html = archivo_html.replace(
                    "%fecha_intento_acceso%", fecha_intento_acceso)
                # Se envía el correo al usuario
                enviar_correo_notificacion(
                    archivo_html, "[LabEIT] Intento de inicio de sesión inusual", datos_usuario_cuenta["email"])

        return redirect("/")

    # Al autentificar al usuario, se comprueba que su cuenta se encuentre habilitada
    # En caso de que se encuentre deshabilitada, se redirecciona y notifica al usuario.

    if not datos_usuario_registrado["activo"]:
        flash("cuenta-inactiva")
        return redirect("/")

    # En caso de que se compruebe la validez de la contraseña, se crea la sesión
    # Adicionalmente, se redirecciona al perfil de usuario
    del datos_usuario_registrado["contraseña"]
    session["usuario"] = {}  # Creación de sesión para usuario
    for atributo in datos_usuario_registrado.keys():
        session["usuario"][str(
            atributo)] = datos_usuario_registrado[str(atributo)]

    # Se verifica si el usuario presenta sanciones
    sql_query = """
        SELECT *
            FROM Sanciones
                WHERE rut_alumno = %s
                AND activa = 1
    """
    #cursor.execute(sql_query, (session["usuario"]["rut"],))
    cursor = db.query(sql_query, (session["usuario"]["rut"],))

    sancion_usuario = cursor.fetchone()

    if sancion_usuario is not None:
        session["usuario"]["sancionado"] = True
    else:  # Si no se recibe nada de la consulta, no tiene sanciones
        session["usuario"]["sancionado"] = False

    # Se elimina el registro de los intentos de login
    del session["intentos_login"]

    return redirect('/perfil')

# Vista para recuperación de contraseña.


@mod.route("/recuperacion_password", methods=["GET"])
def recuperacion_password():
    if "usuario" in session.keys():
        return redirect("/")
    return render_template("/vistas_exteriores/recuperacion_password.html")


@mod.route("/enviar_recuperacion_password", methods=["POST"])
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
    #cursor.execute(
    #    sql_query, (datos_recuperacion["identificacion_usuario"], datos_recuperacion["identificacion_usuario"]))
    cursor = db.query(sql_query, (datos_recuperacion["identificacion_usuario"], datos_recuperacion["identificacion_usuario"]))

    datos_usuario = cursor.fetchone()

    # Si el correo o el rut no se encuentran registrados, se alerta al usuario
    if datos_usuario is None:
        flash("notificacion-recuperacion")
        return redirect("/recuperacion_password")

    # En caso de existir registro, se envía el correo de recuperación y se alerta al usuario

    # Se abre el template HTML correspondiente al restablecimiento de contraseña
    direccion_template = os.path.normpath(os.path.join(
        os.getcwd(), "app/templates/vistas_exteriores/recuperacion_password_mail.html"))
    archivo_html = open(direccion_template, encoding="utf-8").read()

    # Se crea el token único para restablecimiento de contraseña
    token = str(uuid4())

    # Se eliminan los registros de token asociados al rut del usuario en caso de existir
    sql_query = """
        DELETE FROM Token_recuperacion_password
            WHERE rut_usuario = %s
    """
    #cursor.execute(sql_query, (datos_usuario["rut"],))
    db.query(sql_query, (datos_usuario["rut"],))

    # Se reemplazan los datos del usuario en el template a enviar vía correo
    archivo_html = archivo_html.replace(
        "%nombre_usuario%", datos_usuario["nombres"])
    archivo_html = archivo_html.replace("%token_restablecimiento%", token)

    # Se agrega el token de recuperación a la base de datos
    fecha_actual = datetime.now().replace(microsecond=0)
    sql_query = """
        INSERT INTO Token_recuperacion_password
            (token,rut_usuario,fecha_registro)
                VALUES (%s,%s,%s)
    """
    #cursor.execute(sql_query, (str(token), datos_usuario["rut"], fecha_actual))
    db.query(sql_query, (str(token), datos_usuario["rut"], fecha_actual))

    # Se envía el correo electrónico al usuario solicitante
    enviar_correo_notificacion(
        archivo_html, "[LabEIT] Recuperación de contraseña", datos_usuario["email"])

    flash("notificacion-recuperacion")
    return redirect("/recuperacion_password")

# Se redirecciona al formulario con el token respectivo al recuperar contraseña


@mod.route("/restablecer_password/<string:token>", methods=["GET"])
def restablecer_password(token):

    # Se verifica si el token se encuentra registrado
    # En caso de que esté registrado, se permite el acceso al formulario
    # En caso contrario, se redirecciona a la sección de recuperar contraseña

    sql_query = """
        SELECT token_id,rut_usuario
            FROM Token_recuperacion_password
                WHERE token = %s
    """
    #cursor.execute(sql_query, (token,))
    cursor = db.query(sql_query, (token,))

    registro_token = cursor.fetchone()

    # En caso de que el token sea inválido, se redirecciona a la sección de recuperación de contraseña
    if registro_token is None:
        return redirect("/recuperacion_password")

    # Se obtiene el nombre del usuario
    sql_query = """
        SELECT nombres,apellidos
            FROM Usuario
                WHERE rut = %s
    """
    #cursor.execute(sql_query, (registro_token["rut_usuario"],))
    cursor = db.query(sql_query, (registro_token["rut_usuario"],))

    registro_nombre_usuario = cursor.fetchone()

    if registro_nombre_usuario is not None:
        registro_token["nombres_usuario"] = registro_nombre_usuario["nombres"]
        registro_token["apellidos_usuario"] = registro_nombre_usuario["apellidos"]
    else:
        registro_token["nombres_usuario"] = ""
        registro_token["apellidos_usuario"] = ""

    return render_template("/vistas_exteriores/formulario_restablecer_password.html",
                           registro_token=registro_token)


@mod.route("/recuperacion/modificar_password", methods=["POST"])
def modificar_password_recuperacion():
    datos_formulario = request.form.to_dict()

    # Se obtiene la identificación del usuario mediante el ID de token
    sql_query = """
        SELECT rut_usuario
            FROM Token_recuperacion_password
                WHERE token_id = %s
    """
    #cursor.execute(sql_query, (int(datos_formulario["token_id"]),))
    cursor = db.query(sql_query, (int(datos_formulario["token_id"]),))

    datos_usuario = cursor.fetchone()

    # Si se ha obtenido un registro, se obtiene el rut
    if datos_usuario is not None:
        rut_usuario = datos_usuario["rut_usuario"]
    else:
        # No existe un rut de usuario asociado al token (posible error)
        # Se notifica al usuario y se redirecciona
        flash("error-id-token")
        return redirect("/")

    # ------------------------------------ El registro de ID de token y usuario existe
    # Se comprueba que ambas contraseñas (nueva y confirmación) coincidan
    if datos_formulario["nueva_contraseña"] != datos_formulario["confirmacion_contraseña"]:
        # Si no coindicen, se notifica y se retorna al formulario desde donde vino
        flash("contraseñas-no-coinciden")
        return redirect(redirect_url())

    # Si coindicen, se elimina la confirmación
    del datos_formulario["confirmacion_contraseña"]

    # Se realiza la encriptación de la nueva contraseña para guardar en base de datos
    hashpass = bcrypt.hashpw(datos_formulario["nueva_contraseña"].encode(
        encoding="UTF-8"), bcrypt.gensalt())

    # Se almacena la nueva contraseña en la base de datos
    sql_query = """
        UPDATE Usuario
            SET contraseña = %s
                WHERE rut = %s
    """
    #cursor.execute(sql_query, (hashpass.decode("UTF-8"), rut_usuario))
    db.query(sql_query, (hashpass.decode("UTF-8"), rut_usuario))

    # Se elimina el token generado de la base de datos
    sql_query = """
        DELETE FROM Token_recuperacion_password
            WHERE token_id = %s
    """
    #cursor.execute(sql_query, (int(datos_formulario["token_id"]),))
    db.query(sql_query, (int(datos_formulario["token_id"]),))

    # Se notifica el éxito al modificar la contraseña
    flash("contraseña-actualizada")
    return redirect("/")  # Se redirecciona al login


@mod.route("/cerrar_sesion", methods=["GET"])
def cerrar_sesion():
    if "usuario" not in session.keys():
        return redirect(redirect_url())

    # Se elimina al usuario de la sesión
    del session["usuario"]
    # Se elimina el carro de pedidos en caso de existir
    if "carro_pedidos" in session.keys():
        del session["carro_pedidos"]
    if "carro_pedidos_circuito" in session.keys():
        del session["carro_pedidos_circuito"]

    # Se redirecciona al login una vez eliminada la sesión de usuario
    return redirect("/")
