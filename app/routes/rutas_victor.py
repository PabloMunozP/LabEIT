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

mod = Blueprint('rutas_victor',__name__)

@mod.route('/victor/login')
def validar_session():

    # Si hay una sesion entra al perfil
    if 'usuario' in session:
        return redirect('/perfil')

    # Si no hay sesion redirecciona al login
    else:
        return render_template('victor/user_login_form.html')




# Perfil del usuario

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

        # Query de prestamos alumno
        # En esta Query la tabla dominante es Solicitud pero muestra la parte de Detalle
        query_prestamos = ('''
            SELECT
                Solicitud.fecha_registro AS fecha_registro_solicitud,
                Detalle_solicitud.id_equipo,
                Detalle_solicitud.fecha_inicio AS fecha_entrega_equipo,
                Detalle_solicitud.fecha_devolucion AS fecha_devolucion_equipo,
                Usuario.nombres AS profesor_nombres,
                Usuario.apellidos AS profesor_apellidos
            FROM
                Solicitud JOIN
                Detalle_solicitud ON Detalle_solicitud.id_solicitud = Solicitud.id JOIN
                Usuario ON Usuario.rut = Solicitud.rut_profesor
            WHERE 
                Solicitud.rut_alumno = %s
            ;
        ''')
                #         Usuario.nombres AS profesor_nombres,
                # Usuario.apellidos AS profesor_apellidos,
                
        cursor.execute(query_prestamos,(session['usuario']['rut'],))
        resultado_prestamos = cursor.fetchall()
        for i in range(len(resultado_prestamos)):
            print('PRESTAMOS',resultado_prestamos[i])


        return render_template(
            'victor/perfil.html',
            perfil_info = resultado_perfil,
            dir_foto_perfil = archivo_foto_perfil,
            completar_info = validar_completar,
            prestamos_info = resultado_prestamos)
    

# Configurar perfil # ** Importante MODAL PERFIl ** #
@mod.route('/perfil/actualizar_informacion', methods = ['POST']) # ** Importante CONFIGURAR PERFIL** #
def configurar_perfil():
    if 'usuario' not in session:
        return redirect('/')
    if request.method == 'POST':
        informacion_a_actualizar = request.form.to_dict()
        print(informacion_a_actualizar)
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


# Formulario para agregar usuario
@mod.route('/victor/user_add_form')
def add_user():
    return render_template('victor/user_add_form.html')


# Recibe formulario de add_user()
@mod.route('/victor/añadir/usuario', methods = ['POST'])
def add_user2():
    if request.method == 'POST':
        rut_entrada = request.form.get('rut')
        contraseña_entrada = request.form.get('contraseña').encode('utf-8')
        contraseña_encriptada = bcrypt.hashpw(contraseña_entrada, bcrypt.gensalt()).decode('utf-8')
        email_entrada = request.form.get('email')
        credencial_entrada = request.form.get('credencial')
        print(rut_entrada, email_entrada, contraseña_encriptada, credencial_entrada)

        # Query para insertar valores en Usuario
        query = '''
            INSERT INTO Usuario (rut, contraseña, email, id_credencial) 
            VALUES (%s, %s, %s, %s)
        '''
        cursor = db.cursor()
        cursor.execute( query, 
            ( rut_entrada, 
            contraseña_encriptada, 
            email_entrada, 
            int(credencial_entrada)
            ))
        db.commit()
        return redirect('/victor/user_add_form')







