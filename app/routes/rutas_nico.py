from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify
from config import db,cursor
import os,time,bcrypt

def redirect_url(default='index'): # Redireccionamiento desde donde vino la request
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

mod = Blueprint("rutas_nico",__name__)

@mod.route("/nico",methods=["GET"])
def principal():
    return "OK"



# Consulta una lista con los equipos
# Es usada en la vista general de todos los equipos
def consultar_lista_equipos_general(ask_print = False):
    query = ('''
        SELECT
            Equipo.id,
            Equipo.codigo,
            Equipo.modelo,
            Equipo.marca,
            Equipo.descripcion,
            Equipo.dias_max_prestamo,
            COUNT(CASE WHEN Equipo_diferenciado.activo = 1 THEN 1 ELSE NULL END) AS disponibles, 
            COUNT(Equipo_diferenciado.activo) AS total_equipos
        FROM 
            Equipo
            LEFT JOIN Equipo_diferenciado ON Equipo_diferenciado.codigo_equipo = Equipo.codigo
        GROUP BY Equipo.codigo
    ''')
    cursor.execute(query)
    equipos = cursor.fetchall()
    if ask_print == True:
        print('################')
        for i in range(len(equipos)):
            print(i, equipos[i])
        print('################')
    return equipos

# Consulta una una lista de equipos especificos
# Es usada en la vista de equipos asociados
# Ejemplo: Solo ARDUINO UNO
def consultar_lista_equipos_detalle(codigo_equipo, ask_print = False):
    query = ('''
        SELECT *
        FROM Equipo_diferenciado
        WHERE Equipo_diferenciado.codigo_equipo = %s
    '''
    )
    cursor.execute(query,(codigo_equipo,))
    equipos_detalle = cursor.fetchall()
    if ask_print == True:
        print('################')
        print(equipos_detalle)
        print('################')
    return equipos_detalle


# Agrega un tipo de equipo con sus datos generales
def insertar_lista_equipos_general(valores_a_insertar):
    query = ('''
        INSERT INTO Equipo (codigo, modelo, marca, descripcion, dias_max_prestamo, adquiridos, codigo_sufijo)
        VALUES (%s, %s, %s, %s ,%s, %s, %s);
    ''')
    cursor.execute(query,(
        valores_a_insertar['codigo'],
        valores_a_insertar['modelo'],
        valores_a_insertar['marca'],
        valores_a_insertar['descripcion'],
        valores_a_insertar['dias_maximo_prestamo'],
        valores_a_insertar['adquiridos'],
        valores_a_insertar['codigo_sufijo']))

    db.commit()
    return 'OK'

@mod.route("/gestion_inventario_admin")
def gestion_inventario_admin():
    equipos = consultar_lista_equipos_general(True)
    equipos_detalle = consultar_lista_equipos_detalle('AAXDAA',True)
     
    # return 'Ok'
    # return render_template('vistas_gestion_inventario/gestion_inventario.html')
    return render_template('pruebas/inventario.html', lista_equipo = equipos)

@mod.route("/gestion_inventario_admin/<string:codigo_equipo>")
def gestion_inventario_admin_equipo(codigo_equipo):
    equipos = consultar_lista_equipos_detalle(codigo_equipo,True)
    return render_template('pruebas/inventario_copy.html', equipos_detalle = equipos)



@mod.route("/form_add_inventario")
def añadir_equipo_form():
    return render_template('pruebas/form_inventario.html')

@mod.route("/validar_form_add_inventario", methods = ['POST'])
def funcion_añadir_equipo_form():
    if request.method == 'POST':
        informacion_a_insertar = request.form.to_dict()
        print(informacion_a_insertar)
        insertar_lista_equipos_general(informacion_a_insertar)
        return 'OK'