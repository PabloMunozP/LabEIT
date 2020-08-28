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


@mod.route("/agregar_al_carro_circuito",methods=['POST'])
def agregar_al_carro_circuito():
    datos_circuito_pedido = request.form.to_dict()
    
    print(datos_circuito_pedido)
    if "carro_pedidos_circuito" not in session.keys(): # crea la sesion
        session["carro_pedidos_circuito"] = {}
    
    if str(datos_circuito_pedido["id_circuito"]) in session["carro_pedidos_circuito"].keys(): # si ya hay le suma
        session["carro_pedidos_circuito"][str(datos_circuito_pedido["id_circuito"])] = int(datos_circuito_pedido["cantidad_unidades_solicitadas"]) + int(session["carro_pedidos_circuito"][str(datos_circuito_pedido["id_circuito"])])
    else:
        session["carro_pedidos_circuito"][str(datos_circuito_pedido["id_circuito"])] = int(datos_circuito_pedido["cantidad_unidades_solicitadas"]) # si no se crea y le agrega un valor
    print(session["carro_pedidos_circuito"])
    
    return render_template("/solicitudes_prestamos_circuitos/tablas/lista_carro_circuito.html")

    # return render_template("/solicitudes_prestamos/seccion_carro_pedidos.html",
    #     lista_carro=lista_carro)