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
                fecha_registro      
            FROM Usuario
            LEFT JOIN Credencial
            ON Credencial.id = Usuario.id_credencial
            WHERE rut = %s
        ''')
        cursor.execute(query_perfil,(session['usuario']['rut'],))
        resultado_perfil = cursor.fetchone()
        resultado_perfil['rut'] = rut_chile.formato_rut(resultado_perfil['rut'])# Le da formato al rut como "12.345.678-9"

        for key in resultado_perfil:
            print(resultado_perfil[key])
        
        print('resultado: ', resultado_perfil)
        return render_template('victor/perfil.html', perfil_info = resultado_perfil)
    else: 
        return redirect('/victor/back_login') # ** cambiar url en produccion ** 

# Configurar perfil
@mod.route('/perfil/configurar') # ** Importante CONFIGURAR PERFIL** #
def configurar_perfil():
    if 'usuario' in session:
        return render_template('victor/configurar_perfil.html')
    else:
        return redirect('/')


# ********** borrar antes de producción ************************ #
# puerta trasera de login 
@mod.route('/victor/back_login')
def back_login():
    return render_template('victor/back_login.html')

# Validador del login
@mod.route('/victor/validar_back_login', methods = ['POST'])
def validar_back_login():
    datos_login=request.form.to_dict()
    print(datos_login)
    query = ('''
            SELECT
                id_credencial,
                rut       
            FROM Usuario
            WHERE rut = %s
        ''') % (datos_login['rut'])
    cursor.execute(query)
    resultado = cursor.fetchone()
    print(resultado)
    session['usuario'] = {}
    session['usuario']['rut'] = resultado['rut']
    session['usuario']['id_credencial'] = resultado ['id_credencial']

    print('session:', session)
    return redirect('/perfil')

# ************************************************************** #

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







