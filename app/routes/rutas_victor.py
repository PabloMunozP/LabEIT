from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify
from config import db,cursor
import os, time, bcrypt
import mysql.connector



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

# Validador de login

@mod.route('/victor/user_login', methods = ['POST'])
def login_session():
    if request.method == 'POST':
        
        # Valores obtenidos por el metodo 
        rut_entrada = request.form.get('rut')
        contraseña_entrada = request.form.get('contraseña')
        
        # Query donde se obtienen los datos del usuario
        query = ('''
            SELECT 
                rut,
                contraseña, 
                id_credencial 
            FROM Usuario
            WHERE rut = %s;
        ''')
        cursor.execute(query, (rut_entrada,))
        resultado = cursor.fetchall()


        # Si los datos para ingresar son incorrectos redirigira al login con un error
        if (resultado == []):    
            flash('El usuario o la contraseña no son validos')
            return redirect('/victor/login')
        # Si la contraseña es correctoa guarda los 
        elif bcrypt.checkpw(contraseña_entrada.encode('utf-8'), resultado[0][1].encode('utf-8')):
            session['rut'] = rut_entrada
            session['id_credencial'] = resultado[0][2]
            return redirect('/victor/login')
        else:
            flash('El usuario o la contraseña no son validos')
            return redirect('/victor/login')


@mod.route('/perfil')
def perfil():
    # si hay un usuario en la session
    if 'usuario' in session:
        query_perfil = ('''
            SELECT
                id_credencial,
                rut,
                email,
                nombres,
                apellidos,
                region,
                ciudad,
                comuna,
                direccion,
                fecha_registro,
                foto           
            FROM Usuario
            WHERE rut = %s
        ''')
        cursor.execute(query_perfil,(session['usuario']['rut'],))
        resultado_perfil = cursor.fetchone()
        for key in resultado_perfil:
            print(resultado_perfil[key])
        print('resultado: ', resultado_perfil)
        return render_template('victor/perfil.html', perfil_info = resultado_perfil)
    else: 
        return redirect('/victor/back_login') # ** cambiar url en produccion ** 



# ********** borrar ante de producción ************************ #
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







