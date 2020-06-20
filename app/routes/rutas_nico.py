from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify
from config import db,cursor
import os,time,bcrypt
from datetime import datetime

def redirect_url(default='index'): # Redireccionamiento desde donde vino la request
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

mod = Blueprint("rutas_nico",__name__)

@mod.route("/nico",methods=["GET"])
def principal():
    return "OK"
# ************************************************************* #
# *                   IMPORTANTE FUNCIONES                    * #
# ************************************************************* #

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

 # ** Importante CONFIGURAR EQUIPO** #

def editar_equipo_general(informacion_a_actualizar):
        query = ('''
            UPDATE Equipo
            SET codigo = %s,
                modelo = %s,
                marca = %s,
                descripcion = %s,
                dias_max_prestamo = %s,
                adquiridos = %s
            Where Equipo.codigo = codigo_equipo
        ''')
        cursor.execute(query,(
            informacion_a_actualizar['codigo'],
            informacion_a_actualizar['modelo'],
            informacion_a_actualizar['marca'],
            informacion_a_actualizar['descripcion'],
            informacion_a_actualizar['dias_max_prestamo'],
            informacion_a_actualizar['adquiridos']
            ))
        db.commit()
        return informacion_a_actualizar

# Agrega un tipo de equipo con sus datos generales
def insertar_lista_equipos_general(valores_a_insertar):
    query = ('''
        INSERT INTO Equipo (codigo, modelo, marca, descripcion, dias_max_prestamo, adquiridos)
        VALUES (%s, %s, %s, %s ,%s, %s);
    ''')
    cursor.execute(query,(
        valores_a_insertar['codigo'],
        valores_a_insertar['modelo'],
        valores_a_insertar['marca'],
        valores_a_insertar['descripcion'],
        valores_a_insertar['dias_maximo_prestamo'],
        valores_a_insertar['adquiridos']))
    db.commit()
    return 'OK'

# Agrega un equipo a partir de la relacion que que tenga
def insertar_lista_equipos_detalle(codigo_equipo, valores_a_insertar):
    query = ('''
        INSERT INTO Equipo_diferenciado (codigo_equipo, codigo_sufijo, fecha_compra, activo)
        VALUES (%s, %s, %s, %s);
    ''')
    cursor.execute(query,(
        codigo_equipo,
        valores_a_insertar['codigo_sufijo'],
        valores_a_insertar['fecha_compra'],
        valores_a_insertar['activo']))
    db.commit()
    return 'OK'
# ************************************************************* #
# *                                                           * #
# ************************************************************* #

# ** Importante VISTA PRINCIPAL GESTION INVENTARIO ** #
@mod.route("/gestion_inventario_admin")
def gestion_inventario_admin():
    equipos = consultar_lista_equipos_general(True)
    return render_template('vistas_gestion_inventario/gestion_inventario.html', lista_equipo = equipos)


# ** Importante VISTA GESTION INVENTARIO DIFERENCIADO ** #
@mod.route("/gestion_inventario_admin/<string:codigo_equipo>")
def gestion_inventario_admin_equipo(codigo_equipo):
    equipos = consultar_lista_equipos_detalle(codigo_equipo,True)
    return render_template('vistas_gestion_inventario/similares_tabla.html', equipos_detalle = equipos) #Cambiar render por el que corresponda

# ** VALIDA FORMULARIO DE PRUEBA INGRESAR EQUIPO ** #
# ** BORRAR ANTES DE PRODUCCION ** #
@mod.route("/gestion_inventario_admin/form/<string:codigo_equipo>")
def form_añadir_equipo_espeficio(codigo_equipo):
    return render_template('pruebas/form_inventario.html',codigo_equipo = codigo_equipo)

# ** Importante FUNCION() QUE INGRESA LOS VALORES DE FORMULARIO "AGREGAR" EN VISTA PRINCIPAL DE GESTION INVENTARIO ** #
@mod.route("/validar_form_add_inventario", methods = ['POST'])
def funcion_añadir_equipo_form():
    if request.method == 'POST':
        informacion_a_insertar = request.form.to_dict()
        insertar_lista_equipos_general(informacion_a_insertar)
        flash("El equipo fue agregado correctamente")
        equipos = consultar_lista_equipos_general(True)
        return render_template('vistas_gestion_inventario/gestion_inventario.html', lista_equipo= equipos)

@mod.route('/gestion_inventario_admin/actualizar_informacion/<string:codigo_equipo>', methods = ['POST'])
def funcion_editar_equipo_form(codigo_equipo):
    if request.method == 'POST':
        informacion_a_actualizar = request.form.to_dict()
        insertar_lista_equipos_general(informacion_a_actualizar)
        flash("El equipo se actualizo")
        equipos = consultar_lista_equipos_general(True)
        return render_template('vistas_gestion_inventario/gestion_inventario.html', lista_equipo= equipos)
# Importante FUNCION() ENCARGADA DE INGRESAR LOS VALORES DEL FORMULARIO "AGREGAR" EN VISTA GESTION INVENTARIO DIFERENCIAD0 ** #

@mod.route("/gestion_inventario_admin/validar_add/form/<string:codigo_equipo>", methods = ['POST'])
def validar_form_añadir_equipo_espeficio(codigo_equipo):
    if request.method == 'POST':
        print(codigo_equipo)
        informacion_a_insertar = request.form.to_dict()
        dateTimeObj = datetime.now()
        informacion_a_insertar['fecha_compra'] = dateTimeObj # cambiar despues
        insertar_lista_equipos_detalle(codigo_equipo, informacion_a_insertar)
        flash("El equipo fue agregado correctamente")
        return redirect("/gestion_inventario_admin/form/"+codigo_equipo) #Cambiar a redirect VISTA GESTION INVENTARIO DIFERENCIAD0
                                                                         # mantener " + codigo_equipo"
