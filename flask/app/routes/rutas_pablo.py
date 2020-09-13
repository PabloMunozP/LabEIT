from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify
from config import db,cursor, BASE_DIR
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
import glob
import platform
from itertools import cycle
from datetime import datetime, timedelta
PATH = BASE_DIR # obtiene la ruta del directorio actual
PROFILE_PICS_PATH = PATH.replace(os.sep, '/')+'/app/static/imgs/profile_pics/' #  remplaza [\\] por [/] en windows


mod = Blueprint("rutas_gestion_usuarios",__name__)

def redirect_url(default='index'): # Redireccionamiento desde donde vino la request
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

def obtener_foto_perfil(rut_usuario): # Función para obtener el archivo de la foto de perfil
    if glob.glob(PROFILE_PICS_PATH + rut_usuario +'.*'): # Si la foto existe
        filename = glob.glob(PROFILE_PICS_PATH + rut_usuario +'.*') # Nombre del archivo + extension
        head, tail = os.path.split(filename[0])
        return tail # Retorna nombre del archivo + extension de la foto de perfil
    else: # Si la foto no existe
        return 'default_pic.png' # Retorna la foto default

@mod.route("/gestion_usuarios",methods=['GET'])
def ver_usuarios():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")

    query= """
            SELECT Usuario.nombres AS nombres, Usuario.apellidos AS apellidos, Usuario.rut AS rut, Credencial.nombre AS credencial, Usuario.email as correo, Usuario.region as region, Usuario.comuna as comuna, Usuario.direccion as direccion
                FROM Usuario,Credencial
                    WHERE Usuario.id_credencial= Credencial.id AND Usuario.activo=1
            """
    cursor.execute(query)
    usuarios=cursor.fetchall()


    return render_template("/vistas_gestion_usuarios/ver_usuarios.html",usuarios=usuarios)

def digito_verificador(rut):
    reversed_digits = map(int, reversed(str(rut)))
    factors = cycle(range(2, 8))
    s = sum(d * f for d, f in zip(reversed_digits, factors))
    ver = (-s) % 11
    if ver < 10:
        return str(ver)
    if ver == 10:
        return 'K'

@mod.route("/gestion_usuarios/anadir_usuario",methods=["POST"])
def añadir_usuario():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")

    if request.method=='POST':
        #Creacion del usuario
        datos_usuario=request.form.to_dict()#obtener datos del usuario en un diccionario
        #Comprobar que el usuario no exista previamente

        query= ''' SELECT Usuario.rut as rut FROM Usuario WHERE rut=%s '''
        cursor.execute(query,(datos_usuario['rut'],))
        duplicados_rut=cursor.fetchone()

        query= ''' SELECT Usuario.email as correo FROM Usuario WHERE email=%s '''
        cursor.execute(query,(datos_usuario['correo'],))
        duplicados_correo=cursor.fetchone()


        if duplicados_rut is not None : #Ya existe un usuario con ese rut
            flash('error-añadir-rut')
            return redirect("/gestion_usuarios")
        if duplicados_correo is not None : #Ya existe alguien registrado con ese rut
            flash('error-añadir-correo')
            return redirect("/gestion_usuarios")
        if duplicados_rut is None and duplicados_correo is None :#No exista nadie con rut ni correo repetido.

            #Comprobar que el rut y verificador sean validos.
            print(datos_usuario['rut'][-1])
            print(digito_verificador(datos_usuario['rut'][0:-1]))
            if datos_usuario['rut'][-1] == digito_verificador(datos_usuario['rut'][0:-1]):
                #El rut es correcto

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
                sql_query = """ DELETE FROM Token_recuperacion_password
                      WHERE rut_usuario = %s   """
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

                except Exception as e:
                    print(e)
                    flash("error-correo-inicio") # Notificación de fallo al enviar el correo
                flash('agregar-correcto')
                return redirect("/gestion_usuarios")
            else:
                flash('error-digitoVerficador')
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
        #Comprobar que el usuario no tenga equipos pendientes
        query= '''SELECT id FROM Solicitud Where rut_alumno = %s'''
        cursor.execute(query,(rut,))
        solicitudes=cursor.fetchone()
        if solicitudes is not None: # El usuario tiene solicitudes activas
            flash("error-eliminar")
            return redirect("/gestion_usuarios")
        else:#El usuario no tiene solicitudes pendientes.
            query=''' DELETE FROM Usuario WHERE rut= %s'''
            cursor.execute(query,(rut,))
            flash('eliminar-correcto')
            return redirect("/gestion_usuarios")

@mod.route("/gestion_usuarios/inhabilitar",methods=["POST"])
def inhabilitar():

    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")

    if request.method== 'POST':
        rut=request.form['rut']
        query= '''SELECT id FROM Solicitud Where rut_alumno = %s'''
        cursor.execute(query,(rut,))
        solicitudes=cursor.fetchone()

        if solicitudes is not None: # El usuario tiene solicitudes activas
            flash("error-inhabilitar")
            return redirect("/gestion_usuarios")
        else:#El usuario no tiene solicitudes pendientes.
            query='''UPDATE Usuario SET Usuario.activo = 0 WHERE rut= %s'''
            cursor.execute(query,(rut,))
            flash('inhabilitar-correcto')
            return redirect("/gestion_usuarios")


@mod.route("/gestion_usuarios/ver_usuario/<string:rut>" ,methods=["GET"])
def detalle_usuario(rut):
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")

    if request.method=='GET':
        #print(rut)
        query=''' SELECT Usuario.nombres as nombres, Usuario.apellidos as apellidos, Credencial.nombre as credencial,
            Usuario.email as correo, Usuario.region as region, Usuario.comuna as comuna, Usuario.rut as rut,
            Usuario.direccion as direccion, Usuario.celular as celular FROM Usuario,Credencial WHERE Credencial.id=Usuario.id_credencial AND Usuario.rut=%s '''
        cursor.execute(query,(rut,))
        usuario=cursor.fetchone()

        query=''' SELECT Solicitud.id as id, Solicitud.rut_profesor as profesor, Solicitud.rut_alumno as alumno, Solicitud.motivo as motivo, Solicitud.fecha_registro as registro,
            Detalle_solicitud.estado as estado, Detalle_solicitud.id as id_detalle, Equipo.nombre as equipo, Equipo.modelo as modelo, Equipo.marca as marca_equipo
            FROM Solicitud, Detalle_solicitud, Equipo
            WHERE Solicitud.id = Detalle_solicitud.id_solicitud AND Solicitud.rut_alumno= %s AND Equipo.id = Detalle_solicitud.id_equipo '''
        cursor.execute(query,(rut,))
        solicitudes=cursor.fetchall()

        query="""
            SELECT Curso.*,Seccion.codigo AS codigo_seccion
                FROM Curso,Seccion,Seccion_alumno
                    WHERE Curso.id = Seccion.id_curso
                    AND Seccion.id = Seccion_alumno.id_seccion
                    AND Seccion_alumno.rut_alumno = %s
                    ORDER BY Curso.nombre
        """
        cursor.execute(query,(rut,))
        cursos=cursor.fetchall()

        query= '''SELECT * FROM Sanciones WHERE rut_alumno = %s'''
        cursor.execute(query,(rut,))
        sancion=cursor.fetchone()

        archivo_foto_perfil=obtener_foto_perfil(rut)

        return render_template("/vistas_gestion_usuarios/detalle_usuario.html",usuario=usuario,solicitudes=solicitudes,
            cursos=cursos,sancion=sancion,dir_foto_perfil = url_for('static',filename='imgs/profile_pics/'+archivo_foto_perfil) )

@mod.route("/gestion_usuarios/anadir_masivo",methods=["POST"])
def masivo():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:

      if request.method=='POST':
          archivo=request.files["file"]
          if  not "." in archivo.filename:
              flash("sin-extension")
              return 'error extension'
          ext= os.path.splitext(archivo.filename)[1]

          if ext  == '.csv' :
              print('extension correcta')
              archivo.filename = session['usuario']['rut'] + "." + archivo.filename.split('.')[1].lower()
              archivo.save(os.path.join( PATH+'/app/static/files/uploads/', secure_filename(archivo.filename) ) )
              with open(os.path.join( PATH+'/app/static/files/uploads/', secure_filename(archivo.filename)) , 'r')  as csvfile:
                  read = csv.reader(csvfile, delimiter=',')
                  lines = list(read)
                  query=''' INSERT INTO Usuario(rut,nombres,apellidos,id_credencial)
                          VALUES (%s,%s,%s,%s)'''
                  del lines[0]
                  for line in lines:
                      print(line)
                      id = 1 if line[3] == 'Alumno' else 2 if line[3] == 'Profesor' else 3
                      cursor.execute(query,(line[0],line[1],line[2],id))

                  flash('agregar-masivo-correcto')
                  return redirect("/gestion_usuarios")



@mod.route("/gestion_usuarios/sancion",methods=["POST"])
def sancion():
    data=request.form.to_dict()
    if data['cant_sancion'] == '0' :
        flash("sin-cambio")
        #print("paso por aca")
    else:
        query= ''' SELECT cantidad_dias FROM Sanciones WHERE rut_alumno= %s'''
        cursor.execute(query,(data['rut'],))
        dias=cursor.fetchone()
        dias=dias['cantidad_dias']
        if data['op_sancion'] == '1' :#Aumentar dias de sancion
            dias=dias+int(data['cant_sancion'])
        elif data['op_sancion']== '2' : #Disminuir dias de sancion
            dias=dias-int(data['cant_sancion'])
            #print(dias)
        if dias < 0:
            #print("error")
            flash("Error")
            return redirect(redirect_url())
        elif dias == 0:
            query= ''' DELETE FROM  Sanciones WHERE rut_alumno= %s '''
            cursor.execute(query,(data['rut'],))
            flash("cambio-realizado")
            return redirect(redirect_url())
        #Se actualiza el registro y se comprueba si se debe eliminar.
        query= ''' UPDATE Sanciones SET cantidad_dias = %s WHERE rut_alumno = %s'''
        cursor.execute(query,(dias,data['rut']))
        #print("cambio-realizado")
        flash("cambio-realizado")
    return redirect(redirect_url())
