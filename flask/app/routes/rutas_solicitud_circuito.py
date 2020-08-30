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

@mod.route("/gestion_solicitudes_prestamos_circuitos")
def gestion_solicitudes_prestamos_circuitos():
    
    return render_template('solicitudes_prestamos_circuitos/preview.html',
                           lista_circuitos = consultar_lista_circuito())
    
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

@mod.route("/agregar_al_carro_circuito",methods=['POST'])
def agregar_al_carro_circuito():
    if request.method == "POST":
        id_circuito = request.form["id_circuito"]
        cantidad = request.form["cantidad"]
        
        if id_circuito and cantidad:
            if 'carro_circuito' not in session: # si no hay carrito
                session["carro_circuito"] = {}
            
            if id_circuito not in session["carro_circuito"].keys(): # Si el circuito no esta
                session["carro_circuito"][id_circuito] = {} # Crea un diccionario carro = { id : {}}
                session["carro_circuito"][id_circuito]['id'] = str(id_circuito) # carro = { id : {'id': 'id'}}
                session["carro_circuito"][id_circuito]['cantidad'] = int(cantidad)  # carro = { id : {'id': str , 'cantidad' : int}}
                print(session["carro_circuito"])            
                return jsonify({id_circuito : {'id_circuito': id_circuito, 'cantidad' : cantidad }})
            else:
                session["carro_circuito"][id_circuito]['cantidad'] = int(session["carro_circuito"][id_circuito]['cantidad']) + int(cantidad) 
                return jsonify({id_circuito : {'id_circuito': id_circuito, 'cantidad' : cantidad }})
                print(session["carro_circuito"])    
                # carro = { id : {'id': str , 'cantidad' : int + int}}
        else:
            return jsonify({'error':'missing data!'})
    
    return None
    
    # print(datos_circuito_pedido)
    # if "carro_pedidos_circuito" not in session.keys(): # crea la sesion
    #     session["carro_pedidos_circuito"] = {}
    
    # if str(datos_circuito_pedido["id_circuito"]) in session["carro_pedidos_circuito"].keys(): # si ya hay le suma
    #     session["carro_pedidos_circuito"][str(datos_circuito_pedido["id_circuito"])] = int(datos_circuito_pedido["cantidad_unidades_solicitadas"]) + int(session["carro_pedidos_circuito"][str(datos_circuito_pedido["id_circuito"])])
    # else:
    #     session["carro_pedidos_circuito"][str(datos_circuito_pedido["id_circuito"])] = int(datos_circuito_pedido["cantidad_unidades_solicitadas"]) # si no se crea y le agrega un valor
    # print(session["carro_pedidos_circuito"])
    
    # return render_template("/solicitudes_prestamos_circuitos/tablas/lista_carro_circuito.html")

    # return render_template("/solicitudes_prestamos/seccion_carro_pedidos.html",
    #     lista_carro=lista_carro)
    
@mod.route("/confirmar_al_carro_circuito",methods=['POST'])
def confirmar_carro_circuito():
    for i in session["carro_pedidos_circuito"]:
        print(i)
    return 'xD'