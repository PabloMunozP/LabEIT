import timeago
from jinja2 import Environment
from datetime import datetime,timedelta
from openpyxl.styles.borders import Border, Side, BORDER_THIN
from config import db,cursor,BASE_DIR,ALLOWED_EXTENSIONS,MAX_CONTENT_LENGTH
from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify,send_file

mod = Blueprint("rutas_mensajes_administrativos",__name__)

def redirect_url(default='index'): # Redireccionamiento desde donde vino la request
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

# MENSAJES ADMINISTRATIVOS
@mod.route("/mensajes_administrativos",methods=["GET"])
def mensajes_administrativos():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3: # El usuario debe ser un administrador (Credencial = 3)
        return redirect("/")

    # Se obtiene la lista de mensajes administrativos registrados
    sql_query = """
        SELECT * FROM Mensaje_administrativo
            ORDER BY fecha_registro DESC
    """
    cursor.execute(sql_query)
    lista_mensajes_administrativos = cursor.fetchall()

    # Se obtiene el timeago para cada una de las fechas de registro de cada mensaje
    for mensaje_administrativo in lista_mensajes_administrativos:
        mensaje_administrativo["timeago_mensaje"] = timeago.format(mensaje_administrativo["fecha_registro"], datetime.now(), 'es')
        mensaje_administrativo["fecha_eliminacion"] = mensaje_administrativo["fecha_eliminacion"].date()

    return render_template("/mensajes_administrativos/mensajes_admin.html",
        lista_mensajes_administrativos=lista_mensajes_administrativos)

@mod.route("/registrar_mensaje_administrativo",methods=["POST"])
def registrar_mensaje_administrativo():
    datos_formulario = request.form.to_dict()

    # Se verifica si existe fecha de eliminación
    if not len(datos_formulario["fecha_eliminacion"]):
        # No se especificó una fecha de eliminación
        datos_formulario["fecha_eliminacion"] = str(datetime.now().date())

    # Se agrega la hora 23:59 a la fecha de eliminación
    datos_formulario["fecha_eliminacion"] = datetime.strptime(datos_formulario["fecha_eliminacion"],"%Y-%m-%d")
    datos_formulario["fecha_eliminacion"] = str(datos_formulario["fecha_eliminacion"].replace(hour=23,minute=59,second=0))

    sql_query = """
        INSERT INTO Mensaje_administrativo
            (titulo,mensaje,fecha_eliminacion,fecha_registro)
                VALUES (%s,%s,%s,%s)
    """
    cursor.execute(sql_query,(datos_formulario["titulo"],datos_formulario["mensaje"],datos_formulario["fecha_eliminacion"],datetime.now().replace(microsecond=0)))

    return redirect(redirect_url())

@mod.route("/eliminar_mensaje_administrativo/<string:id_mensaje>",methods=["POST"])
def eliminar_mensaje_administrativo(id_mensaje):
    sql_query = """
        DELETE FROM Mensaje_administrativo
            WHERE id = %s
    """
    cursor.execute(sql_query,(id_mensaje,))

    flash("mensaje-borrado")
    return redirect(redirect_url())

@mod.route("/modificar_mensaje_administrativo/<string:id_mensaje>",methods=["POST"])
def modificar_mensaje_administrativo(id_mensaje):
    datos_formulario = request.form.to_dict()

    # Se verifica si existe fecha de eliminación
    if not len(datos_formulario["fecha_eliminacion"]):
        # No se especificó una fecha de eliminación
        datos_formulario["fecha_eliminacion"] = str(datetime.now().date())

    # Se agrega la hora 23:59 a la fecha de eliminación
    datos_formulario["fecha_eliminacion"] = datetime.strptime(datos_formulario["fecha_eliminacion"],"%Y-%m-%d")
    datos_formulario["fecha_eliminacion"] = str(datos_formulario["fecha_eliminacion"].replace(hour=23,minute=59,second=0))

    sql_query = """
        UPDATE Mensaje_administrativo
            SET titulo=%s,mensaje=%s,fecha_eliminacion=%s,fecha_actualizacion=%s
                WHERE id=%s
    """
    cursor.execute(sql_query,(datos_formulario["titulo"],datos_formulario["mensaje"],datos_formulario["fecha_eliminacion"],str(datetime.now()),id_mensaje))

    flash("mensaje-modificado")
    return redirect(redirect_url())