from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify
from config import db,cursor
import os,time,bcrypt
from datetime import datetime

def redirect_url(default='index'): # Redireccionamiento desde donde vino la request
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

mod = Blueprint("rutas_nico",__name__)

#*********************************************************************************************#

# ***** Importante VISTA PRINCIPAL GESTION INVENTARIO **** #


# Consulta una lista con los equipos
# Es usada en la vista general de todos los equipos
def consultar_lista_equipos_general():
    # Nota importante:
    # actualizar la query papra definir equipos_disponibles y total_equipos
    query = ('''
        SELECT
            Equipo.id,
            Equipo.codigo,
            Equipo.modelo,
            Equipo.marca,
            Equipo.descripcion,
            Equipo.dias_max_prestamo,
            Equipo.imagen,
            CASE    WHEN Equipo.cantidad_circuito IS NOT NULL THEN 'true'
                    ELSE 'false'
                    END AS multi_componente,
            CASE    WHEN Equipo.cantidad_circuito IS NOT NULL THEN Equipo.cantidad_circuito
                    ELSE COUNT(CASE WHEN Equipo_diferenciado.activo = 1 THEN 1 ELSE NULL END)
                    END AS disponibles,
            CASE    WHEN Equipo.cantidad_circuito IS NOT NULL THEN Equipo.cantidad_circuito
                    ELSE COUNT(Equipo_diferenciado.activo)
                    END AS total_equipos
            FROM
                Equipo
                LEFT JOIN Equipo_diferenciado ON Equipo_diferenciado.codigo_equipo = Equipo.codigo
            GROUP BY Equipo.codigo
    ''')
    cursor.execute(query)
    equipos = cursor.fetchall()
    return equipos

def consultar_equipo_unico(codigo):
    query = ('''
        SELECT *
        FROM Equipo
        WHERE Equipo.codigo = %s
    '''
    )
    cursor.execute(query,(codigo,))
    equipo_detalle = cursor.fetchall()
    return equipo_detalle


@mod.route("/gestion_inventario_admin")
def gestion_inventario_admin():
    if 'usuario' not in session or session["usuario"]["id_credencial"] != 3:
        return redirect('/')
    else:
        equipos = consultar_lista_equipos_general()
        return render_template('vistas_gestion_inventario/gestion_inventario.html', lista_equipo = equipos)


# **** VISTA_PRINCIPAL/MODAL "AGREGAR EQUIPO" **** #

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

@mod.route("/validar_form_add_inventario", methods = ['POST'])
def funcion_añadir_equipo_form():
    if request.method == 'POST':
        informacion_a_insertar = request.form.to_dict()
        insertar_lista_equipos_general(informacion_a_insertar)
        flash("El equipo fue agregado correctamente")
        equipos = consultar_lista_equipos_general()
        return redirect('/gestion_inventario_admins')


# **** VISTA_PRINCIPAL/MODAL "EDITAR EQUIPO" **** #

def editar_equipo_general(informacion_a_actualizar):
        if 'multi_componente' not in informacion_a_actualizar:
            print('este equipo no posee el atributo multi componente')
            query = ('''
                UPDATE Equipo, Equipo_diferenciado
                SET Equipo_diferenciado.codigo_equipo = %s,
                    Equipo.codigo = %s,
                    Equipo.modelo = %s,
                    Equipo.marca = %s,
                    Equipo.imagen = %s,
                    Equipo.descripcion = %s,
                    Equipo.dias_max_prestamo = %s,
                    Equipo.cantidad_circuito = NULL
                WHERE
                    Equipo_diferenciado.codigo_equipo = Equipo.codigo
                    AND Equipo.codigo = %s

            ''')

            cursor.execute(query,(
                informacion_a_actualizar['codigo'],
                informacion_a_actualizar['codigo'],
                informacion_a_actualizar['modelo'],
                informacion_a_actualizar['marca'],
                informacion_a_actualizar['imagen'],
                informacion_a_actualizar['descripcion'],
                informacion_a_actualizar['dias_max_prestamo'],
                informacion_a_actualizar['codigo_original']
                ))
            db.commit()
        else:
            print('este equipo posee el atributo multi componente y su cantidad es:', informacion_a_actualizar['cantidad_componentes'])
            query = ('''
                UPDATE Equipo
                SET codigo = %s,
                    modelo = %s,
                    marca = %s,
                    imagen = %s,
                    descripcion = %s,
                    dias_max_prestamo = %s,
                    cantidad_circuito = %s
                Where Equipo.codigo = %s
            ''')

            cursor.execute(query,(
                informacion_a_actualizar['codigo'],
                informacion_a_actualizar['modelo'],
                informacion_a_actualizar['marca'],
                informacion_a_actualizar['imagen'],
                informacion_a_actualizar['descripcion'],
                informacion_a_actualizar['dias_max_prestamo'],
                informacion_a_actualizar['cantidad_componentes'],
                informacion_a_actualizar['codigo_original']
                ))
            db.commit()


        return informacion_a_actualizar

def editar_equipo_especifico(informacion_a_actualizar,codigo):
            query = ('''
                UPDATE Equipo_diferenciado
                SET Equipo_diferenciado.codigo_sufijo = %s,
                    Equipo_diferenciado.fecha_compra = %s,
                    Equipo_diferenciado.activo = %s,
                WHERE
                    Equipo_diferenciado.codigo_equipo = Equipo.codigo
                    AND Equipo_diferenciado.codigo_sufijo = %s
            ''')

            cursor.execute(query,(
                informacion_a_actualizar['codigo_sufijo'],
                informacion_a_actualizar['fecha_compra'],
                informacion_a_actualizar['activo'],
                ))
            db.commit()
            return informacion_a_actualizar


@mod.route('/gestion_inventario_admin/<string:codigo_equipo>/actualizar_informacion', methods = ['POST'])
def funcion_editar_equipo_diferenciado_form(codigo_equipo):
    if request.method == 'POST':
        informacion_a_actualizar = request.form.to_dict()
        print('Información a actualizar:', informacion_a_actualizar)
        funcion_editar_equipo_diferenciado_form(informacion_a_actualizar,codigo_equipo)
        return redirect("/gestion_inventario_admin/+codigo_equipo")

@mod.route('/gestion_inventario_admin/actualizar_informacion', methods = ['POST'])
def funcion_editar_equipo_form():
    if request.method == 'POST':
        informacion_a_actualizar = request.form.to_dict()
        print('Información a actualizar:', informacion_a_actualizar)
        editar_equipo_general(informacion_a_actualizar)
        return redirect("/gestion_inventario_admin")



@mod.route("/gestion_inventario_admin/detalles_equipo/<string:codigo_equipo>",methods=["GET"])
def detalle_info_equipo(codigo_equipo):
    equipos = consultar_lista_equipos_detalle(codigo_equipo)
    equipo = consultar_equipo_unico(codigo_equipo)
    return render_template("/vistas_gestion_inventario/detalles_equipo.html", equipo_detalle=equipo, equipos_detalle = equipos)

#*********************************************************************************************#


# Importante FUNCION() ENCARGADA DE INGRESAR LOS VALORES DEL FORMULARIO "AGREGAR" EN VISTA GESTION INVENTARIO DIFERENCIAD0 ** #
@mod.route("/gestion_inventario_admin/validar_add/<string:codigo_equipo>", methods = ['POST'])
def validar_form_añadir_equipo_espeficio(codigo_equipo):
    if request.method == 'POST':
        print(codigo_equipo)
        informacion_a_insertar = request.form.to_dict()
        dateTimeObj = datetime.now()
        insertar_lista_equipos_detalle(codigo_equipo, informacion_a_insertar)
        print(informacion_a_insertar)
        flash("El equipo fue agregado correctamente")
        return redirect("/gestion_inventario_admin/"+codigo_equipo) #Cambiar a redirect VISTA GESTION INVENTARIO DIFERENCIAD0
                                                                         # mantener " + codigo_equipo"



# Consulta una  lista de equipos especificos
# Es usada en la vista de equipos asociados
# Ejemplo: Solo ARDUINO UNO
def consultar_lista_equipos_detalle(codigo_equipo):
    query = ('''
        SELECT *
        FROM Equipo_diferenciado
        WHERE Equipo_diferenciado.codigo_equipo = %s
    '''
    )
    cursor.execute(query,(codigo_equipo,))
    equipos_detalle = cursor.fetchall()
    return equipos_detalle


def consultar_lista_equipos_busqueda(codigo):
    query = ('''
        SELECT *
            FROM Equipo
            GROUP BY Equipo.codigo
            WHERE Equipo.codigo = %s
    ''')
    cursor.execute(query,(codigo,))
    equipos = cursor.fetchall()
    return equipos

@mod.route("/gestion_inventario_admin/search", methods = ['POST'])
def busqueda_equipo():
        informacion_a_buscar = request.form.to_dict()
        equipos = consultar_lista_equipos_busqueda(informacion_a_buscar)
        return render_template('vistas_gestion_inventario/gestion_inventario.html', lista_equipo = equipos)
 # Agrega un tipo de equipo con sus datos generales


# Agrega un equipo a partir de la relacion que que tenga DIF
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

# ** Importante VISTA GESTION INVENTARIO DIFERENCIADO ** #
@mod.route("/gestion_inventario_admin/lista_equipo_diferenciado/<string:codigo_equipo>")
def gestion_inventario_admin_equipo(codigo_equipo):
    equipos = consultar_lista_equipos_detalle(codigo_equipo)
    equipo = consultar_equipo_unico(codigo_equipo)
    return render_template('vistas_gestion_inventario/similares_tabla.html',
    equipo_detalle=equipo, equipos_detalle = equipos, equipo_padre = codigo_equipo) #Cambiar render por el que corresponda

# ** VALIDA FORMULARIO DE PRUEBA INGRESAR EQUIPO ** #
# ** BORRAR ANTES DE PRODUCCION ** #
