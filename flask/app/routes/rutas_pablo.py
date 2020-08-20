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
import csv
from werkzeug.utils import secure_filename

mod = Blueprint("rutas_pablo",__name__)

def redirect_url(default='index'): # Redireccionamiento desde donde vino la request
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

@mod.route("/gestion_usuarios",methods=['GET'])
def ver_usuarios():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")

    query= """
            SELECT Usuario.nombres AS nombres, Usuario.apellidos AS apellidos, Usuario.rut AS rut, Credencial.nombre AS credencial, Usuario.email as correo, Usuario.region as region, Usuario.comuna as comuna, Usuario.direccion as direccion
                FROM Usuario,Credencial
                    WHERE Usuario.id_credencial= Credencial.id
            """
    cursor.execute(query)
    usuarios=cursor.fetchall()

    return render_template("/pablo/ver_usuarios.html",usuarios=usuarios)

@mod.route("/gestion_usuarios/anadir_usuario",methods=["POST"])
def añadir_usuario():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")

    if request.method=='POST':
        #Creacion del usuario
        datos_usuario=request.form.to_dict()#obtener datos del usuario en un diccionario
        query = ''' INSERT INTO Usuario(rut, id_credencial, email, nombres, apellidos)
            VALUES (%s, %s, %s, %s, %s)'''
        cursor.execute(query,(datos_usuario['rut'], datos_usuario['credencial'], datos_usuario['correo'], datos_usuario['nombres'], datos_usuario['apellidos']))

        #Una vez creado, se le notifica al usuario para que cambie su contraseña y complete sus datos

        # Se abre el template HTML correspondiente al restablecimiento de contraseña
        direccion_template = os.path.normpath(os.path.join(os.getcwd(), "app/templates/vistas_exteriores/establecer_password_mail.html"))
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
        correo["To"] = datos_usuario["correo"]
        correo["Subject"] = "Establecer Contraseña - LabEIT UDP"

        try:
            server = smtplib.SMTP("smtp.gmail.com",587)
            server.starttls()
            server.login("labeit.udp@gmail.com","LabEIT_UDP_2020")
            str_correo = correo.as_string()
            server.sendmail("labeit.udp@gmail.com",datos_usuario["correo"],str_correo)
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
        flash('agregar-correcto')
        return redirect("/gestion_usuarios")

@mod.route("/gestion_usuarios/editar_usuario",methods=["POST"])
def editar():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")

    if request.method=='POST':
        datos_usuario=request.form.to_dict()
        #query para actualizar datos del usuario
        query=''' UPDATE Usuario SET id_credencial = %s, email=%s, nombres =%s, apellidos= %s, region = %s, comuna = %s, direccion = %s
                    WHERE rut= %s'''
        cursor.execute(query,(datos_usuario['credencial'],datos_usuario['correo'],datos_usuario['nombres'],datos_usuario['apellidos'],datos_usuario['region'],datos_usuario['comuna'],datos_usuario['direccion'],datos_usuario['rut']))
        flash('editado-correcto')
        #se redirige de vuelta a la pagina principal de gestion usuarios
        return redirect("/gestion_usuarios")

@mod.route("/gestion_usuarios/eliminar_usuario", methods=["POST"])
def eliminar():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")

    if request.method=='POST':   
        rut=request.form['rut']
        query=''' DELETE FROM Usuario WHERE rut= %s'''
        
        cursor.execute(query,(rut,))
        flash('eliminar-correcto')
        return redirect("/gestion_usuarios")

@mod.route("/gestion_usuarios/ver_usuario/<string:rut>" ,methods=["GET"])
def detalle_usuario(rut):
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")

    if request.method=='GET':
        print(rut)
        query=''' Select Usuario.nombres as nombres, Usuario.apellidos as apellidos, Credencial.nombre as credencial,
            Usuario.email as correo, Usuario.region as region, Usuario.comuna as comuna, Usuario.rut as rut,
            Usuario.direccion as direccion, Usuario.celular as celular FROM Usuario,Credencial WHERE Credencial.id=Usuario.id_credencial AND Usuario.rut=%s '''
        cursor.execute(query,(rut,))
        usuario=cursor.fetchone()
        
        query=''' Select Solicitud.id as id, Solicitud.rut_profesor as profesor, Solicitud.rut_alumno as alumno, Solicitud.motivo as motivo, Solicitud.fecha_registro as registro,
            Detalle_solicitud.estado as estado, Detalle_solicitud.id as id_detalle, Equipo.nombre as equipo, Equipo.modelo as modelo  
            FROM Solicitud, Detalle_solicitud, Equipo
            WHERE Solicitud.id = Detalle_solicitud.id_solicitud AND Solicitud.rut_alumno= %s AND Equipo.id = Detalle_solicitud.id_equipo '''
        cursor.execute(query,(rut,))
        solicitudes=cursor.fetchall()

        query='''Select Curso.id as id , Curso.codigo_udp as codigo , Curso.nombre as nombre FROM Curso, Seccion_alumno,Seccion WHERE Seccion_alumno.rut_alumno= %s'''
        cursor.execute(query,(rut,))
        cursos=cursor.fetchall()
        
        query= '''SELECT * FROM Sanciones WHERE rut_alumno = %s'''
        cursor.execute(query,(rut,))
        sancion=cursor.fetchone()
    

        return render_template("/pablo/detalle_usuario.html",usuario=usuario,solicitudes=solicitudes,cursos=cursos,sancion=sancion)

@mod.route("/anadir_masivo",methods=["POST","GET"])
def masivo():
    
    if request.method=='GET':   
        #data=request.files["file"]
        #data.save(secure_filename(data.filename))
        with open("datos.csv") as csv_file:
            reader=csv.reader(csv_file,delimeter=",")
            query = ''' INSERT INTO Usuario(rut, id_credencial, email, nombres, apellidos)
            VALUES '''
            for row in reader:
                query += '''(%s,%s,%s,%s,%s),'''
    #query[0,-1] la query desde el inicio hasta el final, se borra la ultima coma,
    #Hay que recorrer el reader para agregar los valores al execute, dictReader no se puede recorrer. 
    #cursor.execute(query[0:-1],['rut'], datos_usuario['credencial'], datos_usuario['correo'], datos_usuario['nombres'], datos_usuario['apellidos']))
    print(reader["rut"])
    return "ok"


@mod.route("/gestion_usuarios/sancion",methods=["POST"])
def sancion():
    data=request.form.to_dict()
    if data['cant_sancion']!=0:
        query= ''' SELECT cantidad_dias FROM Sanciones WHERE rut_alumno= %s'''
        cursor.execute(query,(data['rut'],))
        dias=cursor.fetchone()
        dias=dias['cantidad_dias']
        if data['op_sancion'] == '1' :#Aumentar dias de sancion
            dias=dias+int(data['cant_sancion'])
        elif data['op_sancion']== '2' : #Disminuir dias de sancion
            dias=dias-int(data['cant_sancion'])
            print(dias)
            if dias < 0:
                print("error")
                flash("Error")
                return redirect(url_for("rutas_pablo.detalle_usuario",rut=data['rut']))
            flash("cambio-realizado")
            return redirect(url_for("rutas_pablo.detalle_usuario",rut=data['rut']))
        #Se actualiza el registro y se comprueba si se debe eliminar.
        query= ''' UPDATE Sanciones SET cantidad_dias = %s WHERE rut_alumno = %s'''
        cursor.execute(query,(dias,data['rut']))
        flash("cambio-realizado")
    return redirect(url_for("rutas_pablo.detalle_usuario",rut=data['rut']))
