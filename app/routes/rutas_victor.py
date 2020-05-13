from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify
#from config import db,cursor
import os,time,bcrypt
import mysql.connector

connection = mysql.connector.connect(
    host = "localhost",
    user = "root",
    passwd = "sodasoda",
    database = "LABEIT"
)



mod = Blueprint('rutas_victor',__name__)

@mod.route('/victor/login')
def prueba_login():
    return render_template('victor/user_login_form.html')


@mod.route("/victor",methods=["GET"])
def principal():
    select_query = "SELECT * from Usuario"
    cursor = connection.cursor()
    cursor.execute(select_query)
    records = cursor.fetchall()
    for i in range(len(records)):
        print("records:", records[i][0])
    return records[0][0]

@mod.route('/victor/user_add_form')
def add_user():
    return render_template('victor/user_add_form.html')

@mod.route('/victor/añadir/usuario', methods = ['POST'])
def add_user2():
    if request.method == 'POST':
        rut = request.form['rut']
        contraseña = request.form['contraseña']
        email = request.form['email']
        credencial = request.form['credencial']
        print(rut, email, credencial)
        return redirect('/')