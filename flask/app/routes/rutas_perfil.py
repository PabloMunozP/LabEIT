from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify,send_from_directory
from config import db,cursor, BASE_DIR
from werkzeug.utils import secure_filename
import os, time, bcrypt, timeago
import mysql.connector
import rut_chile
import glob
import platform
from datetime import datetime, timedelta
PATH = BASE_DIR # obtiene la ruta del directorio actual
PROFILE_PICS_PATH = PATH.replace(os.sep, '/')+'/app/static/imgs/profile_pics/' #  remplaza [\\] por [/] en windows

def redirect_url(default='index'): # Redireccionamiento desde donde vino la request
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

mod = Blueprint('rutas_perfil',__name__)


# Query de solicitudes de equipos del usuario
def get_id_from_list_of_dictionary(list_of_dictionaries): # Funcion para almacenar las id de las solicitudes
    result = []
    for element in list_of_dictionaries:
        result.append(element["id"])
    return result

def consultar_solicitudes(rut): # Query para poder consultar las solicitudes
    query = ('''
            SELECT Solicitud.id,
                Usuario.nombres AS responsable_nombres,
                Usuario.apellidos AS responsable_apellidos,
                Usuario_profesor.nombres AS supervisor_responsable_nombres,
                Usuario_profesor.apellidos AS supervisor_responsable_apellidos,
                DATE(Solicitud.fecha_registro) AS fecha_registro
            FROM Solicitud
            LEFT JOIN Usuario ON Usuario.rut = Solicitud.rut_alumno
            LEFT JOIN Usuario AS Usuario_profesor ON Usuario_profesor.rut = Solicitud.rut_profesor
            WHERE Solicitud.rut_alumno = %s
        ''')
    cursor.execute(query,(rut,))
    query_solicitud = cursor.fetchall()
    return query_solicitud

def consultar_equipos_por_id_solicitudes(list_id_solicitudes): # Query para consultar todos los equipos en relacion a las solicitudes
    if len(list_id_solicitudes) < 1:
        return []

    format_strings = ','.join(['%s'] * len(list_id_solicitudes)) # Genera un string para la query
    query = ('''
        SELECT Detalle_solicitud.id_solicitud,
            Detalle_solicitud.id,
            Detalle_solicitud.fecha_inicio,
            Detalle_solicitud.fecha_termino,
            Detalle_solicitud.fecha_devolucion,
            Detalle_solicitud.fecha_vencimiento,
            Equipo.codigo,
            Equipo.nombre,
            Equipo.modelo,
            Equipo.marca,
            Estado_detalle_solicitud.nombre AS estado
        FROM Detalle_solicitud
        LEFT JOIN Equipo ON Detalle_solicitud.id_equipo = Equipo.id
        LEFT JOIN Estado_detalle_solicitud ON Estado_detalle_solicitud.id = Detalle_solicitud.estado
        WHERE Detalle_solicitud.id_solicitud IN (%s)
    ''' % format_strings)
    cursor.execute(query,tuple(list_id_solicitudes))
    query_resultado = cursor.fetchall()
    return query_resultado


def consultar_informacion_perfil(rut_perfil): # Query para consultar la informacion del perfil
    query = ('''
            SELECT
                id_credencial,
                Credencial.nombre AS credencial_nombre,
                rut,
                email,
                nombres,
                apellidos,
                region,
                comuna,
                direccion,
                celular,
                fecha_registro
            FROM Usuario
            LEFT JOIN Credencial
            ON Credencial.id = Usuario.id_credencial
            WHERE rut = %s
        ''')
    cursor.execute(query,(rut_perfil,))
    resultado_perfil = cursor.fetchone()
    return resultado_perfil

def obtener_foto_perfil(rut_usuario): # Función para obtener el archivo de la foto de perfil
    if glob.glob(PROFILE_PICS_PATH + rut_usuario +'.*'): # Si la foto existe
        filename = glob.glob(PROFILE_PICS_PATH + rut_usuario +'.*') # Nombre del archivo + extension
        head, tail = os.path.split(filename[0])
        return tail # Retorna nombre del archivo + extension de la foto de perfil
    else: # Si la foto no existe
        return 'default_pic.png' # Retorna la foto default


# session['usuario']['rut']
# ************ Perfil ***************************
@mod.route('/gestion_usuarios/usuario/<string:rut_perfil>',  methods =['GET','POST']) # ** Importante PERFIL** #
def ver_usuario_gestion(rut_perfil):
    if 'usuario' not in session or session["usuario"]["id_credencial"] != 3:
        return redirect('/')
    resultado_perfil = consultar_informacion_perfil(rut_perfil)
    archivo_foto_perfil = obtener_foto_perfil(rut_perfil)
    solicitudes = consultar_solicitudes(rut_perfil) # Consulta las solicitudes a partir del rut
    ids = get_id_from_list_of_dictionary(solicitudes) # Obtiene las id de las solicitudes
    solicitudes_equipos = consultar_equipos_por_id_solicitudes(ids) # Obtiene todas las solicitudes de los equipos por la ID
    return render_template(
                'vistas_perfil/perfil.html',
                solicitudes = solicitudes,
                solicitudes_equipos = solicitudes_equipos,
                perfil_info = resultado_perfil,
                dir_foto_perfil = url_for('static',filename='imgs/profile_pics/'+archivo_foto_perfil),
                completar_info = False,
                admin_inspeccionar_perfil = True)



@mod.route('/perfil',  methods =['GET','POST']) # ** Importante PERFIL** #
def perfil():
    # si hay un usuario en la session carga el perfil
    if 'usuario' not in session:
        return redirect('/')
    else:
        resultado_perfil = consultar_informacion_perfil(session['usuario']['rut']) # Hace la consulta a la base sobre los datos del usuario
        validar_completar = False # Variable que sera pasada para completar la información
        # Loop para validar si es que faltan completar datos (marcados como None)
        # Si falta completar algún dato, la variable cambiará a True
        for key in resultado_perfil:
            if resultado_perfil[key] == None:
                validar_completar = True
                break

        archivo_foto_perfil = obtener_foto_perfil(session['usuario']['rut']) # obitiene la foto de perfil

        solicitudes = consultar_solicitudes(session['usuario']['rut']) # Consulta las solicitudes a partir del rut
        ids = get_id_from_list_of_dictionary(solicitudes) # Obtiene las id de las solicitudes
        solicitudes_equipos = consultar_equipos_por_id_solicitudes(ids) # Obtiene todas las solicitudes de los equipos por la ID

        # Se obtienen los mensajes administrativos registrados
        sql_query = """
            SELECT * FROM
                Mensaje_administrativo
                    ORDER BY fecha_registro DESC
        """
        cursor.execute(sql_query)
        lista_mensajes_administrativos = cursor.fetchall()

        for mensaje_administrativo in lista_mensajes_administrativos:
            mensaje_administrativo["timeago_mensaje"] = timeago.format(mensaje_administrativo["fecha_registro"], datetime.now(), 'es')
            if mensaje_administrativo["fecha_actualizacion"] is not None:
                mensaje_administrativo["timeago_ultima_actualizacion"] = timeago.format(mensaje_administrativo["fecha_actualizacion"],datetime.now(),'es')

        return render_template(
            'vistas_perfil/perfil.html',
            solicitudes = solicitudes,
            solicitudes_equipos = solicitudes_equipos,
            perfil_info = resultado_perfil,
            dir_foto_perfil = url_for('static',filename='imgs/profile_pics/'+archivo_foto_perfil),
            completar_info = validar_completar,
            admin_inspeccionar_perfil = False,
            lista_mensajes_administrativos=lista_mensajes_administrativos)


# ************Acciones de información de perfil****************
@mod.route('/perfil/actualizar_informacion', methods = ['POST']) # ** Importante CONFIGURAR PERFIL** #
def configurar_perfil():
    if 'usuario' not in session:
        return redirect('/')
    if request.method == 'POST':
        informacion_a_actualizar = request.form.to_dict()
        #print(informacion_a_actualizar)
        query = ('''
            UPDATE Usuario
            SET nombres = %s,
                apellidos = %s,
                region = %s,
                comuna = %s,
                direccion = %s,
                celular = %s
            Where Usuario.rut = %s
        ''')
        cursor.execute(query,(
            informacion_a_actualizar['nombres'],
            informacion_a_actualizar['apellidos'],
            informacion_a_actualizar['region'],
            informacion_a_actualizar['comuna'],
            informacion_a_actualizar['direccion'],
            informacion_a_actualizar['celular'],
            session['usuario']['rut']
            ))
        db.commit()
        return redirect('/')



EXTENSIONES_PERMITIDAS = ["PNG","JPG","JPEG","GIF"]
def allowed_image(filename): # funcion que valida la extension de la imagen
    if not "." in filename:
        return False

    ext = filename.rsplit(".",1)[1]
    if ext.upper() in EXTENSIONES_PERMITIDAS:
        return True
    else:
        return False


# ************Acciones de fotos de perfil****************
@mod.route('/perfil/subir_foto',methods = ['GET','POST'])
def subir_foto():
    if request.method == "POST":
            image = request.files["image"] # obtiene la imagen del formulario

            if not allowed_image(image.filename): # Comprueba la extension de la imagen
                print("extension no permitida")
                return redirect('/')

            if glob.glob(PROFILE_PICS_PATH + session['usuario']['rut'] +'.*'): # Si existe alguna foto del usuario
                filename = glob.glob(PROFILE_PICS_PATH + session['usuario']['rut'] +'.*') # Obtiene la direccion de la foto del usuario
                head, tail = os.path.split(filename[0]) # separa el nombre del archivo
                os.remove(PROFILE_PICS_PATH + tail ) # elimina el archivo

            image.filename = session['usuario']['rut'] +"." +image.filename.split('.')[1].lower() # Le da a la imagen el nombre del rut

            image.save( os.path.join( PATH+'/app/static/imgs/profile_pics', secure_filename(image.filename) ) ) # guarda la imagen en la direccion /app/static/imgs/profile_pics/

            return redirect('/')

    return redirect('/')




# ************Acciones de solicitudes de perfil****************
@mod.route('/perfil/cancelar_solicitud',methods = ['GET','POST']) # funcion para cancelar una solicitud
def cancelar_solicitud():
    if request.method == "POST":
        solicitud = request.form.to_dict()
        query = ('''
                UPDATE Detalle_solicitud
                SET Detalle_solicitud.estado = 7
                WHERE Detalle_solicitud.id = %s
                    AND Detalle_solicitud.estado = 0
                ''') # 7 == cancelado
        cursor.execute(query,(solicitud["id_solicitud_detalle"],))
        db.commit()
        return redirect('/')

    return redirect('/')



@mod.route('/perfil/extender_prestamo',methods = ['GET','POST']) # funcion para cancelar una solicitud
def extender_prestamo():
    if request.method == "POST":
        solicitud_detalle_a_extender = request.form.to_dict()

        query = ("""
                UPDATE Detalle_solicitud
                SET Detalle_solicitud.fecha_termino = DATE_ADD(Detalle_solicitud.fecha_termino, INTERVAL 7 DAY),
                Detalle_solicitud.renovaciones = Detalle_solicitud.renovaciones + 1
                WHERE Detalle_solicitud.id = %s
                    AND Detalle_solicitud.estado = 2
                """)

        cursor.execute(query,(solicitud_detalle_a_extender["id_solicitud_detalle"],))
        db.commit()

        return redirect('/')

    return redirect('/')


@mod.route('/perfil/resolicitar_equipo',methods = ['GET','POST'])
def resolicitar_equipo():
    if request.method == "POST":
        print("equipo por solicitar")
        return redirect('/')

    return redirect('/')
