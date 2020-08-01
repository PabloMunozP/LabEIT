from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify
from config import db,cursor
import os, time, bcrypt
import mysql.connector
import rut_chile
import glob

def redirect_url(default='index'): # Redireccionamiento desde donde vino la request
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

mod = Blueprint('rutas_perfil',__name__)


# Quuery de solicitudes de equipos del usuario
def consultar_solicitudes_alumno_compuesta(rut_alumno):
    query = ('''
            SELECT Detalle_solicitud.id_solicitud,
                Solicitud.rut_alumno,    
                Solicitud.rut_profesor,
                Solicitud.motivo,
                Solicitud.fecha_registro,
                Detalle_solicitud.id_equipo,
                Equipo.codigo,
                Equipo.nombre,
                Equipo.modelo,
                Equipo.marca,
                Estado_detalle_solicitud.nombre AS estado
            FROM Solicitud
            RIGHT JOIN Detalle_solicitud ON Detalle_solicitud.id_solicitud = Solicitud.id
            LEFT JOIN Estado_detalle_solicitud ON Estado_detalle_solicitud.id = Detalle_solicitud.estado
            LEFT JOIN Equipo ON Equipo.id = Detalle_solicitud.id_equipo 
            
            WHERE Solicitud.rut_alumno = %s
        ''')
    cursor.execute(query,(rut_alumno,))
    query_solicitud = cursor.fetchall()
    return query_solicitud


@mod.route('/debug_sol_query') # link para hacer debug de la query
def debug_sol_query():
    solicitudes = consultar_solicitudes_alumno_compuesta("198182354")
    for i in solicitudes:
        print(i)
    return 'debug_sol_query'


@mod.route('/perfil') # ** Importante PERFIL** #
def perfil():
    # si hay un usuario en la session carga el perfil
    if 'usuario' not in session:
        return redirect('/')
    # Query para obtener datos del perfil
    else:
        query_perfil = ('''
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
        cursor.execute(query_perfil,(session['usuario']['rut'],))
        resultado_perfil = cursor.fetchone()
        resultado_perfil['rut'] = rut_chile.formato_rut(resultado_perfil['rut']) # Le da formato al rut como "12.345.678-9"

        
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
        if glob.glob(os.getcwd()+'/app/static/imgs/profile_pics/'+ session['usuario']['rut'] +'.*'):
            filename = glob.glob(os.getcwd()+'/app/static/imgs/profile_pics/'+ session['usuario']['rut'] +'.*')
            head, tail = os.path.split(filename[0])
            archivo_foto_perfil = tail
        else:
            archivo_foto_perfil = 'default_pic.png'

        # print(archivo_foto_perfil)         
        # print('resultado: ', resultado_perfil)


        return render_template(
            'vistas_perfil/perfil.html',
            perfil_rut = session['usuario']['rut'],
            perfil_info = resultado_perfil,
            dir_foto_perfil = archivo_foto_perfil,
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









