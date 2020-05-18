from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify
from config import db,cursor
import os, time, bcrypt

mod = Blueprint('rutas_victor',__name__)

# Formulario para agregar usuario
@mod.route('/victor/user_add_form')
def add_user():
    return render_template('victor/user_add_form.html')
# Agrega
@mod.route('/victor/añadir/usuario', methods = ['POST'])
def add_user2():
    if request.method == 'POST':
        rut = request.form['rut']
        contraseña = request.form['contraseña']
        email = request.form['email']
        credencial = request.form['credencial']
        print(rut, email, credencial)
        return redirect('/')


#Login para mantener datos de sesion
@mod.route('/victor/login')
def prueba_login():
    return render_template('victor/user_login_form.html')

@mod.route('/victor/user_login', methods = ['POST'])
def login_session():
    if request.method == 'POST':
        # Valores obtenidos por el metodo
        rut_entrada = request.form['rut']
        contraseña_entrada = request.form['contraseña']
        print('usuario: ', rut_entrada)
        print('contraseña: ', contraseña_entrada)

        # Query donde se obtienen los datos del usuario
        query = ('''
            SELECT
                rut,
                contraseña,
                credencial,
                email
            FROM Usuario
            WHERE rut = %s;
        ''')
        cursor = connection.cursor()
        cursor.execute(query, (rut_entrada,))
        resultado = cursor.fetchall()
        # Si los datos para ingresar son incorrectos redirigira al login y enviara un mensaje
        if (resultado == []):
            flash('El usuario o la contraseña estan mal xD')
            return redirect('/victor/login')

        # Si la contraseña es incorrecta
        elif (contraseña_entrada != resultado[0][1] ):
            flash('El usuario o la contraseña estan mal xD')
            return redirect('/victor/login')
        else:
            return 'perfil'
    return 'OK'
