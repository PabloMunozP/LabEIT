from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify
from config import db,cursor
import os,time,bcrypt

def redirect_url(default='index'): # Redireccionamiento desde donde vino la request
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

mod = Blueprint("rutas_pablo",__name__)

@mod.route("/pablo",methods=["GET"])
def principal():
    return "OK"


@mod.route("/anadir_usuario",methods=["GET"])
def ver_añadir():
    return render_template("/pablo/añadir_usuario.html")

@mod.route("/anadir_usuario",methods=["POST"])
def añadir_usuario():
       datos_usuario=request.form.to_dict()#obtener datos del usuario en un diccionario
       print(datos_usuario)
       return 'OK'

@mod.route("/editar_usuario/<string:rut>",methods=["GET","POST"])
def editar(rut=None):
    if request.method=='GET':
        if rut:
            query=('''SELECT * FROM Usuario WHERE rut= %s''')
            cursor = db.cursor()
            cursor.execute(query, (rut,))
            resultado = cursor.fetchall()
            print(resultado[0])
            if(resultado==[]):
                return render_template("/pablo/editar_usuario.html",msg='No existe ese alumno')
            elif(resultado[0][0]==rut):
                credencial= 'Alumno' if resultado[0][1]== 3 else 'Profesor' if resultado[0][1] == 2 else 'Administrador' if resultado[0][1] == 1 else None
                return render_template("/pablo/editar_usuario.html",datos=resultado[0],credencial=credencial)
        else:
            return render.template("/pablo/editar_usuario.html",msg='Error en el rut')
    elif request.method=='POST':
        datos_usuario=request.form.to_dict()
