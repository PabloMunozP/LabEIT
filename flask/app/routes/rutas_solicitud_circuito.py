from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify
from config import db,cursor
import os, time, bcrypt
import mysql.connector
import rut_chile
import glob

mod = Blueprint("rutas_solicitud_circuito",__name__)

def redirect_url(default='index'): # Redireccionamiento desde donde vino la request
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)




def consultar_lista_circuito():
    query = ('''
        SELECT *
        FROM Circuito
    ''')
    cursor.execute(query)
    return cursor.fetchall()


# def consultar_carro_circuitos():
#     if 'carro_circuito' not in session or len(session["carro_circuito"]) < 1:
#         return []
#     format_strings = ','.join(['%s'] * len(session["carro_circuito"]))
#     list = []
#     for element in session["carro_circuito"]:
#         list.append(element)
#     query = ('''
#         SELECT id, nombre
#         FROM Circuito
#         WHERE id IN (%s)
#     ''' % format_strings)
#     cursor.execute(query,tuple(list))
#     query_resultado = cursor.fetchall()
#     print (query_resultado)
#     return []
    
    
@mod.route("/solicitudes_prestamos_circuitos")
def gestion_solicitudes_prestamos_circuitos():
    if 'carro_circuito' in session:
        for element in session["carro_circuito"].items():
            print(element)
    
    return render_template('solicitudes_prestamos_circuitos/preview.html',
                           lista_circuitos = consultar_lista_circuito()                           )
    # lista_carro_circuitos = session
@mod.route("/debug_circuito")
def debug_circuito():
    lista_circuitos = consultar_lista_circuito()
    for i in lista_circuitos:
        print(i)
    return 'xD'



def generar_solicitud_alumno(rut_alumno, motivo): # funcion para generar la solicitud de circuitos
    # generar Detalle_solicitud_circuito
    # generar Solicitud_circuito
    query_solicitud_circuito('''
                            INSERT INTO Solicitud_circuito (rut_alumno,motivo)
                            VALUES (%s, %s)
                             ''')
    
    id_solicitud = cursor.lastrowid # Se obtiene el id de solicitud recién creada
    
    return
@mod.route("/eliminar_carro_circuito",methods=['POST'])
def eliminar_carro_circuito():
    if request.method == "POST":
        id_circuito = request.form["id_circuito"]
        print(session["carro_circuito"][id_circuito])
        del session["carro_circuito"][id_circuito]
        if len(session["carro_circuito"]) == 0:
            del session["carro_circuito"]
        return render_template("solicitudes_prestamos_circuitos/tablas/lista_carro_circuito.html")
    return jsonify({'error':'missing data!'})



@mod.route("/agregar_al_carro_circuito",methods=['POST'])
def agregar_al_carro_circuito():
    if request.method == "POST":
        id_circuito = request.form["id_circuito"]
        cantidad = request.form["cantidad"]
        nombre = request.form["nombre_circuito"]
        if id_circuito and cantidad:
            if 'carro_circuito' not in session: # si no hay carrito
                session["carro_circuito"] = {}
            
            if id_circuito not in session["carro_circuito"].keys(): # Si el circuito no esta en el carro, lo agrega
                session["carro_circuito"][id_circuito] = {} # Crea un diccionario carro = { id : {}}
                session["carro_circuito"][id_circuito]['id'] = str(id_circuito) # carro = { id : {'id': 'id'}}
                session["carro_circuito"][id_circuito]['cantidad'] = int(cantidad)  # carro = { id : {'id': str , 'cantidad' : int}}
                session["carro_circuito"][id_circuito]['nombre'] = nombre #agrega el nombre
            else: # Si el circuito está en el carro, le suma la cantidad
                session["carro_circuito"][id_circuito]['cantidad'] = int(cantidad)    
            return render_template("solicitudes_prestamos_circuitos/tablas/lista_carro_circuito.html")
        else:
            return jsonify({'error':'missing data!'})
    
    return jsonify({'error':'missing data!'})
    
    
@mod.route("/confirmar_al_carro_circuito",methods=['POST'])
def confirmar_carro_circuito():
    for i in session["carro_pedidos_circuito"]:
        print(i)
    return 'xD'