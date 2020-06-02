from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify
from config import db,cursor
import os,time,bcrypt

mod = Blueprint("rutas_pablo",__name__)

@mod.route("/pablo",methods=["GET"])
def principal():
    return "OK"


@mod.route("/ver_usuario",methods=['GET'])
def ver_usuarios():
    query= """ SELECT Usuario.nombres as nombres, Usuario.apellidos as apellidos, Usuario.rut as rut, Credencial.nombre as credencial FROM Usuario, Credencial WHERE Usuario.id_credencial=Credencial.id"""
    cursor=db.cursor()
    cursor.execute(query)
    usuarios=cursor.fetchall()
    return render_template("/pablo/ver_usuarios.html",usuarios=usuarios)


@mod.route("/anadir_usuario",methods=["GET","POST"])
def añadir_usuario():
    if request.method=='POST':
        datos_usuario=request.form.to_dict()#obtener datos del usuario en un diccionario
        cursor = db.cursor()
        #print(datos_usuario)
        #Verificar que el usuario no exista previamente
        existe="""SELECT * FROM Usuario WHERE rut=%s"""
        cursor.execute(existe,(datos_usuario['rut'],))
        if cursor.fetchone() is None:#el usuario no existe   
            #se agrega al usuario
            query= """ INSERT INTO Usuario (rut, id_credencial, email, nombres, apellidos) 
            VALUES (%s , %s, %s, %s, %s) """
            cursor.execute(query,(datos_usuario['rut'],datos_usuario['credencial'],datos_usuario['correo'],datos_usuario['nombres'],datos_usuario['apellidos'],))        
            return redirect(url_for("rutas_pablo.ver_usuario"))
        #el usuario existe:
        flash("usuario_existe")
        return redirect(url_for("rutas_pablo.añadir_usuario"))
        
    elif request.method=='GET':
       return render_template("/pablo/añadir_usuario.html")
   
   
@mod.route("/editar_usuario/<string:rut>",methods=['GET','POST'])
def editar(rut=None):
    if request.method =='GET' :
        if rut:
            query=('''SELECT * FROM Usuario WHERE rut= %s''')
            cursor = db.cursor()
            cursor.execute(query, (rut,))
            resultado = cursor.fetchall()
            print(resultado[0])
            if(resultado==[]):
                return render_template("/pablo/editar_usuario.html",msg='No existe ese alumno')
            elif(resultado[0][0]==rut):
                credencial= 'Alumno' if resultado[0][1]== 1 else 'Profesor' if resultado[0][1] == 2 else 'Administrador' if resultado[0][1] == 3 else None
                return render_template("/pablo/editar_usuario.html",datos=resultado[0],credencial=credencial)
        else:
            return render.template("/pablo/editar_usuario.html",msg='Error en el rut')
    elif request.method=='POST':
        datos_usuario=request.form.to_dict()
        print(datos_usuario)
        

       