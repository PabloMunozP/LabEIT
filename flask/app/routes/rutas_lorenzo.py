from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify,send_file
from config import db,cursor, BASE_DIR
from werkzeug.utils import secure_filename
import os,time,bcrypt,smtplib,glob
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
PATH = BASE_DIR
TAMAÑO_MAX_COT = 10000000
PROFILE_DOCS_PATH = PATH.replace(os.sep, '/')+'/app/static/files/cotizaciones_wishlist/'
EXTENSIONES_PERMITIDAS = ["PDF"]
CANTIDAD_LINKS = 10
CANTIDAD_WISHLIST = 5

mod = Blueprint("rutas_lorenzo",__name__)

@mod.context_processor
def utility_functions():
    def print_in_console(message):
        print(str(message))
    return dict(mdebug=print_in_console)

#para imprimir en consola {{ mdebug(detalle_solicitud["nombre_equipo "]) }}

def redirect_url(default='index'): # Redireccionamiento desde donde vino la request
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

def enviar_correo_notificacion(archivo,str_para,str_asunto,correo_usuario):
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
        flash("correo-exito")

    except Exception as e:
        print(e)
        flash("correo-fallido")

def verificar_cancelacion(id_wishlist):
    cursor.execute("SELECT estado_wishlist FROM Wishlist WHERE id = %s", (id_wishlist,))
    estado = cursor.fetchone()["estado_wishlist"]
    return True if estado == 7 else False

def allowed_doc(filename): # funcion que valida la extension de la imagen
    if not "." in filename:
        return False
    ext = filename.rsplit(".",1)[1]
    if ext.upper() in EXTENSIONES_PERMITIDAS:
        return True
    else:
        return False

def obtener_cotizacion(id_wishlist):
    if glob.glob(PROFILE_DOCS_PATH + id_wishlist +'.pdf'):
        filename = glob.glob(PROFILE_DOCS_PATH + id_wishlist +'.pdf')
        head, tail = os.path.split(filename[0])
        return tail, True
    return False, False

def borrar_cotizacion(id_wishlist):
    if glob.glob(PROFILE_DOCS_PATH + id_wishlist +'.pdf'):
        filename = glob.glob(PROFILE_DOCS_PATH + id_wishlist +'.pdf')
        head, tail = os.path.split(filename[0])
        os.remove(PROFILE_DOCS_PATH + tail )

@mod.route("/wishlist_usuario",methods=["GET", "POST"])
def tabla_wishlist():
    if "usuario" not in session.keys():
        return redirect("/")

    if request.method == "POST":
        fecha_solicitud_wishlist = datetime.now()
        form = request.form.to_dict()

        sql_query = """
            INSERT INTO Wishlist
                (rut_solicitante,nombre_equipo,marca_equipo,modelo_equipo,motivo_academico,fecha_solicitud)
                    VALUES (%s,%s,%s,%s,%s,%s)
        """
        cursor.execute(sql_query,(session["usuario"]["rut"],form["nombre"],form["marca"],form["modelo"],form["motivo"],fecha_solicitud_wishlist))

        cursor.execute("SELECT MAX(id) FROM Wishlist")
        last_id = cursor.lastrowid

        if "id" in form:
            sql_query = """
                INSERT INTO Motivo_academico_wishlist
                    (id_wishlist,id_curso)
                    VALUES (%s,%s)
            """
            cursor.execute(sql_query,(last_id,form["id"]))

        if form["adjuntar"] == "1":
            documento = request.files["cotizacion"]
            if request.content_length > TAMAÑO_MAX_COT:
                return
            if not allowed_doc(documento.filename):
                return redirect('/')
            documento.filename = str(last_id) + ".pdf"
            documento.save( os.path.join( PATH+'/app/static/files/cotizaciones_wishlist', secure_filename(documento.filename) ) )

        for i in range(int(form["index"])+1):
            if 'url[{}]'.format(str(i)) in form:
                call = 'url[{}]'.format(str(i))
                url = form[call]
                sql_query= """
                    INSERT INTO Url_wishlist (url,id_wishlist)
                        VALUES (%s,%s)
                """
                cursor.execute(sql_query,(url,last_id))

        flash("solicitud-registrada")

    sql_query = """
        SELECT *
            FROM Wishlist
                WHERE estado_wishlist = 8
                    ORDER BY Wishlist.fecha_solicitud DESC
    """
    cursor.execute(sql_query)
    lista_wishlist_aceptada = cursor.fetchall()

    sql_query = """
        SELECT Wishlist.*,Estado_detalle_solicitud.nombre AS nombre_estado
            FROM Wishlist,Estado_detalle_solicitud
                WHERE rut_solicitante = %s
                AND Wishlist.estado_wishlist = Estado_detalle_solicitud.id
                ORDER BY Wishlist.fecha_solicitud DESC
    """
    cursor.execute(sql_query,(session["usuario"]["rut"],))
    lista_solicitudes_wishlist = cursor.fetchall()

    sql_query = """
        SELECT count(id)
            FROM Wishlist
                WHERE estado_wishlist = 8
    """
    cursor.execute(sql_query)
    count_wishlist = cursor.fetchone()

    sql_query = """
        SELECT *
            FROM Curso
    """
    cursor.execute(sql_query)
    cursos = cursor.fetchall()

    return render_template("/wishlist/user_wishlist.html",
        lista_wishlist_aceptada=lista_wishlist_aceptada,
        lista_solicitudes_wishlist=lista_solicitudes_wishlist,
        count_wishlist = count_wishlist,
        cursos = cursos,
        cantidad_wishlist = CANTIDAD_WISHLIST,
        cantidad_links = CANTIDAD_LINKS)

@mod.route("/wishlist_usuario/editar_solicitud/<string:id_detalle_solicitud>",methods=["GET","POST"])
def editar_solicitud(id_detalle_solicitud):
    if "usuario" not in session.keys():
        return redirect("/")
    if verificar_cancelacion(id_detalle_solicitud):
        return redirect("/")

    if request.method == "POST":
        fecha_modificacion = datetime.now()
        form = request.form.to_dict()
        
        sql_query = """
            UPDATE Wishlist
                SET nombre_equipo = %s,
                marca_equipo = %s,
                modelo_equipo = %s,
                motivo_academico = %s,
                fecha_solicitud = %s,
                modificacion = 1
                    WHERE id = %s
        """
        cursor.execute(sql_query,(form["nombre"],form["marca"],form["modelo"],form["motivo"],fecha_modificacion,id_detalle_solicitud))

        if form["adjuntar"] == "1":
            doc = request.files["documento"]
            if request.content_length > TAMAÑO_MAX_COT:
                return "Tamaño de archivo excede el limite"
            if not allowed_doc(doc.filename):
                return redirect('/')
            borrar_cotizacion(id_detalle_solicitud)
            doc.filename = str(id_detalle_solicitud) + ".pdf"
            doc.save( os.path.join( PATH+'/app/static/files/cotizaciones_wishlist', secure_filename(doc.filename) ) )
        elif form["adjuntar"] == "0":
            if "erase" in form:
                if form["erase"] == "1":
                    borrar_cotizacion(id_detalle_solicitud)

        sql_query = """
            DELETE
                FROM Url_wishlist
                    WHERE id_wishlist = %s
        """
        cursor.execute(sql_query,(id_detalle_solicitud,))

        for i in range(int(form["index"])+1):
            if 'url[{}]'.format(str(i)) in form:
                call = 'url[{}]'.format(str(i))
                url = form[call]
                sql_query= """
                    INSERT INTO Url_wishlist (url,id_wishlist)
                        VALUES (%s,%s)
                """
                cursor.execute(sql_query,(url,id_detalle_solicitud))

        flash("solicitud-modificada")

    sql_query = """
        SELECT Wishlist.*,Estado_detalle_solicitud.nombre AS nombre_estado
            FROM Wishlist,Estado_detalle_solicitud
                WHERE Wishlist.estado_wishlist = Estado_detalle_solicitud.id
                AND Wishlist.id = %s
    """
    cursor.execute(sql_query,(id_detalle_solicitud,))
    detalle_solicitud = cursor.fetchone()

    if detalle_solicitud is None:
        flash("solicitud-no-encontrada")
        return redirect("/gestion_wishlist")

    sql_query = """
        SELECT *
            FROM Curso
    """
    cursor.execute(sql_query)
    cursos = cursor.fetchall()

    sql_query = """
        SELECT *
            FROM Motivo_academico_wishlist
                WHERE id_wishlist = %s
    """
    cursor.execute(sql_query,(id_detalle_solicitud,))
    motivo = cursor.fetchone()

    cotz = {}
    cotz["validar"] = obtener_cotizacion(id_detalle_solicitud)

    sql_query ="""
        SELECT count(id)
            FROM Url_wishlist
                WHERE id_wishlist = %s
    """
    cursor.execute(sql_query,(id_detalle_solicitud,))
    url_count = cursor.fetchone()

    sql_query = """
        SELECT *
            FROM Url_wishlist
                WHERE id_wishlist = %s
    """
    cursor.execute(sql_query,(id_detalle_solicitud,))
    urls = cursor.fetchall()

    return render_template("/wishlist/user_wishlist_edit.html",
        detalle_solicitud = detalle_solicitud,
        cursos = cursos,
        motivo = motivo,
        cotz = cotz,
        url_count=url_count,
        urls = urls,
        cantidad_links = CANTIDAD_LINKS)

@mod.route("/user_cancelar_solicitud_w/<string:id_detalle>",methods=["POST"])
def cancelar_solicitud_user(id_detalle):

    sql_query = """
        UPDATE Wishlist
            SET estado_wishlist = 7
                WHERE id = %s
    """
    cursor.execute(sql_query,(id_detalle,))

    flash("solicitud-cancelada")
    return redirect("/wishlist_usuario")

@mod.route("/gestion_wishlist",methods=["GET"])
def gestionar_wishlist():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3: # El usuario debe ser un administrador (Credencial = 3)
        return redirect("/")

    sql_query = """
        SELECT Wishlist.*,Estado_detalle_solicitud.nombre AS nombre_estado,Usuario.nombres AS nombres_usuario,Usuario.apellidos AS apellidos_usuario
            FROM Wishlist,Estado_detalle_solicitud,Usuario
                WHERE Wishlist.estado_wishlist = Estado_detalle_solicitud.id
                AND Wishlist.rut_solicitante = Usuario.rut
                    ORDER BY Wishlist.fecha_solicitud DESC
    """
    cursor.execute(sql_query)
    lista_solicitudes_wishlist = cursor.fetchall()

    return render_template("/wishlist/admin_wishlist.html",
        lista_solicitudes_wishlist=lista_solicitudes_wishlist)

@mod.route("/gestion_wishlist/detalle_solicitud/<string:id_detalle_solicitud>",methods=["GET"])
def detalle_solicitud(id_detalle_solicitud):
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")

    sql_query = """
        SELECT Wishlist.*,Estado_detalle_solicitud.nombre AS nombre_estado,Usuario.nombres AS nombres,Usuario.apellidos AS apellidos,Usuario.email AS email
            FROM Wishlist,Estado_detalle_solicitud,Usuario
                WHERE Wishlist.estado_wishlist = Estado_detalle_solicitud.id
                AND Wishlist.rut_solicitante = Usuario.rut
                AND Wishlist.id = %s
    """
    cursor.execute(sql_query,(id_detalle_solicitud,))
    detalle_solicitud = cursor.fetchone()

    if detalle_solicitud is None:
        flash("solicitud-no-encontrada")
        return redirect("/gestion_wishlist")

    url_solicitud = {}
    sql_query = """
        SELECT url
	        FROM Url_wishlist
		        WHERE Url_wishlist.id_wishlist = %s
    """
    cursor.execute(sql_query,(id_detalle_solicitud,))

    url_solicitud["url"] = []
    for row in cursor:
        url_solicitud["url"].append(row["url"])

    sql_query = """
        SELECT *
            FROM Curso
    """
    cursor.execute(sql_query)
    cursos = cursor.fetchall()

    sql_query = """
        SELECT *
            FROM Motivo_academico_wishlist
                WHERE id_wishlist = %s
    """
    cursor.execute(sql_query,(id_detalle_solicitud,))
    motivo = cursor.fetchone()

    cotz = {}
    cotz["validar"] = obtener_cotizacion(id_detalle_solicitud)

    return render_template("/wishlist/admin_wishlist_detalle.html",
        detalle_solicitud=detalle_solicitud,
        url_solicitud=url_solicitud,
        cursos = cursos,
        motivo = motivo,
        cotz = cotz)

@mod.route("/aceptar_solicitud_w/<string:id_detalle>",methods=["POST"])
def aceptar_solicitud(id_detalle):
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")

    fecha_revision_solicitud = str(datetime.now().replace(microsecond=0))

    sql_query = """
        UPDATE Wishlist
            SET estado_wishlist = 8,fecha_revision=%s,motivo = NULL
                WHERE id = %s
    """
    cursor.execute(sql_query,(fecha_revision_solicitud,id_detalle))

    sql_query = """
        SELECT *
            FROM Wishlist
                WHERE id = %s
    """
    cursor.execute(sql_query,(id_detalle,))
    datos_solicitud = cursor.fetchone()

    sql_query = """
        SELECT nombres,apellidos,email
            FROM Usuario
                WHERE rut = %s
    """
    cursor.execute(sql_query,(datos_solicitud["rut_solicitante"],))
    datos_usuario = cursor.fetchone()

    direccion_template = os.path.normpath(os.path.join(os.getcwd(), "flask/app/templates/wishlist/templates_mail/aceptacion_solicitud.html"))
    archivo_html = open(direccion_template,encoding="utf-8").read()

    archivo_html = archivo_html.replace("%id_solicitud%",str(id_detalle))
    archivo_html = archivo_html.replace("%nombre_usuario%",datos_usuario["nombres"])
    archivo_html = archivo_html.replace("%equipo_solicitado%",datos_solicitud["nombre_equipo"]+" "+datos_solicitud["marca_equipo"]+" "+datos_solicitud["modelo_equipo"])
    archivo_html = archivo_html.replace("%fecha_registro%",str(datos_solicitud["fecha_solicitud"]))
    archivo_html = archivo_html.replace("%fecha_revision_solicitud%",fecha_revision_solicitud)

    enviar_correo_notificacion(archivo_html,datos_usuario["email"],"Aprobación de solicitud de Wishlist",datos_usuario["email"])

    flash("solicitud-aceptada-correctamente")
    return redirect(redirect_url())

@mod.route("/rechazar_solicitud_w/<string:id_detalle>",methods=["POST"])
def rechazar_solicitud(id_detalle):
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3: # El usuario debe ser un administrador (Credencial = 3)
        return redirect("/")

    fecha_revision_solicitud = str(datetime.now().replace(microsecond=0))

    razon_rechazo = request.form.to_dict()["razon_rechazo"]
    razon_rechazo = razon_rechazo.replace("\n", "<br>")

    sql_query = """
        SELECT *
            FROM Wishlist
                WHERE id = %s
    """
    cursor.execute(sql_query,(id_detalle,))
    datos_solicitud = cursor.fetchone()

    if datos_solicitud is None:
        flash("solicitud-no-encontrada")
        return redirect("/gestion_wishlist")

    sql_query = """
        UPDATE Wishlist
            SET estado_wishlist = 5,fecha_revision=%s
                WHERE id = %s
    """
    cursor.execute(sql_query,(fecha_revision_solicitud,id_detalle))

    sql_query = """
        SELECT nombres,apellidos,email
            FROM Usuario
                WHERE rut = %s
    """
    cursor.execute(sql_query,(datos_solicitud["rut_solicitante"],))
    datos_usuario = cursor.fetchone()

    direccion_template = os.path.normpath(os.path.join(os.getcwd(), "flask/app/templates/wishlist/templates_mail/rechazo_solicitud.html"))
    archivo_html = open(direccion_template,encoding="utf-8").read()

    archivo_html = archivo_html.replace("%id_solicitud%",str(id_detalle))
    archivo_html = archivo_html.replace("%nombre_usuario%",datos_usuario["nombres"])
    archivo_html = archivo_html.replace("%equipo_solicitado%",datos_solicitud["nombre_equipo"]+" "+datos_solicitud["marca_equipo"]+" "+datos_solicitud["modelo_equipo"])
    archivo_html = archivo_html.replace("%fecha_registro%",str(datos_solicitud["fecha_solicitud"]))
    archivo_html = archivo_html.replace("%fecha_revision_solicitud%",fecha_revision_solicitud)

    razon_rechazo = razon_rechazo.strip()
    motivo = razon_rechazo
    if len(razon_rechazo) == 0:
        razon_rechazo = "** No se ha adjuntado un motivo de rechazo de solicitud. **"
        motivo = None

    sql_query = """
        UPDATE Wishlist
            SET motivo=%s
                WHERE id = %s
    """
    cursor.execute(sql_query,(motivo,id_detalle))

    archivo_html = archivo_html.replace("%razon_rechazo%",razon_rechazo)

    enviar_correo_notificacion(archivo_html,datos_usuario["email"],"Rechazo de solicitud de Wishlist",datos_usuario["email"])

    flash("solicitud-rechazada-correctamente")
    return redirect(redirect_url())

@mod.route("/eliminar_solicitud_w/<string:id_detalle>",methods=["POST"])
def eliminar_solicitud(id_detalle):

    sql_query = """
        DELETE FROM
            Url_wishlist
                WHERE id_wishlist = %s
    """
    cursor.execute(sql_query,(id_detalle,))

    sql_query = """
        DELETE FROM
            Wishlist
                WHERE id = %s
    """
    cursor.execute(sql_query,(id_detalle,))
    
    sql_query = """
        DELETE FROM
            Motivo_academico_wishlist
                WHERE id_wishlist = %s
    """
    cursor.execute(sql_query,(id_detalle,))

    borrar_cotizacion(id_detalle)
    
    flash("solicitud-eliminada")
    return redirect("/gestion_wishlist")

@mod.route("/marcar_pendiente_w/<string:id_detalle>",methods=["POST"])
def marcar_pendiente_w(id_detalle):
    fecha_revision_solicitud = str(datetime.now().replace(microsecond=0))

    sql_query = """
        UPDATE Wishlist
            SET estado_wishlist = 0,fecha_revision=%s,motivo = NULL
                WHERE id = %s
    """
    cursor.execute(sql_query,(fecha_revision_solicitud,id_detalle))

    sql_query = """
        SELECT *
            FROM Wishlist
                WHERE id = %s
    """
    cursor.execute(sql_query,(id_detalle,))
    datos_solicitud = cursor.fetchone()

    sql_query = """
        SELECT nombres,apellidos,email
            FROM Usuario
                WHERE rut = %s
    """
    cursor.execute(sql_query,(datos_solicitud["rut_solicitante"],))
    datos_usuario = cursor.fetchone()

    direccion_template = os.path.normpath(os.path.join(os.getcwd(), "flask/app/templates/wishlist/templates_mail/pendiente_solicitud.html"))
    archivo_html = open(direccion_template,encoding="utf-8").read()

    archivo_html = archivo_html.replace("%id_solicitud%",str(id_detalle))
    archivo_html = archivo_html.replace("%nombre_usuario%",datos_usuario["nombres"])
    archivo_html = archivo_html.replace("%equipo_solicitado%",datos_solicitud["nombre_equipo"]+" "+datos_solicitud["marca_equipo"]+" "+datos_solicitud["modelo_equipo"])
    archivo_html = archivo_html.replace("%fecha_registro%",str(datos_solicitud["fecha_solicitud"]))

    enviar_correo_notificacion(archivo_html,datos_usuario["email"],"Solicitud de Wishlist marcada como pendiente",datos_usuario["email"])

    flash("solicitud-pendiente")
    return redirect(redirect_url())

@mod.route("/cotizacion_wishlist/<string:id_detalle_solicitud>",methods=["GET"])
def descargar_cotizacion(id_detalle_solicitud):
    if "usuario" not in session.keys():
        return redirect("/")
    ruta_cotizacion = os.path.normpath(os.path.join(BASE_DIR,"app/static/files/cotizaciones_wishlist/"+id_detalle_solicitud+".pdf"))
    return send_file(ruta_cotizacion,as_attachment=True)