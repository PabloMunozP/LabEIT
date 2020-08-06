from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify,send_from_directory
from config import db,cursor, BASE_DIR
from werkzeug.utils import secure_filename
import os, time, bcrypt
import mysql.connector
import rut_chile
import glob
import platform

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

def consultar_solicitudes_alumno(rut_alumno): # Query para poder consultar las solicitudes
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
    cursor.execute(query,(rut_alumno,))
    query_solicitud = cursor.fetchall()
    return query_solicitud

def consultar_equipos_solicitudes_alumno(list_id_solicitudes): # Query para consultar todos los equipos en relacion a las solicitudes
    if len(list_id_solicitudes) < 1:
        return []
        
    format_strings = ','.join(['%s'] * len(list_id_solicitudes)) # Genera un string para la query
    query = ('''
        SELECT Detalle_solicitud.id_solicitud,
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
        # Funcion que verifica si existe la foto de perfil
        # Las fotos puedes estar guardadas en cualquier tipo de extension
        # Si existe una foto para del usuario obtiene el nombre del archivo + extension
        if glob.glob(PROFILE_PICS_PATH + session['usuario']['rut'] +'.*'):
            filename = glob.glob(PROFILE_PICS_PATH + session['usuario']['rut'] +'.*')
            head, tail = os.path.split(filename[0])
            archivo_foto_perfil = tail
        else:
            archivo_foto_perfil = 'default_pic.png'
        solicitudes = consultar_solicitudes_alumno(session['usuario']['rut']) # Consulta las solicitudes a partir del rut
        ids = get_id_from_list_of_dictionary(solicitudes) # Obtiene las id de las solicitudes
        solicitudes_equipos = consultar_equipos_solicitudes_alumno(ids) # Obtiene todas las solicitudes de los equipos

        return render_template(
            'vistas_perfil/perfil.html',
            solicitudes = solicitudes,
            solicitudes_equipos = solicitudes_equipos,
            perfil_info = resultado_perfil,
            dir_foto_perfil = url_for('static',filename='imgs/profile_pics/'+archivo_foto_perfil),
            completar_info = validar_completar)
    
 
# Configurar perfil # ** Importante MODAL PERFIl ** #
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


@mod.route('/debug')
def debug():
    return 'XD'



EXTENSIONES_PERMITIDAS = ["PNG","JPG","JPEG","GIF"]
def allowed_image(filename): # funcion que valida la extension de la imagen
    if not "." in filename:
        return False
    
    ext = filename.rsplit(".",1)[1] 
    if ext.upper() in EXTENSIONES_PERMITIDAS:
        return True
    else:
        return False



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
                os.remove(PROFILE_PICS_PATH + tail ) 
            
            image.filename = session['usuario']['rut'] +"." +image.filename.split('.')[1].lower() # Le da a la imagen el nombre del rut
            
            image.save( os.path.join( PATH+'/app/static/imgs/profile_pics', secure_filename(image.filename) ) ) # guarda la imagen en la direccion /app/static/imgs/profile_pics/

            return redirect('/')
    
    return redirect('/')