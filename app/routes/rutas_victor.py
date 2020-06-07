from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify
from config import db,cursor
import os, time, bcrypt
import mysql.connector
import rut_chile 

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
    if 'usuario' in session:
    # Query para obtener datos del perfil
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

        # For para validar si es que faltan completar datos
        validar_completar = False # Variable que sera pasada para completar la informacion
        for key in resultado_perfil:
            if resultado_perfil[key] == None:
                validar_completar = True
                break

                
        print('resultado: ', resultado_perfil)
        return render_template('victor/perfil.html', perfil_info = resultado_perfil, completar_info = validar_completar)
    else: 
        return redirect('/')

# Configurar perfil
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







