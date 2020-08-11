from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify
from config import db,cursor
import os,time,bcrypt,smtplib
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText

mod = Blueprint("rutas_lorenzo",__name__)

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

@mod.route("/wishlist_usuario",methods=["GET", "POST"])
def tabla_wishlist():
    if "usuario" not in session.keys():
        return redirect("/")

    if request.method == "POST":
        fecha_solicitud_wishlist = datetime.now()
        form = request.form.to_dict()

        sql_query= """
            INSERT INTO Wishlist
                (rut_solicitante,nombre_equipo,marca_equipo,modelo_equipo,motivo_academico,fecha_solicitud)
                    VALUES (%s,%s,%s,%s,%s,%s)
        """
        cursor.execute(sql_query,(session["usuario"]["rut"],form["nombre"],form["marca"],form["modelo"],form["motivo"],fecha_solicitud_wishlist))

        cursor.execute("SELECT MAX(id) FROM Wishlist")
        last_id = cursor.lastrowid

        for i in range(10):
            if 'url[{}]'.format(str(i)) in form:
                call = 'url[{}]'.format(str(i))
                url = form[call]
                sql_query= """
                    INSERT INTO Url_wishlist (url,id_wishlist)
                        VALUES (%s,%s)
                """
                cursor.execute(sql_query,(url,last_id))
            else:
                break

        flash("solicitud-registrada")

    sql_query = """
        SELECT *
            FROM Wishlist
                WHERE estado_wishlist = 8
                    ORDER BY Wishlist.fecha_solicitud DESC
                        LIMIT 10
    """
    cursor.execute(sql_query)
    lista_wishlist_aceptada = cursor.fetchall()

    sql_query = """
        SELECT Wishlist.*,Estado_detalle_solicitud.nombre AS nombre_estado
            FROM Wishlist,Estado_detalle_solicitud
                WHERE rut_solicitante = %s
                AND Wishlist.estado_wishlist = Estado_detalle_solicitud.id
    """
    cursor.execute(sql_query,(session["usuario"]["rut"],))
    lista_solicitudes_wishlist = cursor.fetchall()

    return render_template("/wishlist/user_wishlist.html",
        lista_wishlist_aceptada=lista_wishlist_aceptada,
        lista_solicitudes_wishlist=lista_solicitudes_wishlist)

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

    return render_template("/wishlist/admin_wishlist_detalle.html",
        detalle_solicitud=detalle_solicitud,
        url_solicitud=url_solicitud)

@mod.route("/aceptar_solicitud/<string:id_detalle>",methods=["POST"])
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
    
    direccion_template = os.path.normpath(os.path.join(os.getcwd(), "app/templates/wishlist/templates_mail/aceptacion_solicitud.html"))
    archivo_html = open(direccion_template,encoding="utf-8").read()

    archivo_html = archivo_html.replace("%id_solicitud%",str(id_detalle))
    archivo_html = archivo_html.replace("%nombre_usuario%",datos_usuario["nombres"]+" "+datos_usuario["apellidos"])
    archivo_html = archivo_html.replace("%equipo_solicitado%",datos_solicitud["nombre_equipo"]+" "+datos_solicitud["modelo_equipo"]+" "+datos_solicitud["marca_equipo"])
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

    direccion_template = os.path.normpath(os.path.join(os.getcwd(), "app/templates/wishlist/templates_mail/rechazo_solicitud.html"))
    archivo_html = open(direccion_template,encoding="utf-8").read()

    archivo_html = archivo_html.replace("%id_solicitud%",str(id_detalle))
    archivo_html = archivo_html.replace("%nombre_usuario%",datos_usuario["nombres"]+" "+datos_usuario["apellidos"])
    archivo_html = archivo_html.replace("%equipo_solicitado%",datos_solicitud["nombre_equipo"]+" "+datos_solicitud["modelo_equipo"]+" "+datos_solicitud["marca_equipo"])
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

    flash("solicitud-eliminada")
    return redirect("/gestion_wishlist")
