from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify
#from config import db,cursor
import os, time, bcrypt
import mysql.connector

connection = mysql.connector.connect(
    host = "localhost",
    user = "root",
    passwd = "sodasoda",
    database = "LABEIT"
)


mod = Blueprint('rutas_victor',__name__)

# Login 
@mod.route('/victor/login')
def prueba_login():
    if 'rut' in session:
        return redirect('/victor/perfil')
    return render_template('victor/user_login_form.html')

@mod.route('/victor/user_login', methods = ['POST'])
def login_session():
    if request.method == 'POST':
        # Valores obtenidos por el metodo 
        rut_entrada = request.form.get('rut')
        contraseña_entrada = request.form.get('contraseña')
        print('usuario: ', rut_entrada)
        print('contraseña: ', contraseña_entrada)
        
        # Query donde se obtienen los datos del usuario
        query = ('''
            SELECT 
                rut,
                contraseña, 
                credencial 
            FROM Usuario
            WHERE rut = %s;
        ''')
        cursor = connection.cursor()
        cursor.execute(query, (rut_entrada,))
        resultado = cursor.fetchall()


        # Si los datos para ingresar son incorrectos redirigira al login con un error
        if (resultado == []):    
            flash('El usuario o la contraseña no son validos')
            return redirect('/victor/login')
        # Si la contraseña es correctoa guarda los 
        elif bcrypt.checkpw(contraseña_entrada.encode('utf-8'), resultado[0][1].encode('utf-8')):
            session['rut'] = rut_entrada
            session['credencial'] = resultado[0][2]
            return redirect('/victor/login')
        else:
            flash('El usuario o la contraseña no son validos')
            return redirect('/victor/login')


@mod.route('/victor/perfil')
def perfil():
    if 'rut' in session:
        return render_template('victor/perfil.html')

    else: 
        return redirect('/victor/login')







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
            INSERT INTO Usuario (rut, contraseña, email, credencial) 
            VALUES (%s, %s, %s, %s)
        '''
        cursor = connection.cursor()
        cursor.execute( query, 
            ( rut_entrada, 
            contraseña_encriptada, 
            email_entrada, 
            int(credencial_entrada)
            ))

        connection.commit()
        return redirect('/victor/user_add_form')






