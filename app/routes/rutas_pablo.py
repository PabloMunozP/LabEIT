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

mod = Blueprint("rutas_pablo",__name__)

@mod.route("/pablo",methods=["GET"])
def principal():
    return "OK"

@mod.route("/ver_usuario",methods=['GET'])
def ver_usuarios():
    query= """ SELECT Usuario.nombres as nombres, Usuario.apellidos as apellidos, Usuario.rut as rut, Credencial.nombre as credencial FROM Usuario, Credencial WHERE Usuario.id_credencial=Credencial.id"""
    cursor=db.cursor()
    cursor.execute(query)
    usuarios=cursor.fetchall()
    return render_template("/pablo/ver_usuarios.html",usuarios=usuarios)

@mod.route("/anadir_usuario",methods=["GET","POST"])
def añadir_usuario():
    if request.method=='GET':
        return render_template("/pablo/añadir_usuario.html")
    elif request.method=='POST':
        #Creacion del usuario
        datos_usuario=request.form.to_dict()#obtener datos del usuario en un diccionario
        query = ''' INSERT INTO Usuario(rut, id_credencial, email, nombres, apellidos) VALUES (%s, %s, %s, %s, %s)'''
        cursor=db.cursor()
        cursor.execute(query,(datos_usuario['rut'], datos_usuario['credencial'], datos_usuario['correo'], datos_usuario['nombres'], datos_usuario['apellidos']))
        print('se creo usuario')    
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
        return render_template("/pablo/ver_usuario.html")
    
@mod.route("/editar_usuario/<string:rut>",methods=["GET","POST"])
def editar(rut=None):
    if request.method =='GET' :
        if rut:
            query='''SELECT * FROM Usuario WHERE rut= %s'''
            cursor = db.cursor()
            cursor.execute(query, (rut,))
            resultado = cursor.fetchall()
            if(resultado==[]):
                return render_template("/pablo/editar_usuario.html",msg='No existe ese alumno')
            elif(resultado[0][0]==rut):
                credencial= 'Alumno' if resultado[0][1]== 1 else 'Profesor' if resultado[0][1] == 2 else 'Administrador' if resultado[0][1] == 3 else None
                return render_template("/pablo/editar_usuario.html",datos=resultado[0],credencial=credencial)
        else:
            return render.template("/pablo/editar_usuario.html",msg='Error en el rut')
    elif request.method=='POST':
        datos_usuario=request.form.to_dict()
        if rut:
            query=''' UPDATE Usuario SET credencial = %s, email=%s, nombres =%s, apellidos= %s, celular = %s, region = %s, comuna = %s, direccion = %s
                     WHERE rut= %s'''
            cursor=db.cursor()
            cursor.execute(query(datos_usuario['credencial'],datos_usuario['correo'],datos_usuario['nombres'],datos_usuario['apellidos'],datos_usuario['celular'],datos_usuario['region'],datos_usuario['comuna'],datos_usuario['direccion'],rut))
            return render_template("/pablo/ver_usuario.html",msg='Actualizado con exito')