from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify, make_response
from flask_csv import send_csv
from config import db,cursor
import os,time,bcrypt
from datetime import datetime
import json
from jinja2 import Environment

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
        SELECT *,
            COUNT(CASE WHEN Detalle_solicitud.estado IN (1, 2, 3) THEN 1
            ELSE NULL END) AS en_prestamo
        FROM (SELECT
                Equipo.id AS equipo_id,
                Equipo.codigo,
                Equipo.nombre,
                Equipo.modelo,
                Equipo.marca,
                Equipo.descripcion,
                Equipo.dias_max_prestamo,
                Equipo.imagen,
                COUNT(CASE WHEN Equipo_diferenciado.activo = 1 THEN 1 ELSE NULL END) AS disponibles,
                COUNT(Equipo_diferenciado.activo) AS total_equipos
                FROM Equipo
                    LEFT JOIN Equipo_diferenciado ON  Equipo.codigo = Equipo_diferenciado.codigo_equipo
                GROUP BY Equipo.id) AS inventario_general
            LEFT JOIN Detalle_solicitud ON inventario_general.equipo_id = Detalle_solicitud.id_equipo
        GROUP BY inventario_general.equipo_id
            ''')
    cursor.execute(query)
    equipos = cursor.fetchall()
    # for element in equipos:
    #     print(element)
    return equipos
def consultar_lista_equipos(): # funcion para poder conusultar toda la lista de equiipos detallados
    query = ("""
        SELECT Equipo_diferenciado.id,
            Equipo_diferenciado.codigo_equipo,
            Equipo_diferenciado.codigo_sufijo,
            Equipo_diferenciado.codigo_activo,
            Equipo_diferenciado.fecha_compra,
            Equipo.nombre,
            Equipo.modelo,
            Equipo.marca,
            Equipo_diferenciado.activo,
            Equipo_diferenciado.razon_inactivo,
            CASE WHEN Equipo_diferenciado.activo = 0 THEN 'No disponible'
                WHEN Detalle_solicitud.estado = 1 THEN 'Por retirar'
                WHEN Detalle_solicitud.estado = 2 THEN 'En posesión'
                WHEN Detalle_solicitud.estado = 3 THEN 'Con atraso'
                ELSE 'Disponible' END AS estado,
            Detalle_solicitud.codigo_sufijo_equipo
        FROM Equipo_diferenciado
        LEFT JOIN Equipo ON Equipo.codigo = Equipo_diferenciado.codigo_equipo
        LEFT JOIN (SELECT * FROM Detalle_solicitud WHERE Detalle_solicitud.estado IN (1,2,3)) AS Detalle_solicitud
            ON Detalle_solicitud.id_equipo = Equipo.id
            AND Detalle_solicitud.codigo_sufijo_equipo = Equipo_diferenciado.codigo_sufijo
    """)
    cursor.execute(query)
    resultado = cursor.fetchall()
    return resultado
@mod.route("/debug_query")
def debug_query():
    debug_equipos = consultar_lista_equipos()
    for i in debug_equipos:
        print(i)
    return 'xD'


@mod.route("/gestion_inventario_admin")
def gestion_inventario_admin():
    if 'usuario' not in session or session["usuario"]["id_credencial"] != 3:
        return redirect('/')
    else:
        equipos = consultar_lista_equipos_general()
        equipos_detalle = consultar_lista_equipos()
        circuitos = consultar_lista_circuito()
        cursor = db.cursor(dictionary=True)
        query = ("""
            SELECT *
                    FROM Equipo
                """)
        cursor.execute(query)
        resultado = cursor.fetchall()
        ## print(f"json: {json.dumps(resultado)}")
        return render_template('vistas_gestion_inventario/gestion_inventario.html',
            lista_equipo = equipos,
            lista_equipo_detalle = equipos_detalle,
            lista_circuitos = circuitos,
            resultados= {json.dumps(resultado)} )


# **** VISTA_PRINCIPAL/MODAL "AGREGAR EQUIPO" **** #

def insertar_lista_equipos_general(valores_a_insertar):
    query = ('''
        INSERT INTO Equipo (codigo, nombre, modelo, marca, descripcion, imagen, dias_max_prestamo)
        VALUES (%s, %s, %s, %s, %s, %s,%s);
    ''')
    cursor.execute(query,(
        valores_a_insertar['codigo'],
        valores_a_insertar['nombre'],
        valores_a_insertar['modelo'],
        valores_a_insertar['marca'],
        valores_a_insertar['descripcion'],
        valores_a_insertar['imagen'],
        valores_a_insertar['dias_maximo_prestamo']))
    db.commit()
    return valores_a_insertar['codigo']

@mod.route("/gestion_inventario_admin/insert", methods = ['POST'])
def funcion_añadir_equipo_form():
    if request.method == 'POST':
        informacion_a_insertar = request.form.to_dict()
        equipos = consultar_lista_equipos_general()
        for val in equipos:
            if (val["codigo"]==informacion_a_insertar["codigo"]):
                print("el codigo",informacion_a_insertar["codigo"] ,"ya existe")
                return redirect('/gestion_inventario_admin')
        print("el codigo",informacion_a_insertar["codigo"] ,"no existe")
        insertar_lista_equipos_general(informacion_a_insertar)
        flash("El equipo fue agregado correctamente")
        equipos = consultar_lista_equipos_general()
        return redirect('/gestion_inventario_admin')


# **** VISTA_PRINCIPAL/MODAL "EDITAR EQUIPO" **** #

def editar_equipo_general(informacion_a_actualizar):  # Query UPDATE
            query = ('''
                UPDATE Equipo
                LEFT JOIN Equipo_diferenciado ON Equipo_diferenciado.codigo_equipo = Equipo.codigo
                SET Equipo_diferenciado.codigo_equipo = %s,
                    Equipo.codigo = %s,
                    Equipo.nombre = %s,
                    Equipo.modelo = %s,
                    Equipo.marca = %s,
                    Equipo.imagen = %s,
                    Equipo.descripcion = %s,
                    Equipo.dias_max_prestamo = %s,
                WHERE
                    Equipo.codigo = %s

            ''')
            cursor.execute(query,(
                informacion_a_actualizar['codigo'],
                informacion_a_actualizar['codigo'],
                informacion_a_actualizar['nombre'],
                informacion_a_actualizar['modelo'],
                informacion_a_actualizar['marca'],
                informacion_a_actualizar['imagen'],
                informacion_a_actualizar['descripcion'],
                informacion_a_actualizar['dias_max_prestamo'],
                informacion_a_actualizar['codigo_original']
                ))
            db.commit()
            return informacion_a_actualizar

def editar_equipo_especifico(informacion_a_actualizar):
            query = ('''
                UPDATE Equipo_diferenciado
                SET Equipo_diferenciado.codigo_sufijo = %s,
                    Equipo_diferenciado.fecha_compra = %s,
                    Equipo_diferenciado.codigo_activo = %s,
                    Equipo_diferenciado.activo = %s,
                    Equipo_diferenciado.razon_inactivo = %s
                WHERE Equipo_diferenciado.codigo_sufijo = %s
                AND Equipo_diferenciado.codigo_equipo = %s
            ''')

            cursor.execute(query,(
                informacion_a_actualizar['codigo_sufijo'],
                informacion_a_actualizar['fecha_compra'],
                informacion_a_actualizar['codigo_activo'],
                informacion_a_actualizar['activo'],
                informacion_a_actualizar['razon_inactivo'],
                informacion_a_actualizar['codigo_sufijo_original'],
                informacion_a_actualizar['codigo_equipo']
                ))
            db.commit()
            return informacion_a_actualizar


#Actualizar informacion equipo diferenciado

@mod.route('/gestion_inventario_admin/lista_equipo_diferenciado/actualizar_informacion', methods = ['POST'])
def funcion_editar_equipo_diferenciado_form():
    if request.method == 'POST':
        informacion_a_actualizar = request.form.to_dict()
        print('Información a actualizar:', informacion_a_actualizar)
        equipos = consultar_lista_equipos_detalle(informacion_a_actualizar["codigo_equipo"])
        print(informacion_a_actualizar["codigo_sufijo"])
        for val in equipos:
            if (val["codigo_sufijo"]==informacion_a_actualizar["codigo_sufijo"]):
                    print("codigo ya existe")
                    return redirect("/gestion_inventario_admin/lista_equipo_diferenciado/"+informacion_a_actualizar["codigo_equipo"])
        print("codigo no existe")
        editar_equipo_especifico(informacion_a_actualizar)
        return redirect("/gestion_inventario_admin/lista_equipo_diferenciado/"+informacion_a_actualizar["codigo_equipo"])

#Actualizar información del equipo

@mod.route('/gestion_inventario_admin/actualizar_informacion', methods = ['POST'])
def funcion_editar_equipo():
    if request.method == 'POST':
        informacion_a_actualizar = request.form.to_dict()
        equipos = consultar_lista_equipos_general()
        for val in equipos:
            if (val["codigo"]==informacion_a_actualizar["codigo"]):
                    print("codigo ya existe")
                    return redirect('/gestion_inventario_admin')
        print("codigo no existe")
        # print('Información a actualizar:', informacion_a_actualizar)
        editar_equipo_general(informacion_a_actualizar)
        return redirect("/gestion_inventario_admin")

# **** VISTA_PRINCIPAL/MODAL "BORRAR EQUIPO" **** #

def eliminar_equipo_general(equipo):
    query = ('''
        DELETE Equipo, Equipo_diferenciado
        FROM Equipo
        LEFT JOIN Equipo_diferenciado ON Equipo_diferenciado.codigo_equipo = Equipo.codigo
        WHERE Equipo.codigo = %s
    ''')
    cursor.execute(query,(equipo['codigo'],))
    db.commit()
    return 'ok'

#Ruta eliminar equipo

@mod.route("/gestion_inventario_admin/delete",methods=["POST"])
def funcion_eliminar_equipo():
    if request.method == 'POST':
        equipo_a_eliminar = request.form.to_dict()
        eliminar_equipo_general(equipo_a_eliminar)
        #dejar comentario en flash
        return redirect("/gestion_inventario_admin")




#*********************************************************************************************#

# **** VISTA_PRINCIPAL/MODAL "BORRAR EQUIPO DIFERENCIADO" **** #

def eliminar_equipo_vista_diferenciado(equipo):
    query = ('''
        DELETE Equipo_diferenciado
        FROM Equipo_diferenciado
        WHERE Equipo_diferenciado.codigo_equipo = %s
        AND Equipo_diferenciado.codigo_sufijo = %s
    ''')
    cursor.execute(query,(
    equipo['codigo_equipo'],
    equipo['codigo_sufijo']
    ))
    db.commit()
    return 'ok'

#Ruta eliminar equipo

@mod.route("/gestion_inventario_admin/lista_equipo_diferenciado/delete",methods=["POST"])
def funcion_eliminar_equipo_diferenciado():
    if request.method == 'POST':
        equipo_a_eliminar = request.form.to_dict()
        # print(equipo_a_eliminar)
        eliminar_equipo_vista_diferenciado(equipo_a_eliminar)
        #dejar comentario en flash
        return redirect("/gestion_inventario_admin/lista_equipo_diferenciado/"+equipo_a_eliminar["codigo_equipo"])




#*********************************************************************************************#
#Informacion de equipo unico para listado de equipo_diferenciado
def consultar_equipo_descripcion(codigo):
    query = ('''
        SELECT *
        FROM Equipo
        WHERE Equipo.codigo = %s
    '''
    )
    cursor.execute(query,(codigo,))
    equipo_detalle = cursor.fetchone()
    return equipo_detalle

# Consulta una  lista de equipos especificos
def consultar_lista_equipos_detalle_estado(codigo_equipo):
    query = ('''
        SELECT
            Equipo_diferenciado.codigo_equipo,
            Equipo_diferenciado.codigo_sufijo,
            Equipo_diferenciado.activo,
            Equipo.id AS equipo_id,
            Detalle_solicitud.id AS detalle_sol_id,
            Detalle_solicitud.codigo_sufijo_equipo,
            Detalle_solicitud.estado,
            Estado_detalle_solicitud.nombre,
            Solicitud.rut_alumno,
            Detalle_solicitud.fecha_inicio,
            Detalle_solicitud.fecha_termino,
            Detalle_solicitud.fecha_vencimiento
        FROM Equipo_diferenciado
        LEFT JOIN Equipo ON Equipo.codigo = Equipo_diferenciado.codigo_equipo
        LEFT JOIN Detalle_solicitud ON Detalle_solicitud.id_equipo = Equipo.id
            AND Detalle_solicitud.codigo_sufijo_equipo = Equipo_diferenciado.codigo_sufijo
        LEFT JOIN Solicitud ON Solicitud.id=Detalle_solicitud.id_solicitud
        LEFT JOIN Estado_detalle_solicitud ON Estado_detalle_solicitud.id=Detalle_solicitud.estado
        WHERE Equipo_diferenciado.codigo_equipo = %s
            AND Detalle_solicitud.estado IN (1,2,3)
    '''
    )
    cursor.execute(query,(codigo_equipo,))
    equipos_detalle = cursor.fetchall()
    return equipos_detalle

# funcion para probar la consulta
@mod.route("/prueba/detalles_equipo/<string:codigo_equipo>",methods=["GET"])
def lista_detalle_info_equipo_estado(codigo_equipo):
    equipos = consultar_lista_equipos_detalle_estado(codigo_equipo)
    for i in equipos:
        print(i)
    return 'XD'


#Vista más informacion equipo , sin tabla solicitudes definida
@mod.route("/gestion_inventario_admin/detalles_equipo/<string:codigo_equipo>",methods=["GET"])
def detalle_info_equipo(codigo_equipo):
    equipos = consultar_lista_equipos_detalle_estado(codigo_equipo)
    equipo_descripcion = consultar_equipo_descripcion(codigo_equipo)
    return render_template("/vistas_gestion_inventario/detalles_equipo.html",
    equipo_descripcion=equipo_descripcion, equipos_detalle = equipos)


# Importante FUNCION() ENCARGADA DE INGRESAR LOS VALORES DEL FORMULARIO "AGREGAR" EN VISTA GESTION INVENTARIO DIFERENCIAD0 ** #
@mod.route("/gestion_inventario_admin/lista_equipo_diferenciado/validar_add/<string:codigo_equipo>", methods = ['POST'])
def validar_form_añadir_equipo_espeficio(codigo_equipo):
    if request.method == 'POST':
        informacion_a_insertar = request.form.to_dict()
        insertar_lista_equipos_detalle(codigo_equipo, informacion_a_insertar)
        equipos = consultar_lista_equipos_detalle(codigo_equipo)
        print(informacion_a_insertar["codigo_sufijo"])
        for val in equipos:
            if (val["codigo_sufijo"]==informacion_a_insertar["codigo_sufijo"]):
                    print("codigo ya existe")
                    return redirect("/gestion_inventario_admin/lista_equipo_diferenciado/"+codigo_equipo)
        print("codigo no existe")
        return redirect("/gestion_inventario_admin/lista_equipo_diferenciado/"+codigo_equipo)


# Agrega un equipo a partir de la relacion que tenga DIF
def insertar_lista_equipos_detalle(codigo_equipo, valores_a_insertar):
    query = ('''
        INSERT INTO Equipo_diferenciado (codigo_equipo, codigo_sufijo, codigo_activo, fecha_compra, activo)
        VALUES (%s, %s, %s, %s, %s);
    ''')
    cursor.execute(query,(
        codigo_equipo,
        valores_a_insertar['codigo_sufijo'],
        valores_a_insertar['codigo_activo'],
        valores_a_insertar['fecha_compra'],
        valores_a_insertar['activo']))
    db.commit()
    return 'OK'


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

# ** Importante VISTA GESTION INVENTARIO DIFERENCIADO ** #
@mod.route("/gestion_inventario_admin/lista_equipo_diferenciado/<string:codigo_equipo>")
def gestion_inventario_admin_equipo(codigo_equipo):
    equipos = consultar_lista_equipos_detalle(codigo_equipo)
    equipos_descripcion = consultar_equipo_descripcion(codigo_equipo)
    return render_template('vistas_gestion_inventario/similares_tabla.html',
    equipos_descripcion=equipos_descripcion, equipos_detalle = equipos, equipo_padre = codigo_equipo) #Cambiar render por el que corresponda



#*********************************************************************************************#

# ***** Importante VISTA CIRCUITOS **** #

#Consulta tabla principal
def consultar_lista_circuito():
    query = ('''
        SELECT *
        FROM Circuito
    '''
    )
    cursor.execute(query)
    circuitos = cursor.fetchall()
    return circuitos


#Consulta para insertar circuito
def insertar_lista_circuitos(valores_a_insertar):
    query = ('''
        INSERT INTO Circuito (nombre, cantidad, descripcion)
        VALUES (%s, %s, %s);
    ''')
    cursor.execute(query,(
        valores_a_insertar['nombre_circuito'],
        valores_a_insertar['cantidad_circuito'],
        valores_a_insertar['descripcion_circuito']))
    db.commit()
    return 'OK'

#funcion insertar nuevo circuito
@mod.route("/gestion_inventario_admin/insert_circuito", methods = ['POST'])
def funcion_añadir_circuito_form():
    if request.method == 'POST':
        informacion_a_insertar = request.form.to_dict()
        insertar_lista_circuitos(informacion_a_insertar)
        flash("El equipo fue agregado correctamente")
        return redirect('/gestion_inventario_admin')

#Consulta editar circuito
def editar_circuito(informacion_a_actualizar):  # Query UPDATE
            query = ('''
                UPDATE Circuito
                SET Circuito.nombre = %s,
                    Circuito.cantidad = %s,
                    Circuito.descripcion = %s
                WHERE Circuito.nombre= %s
                AND Circuito.descripcion = %s

            ''')
            cursor.execute(query,(
                informacion_a_actualizar['nombre_circuito'],
                informacion_a_actualizar['cantidad_circuito'],
                informacion_a_actualizar['descripcion_circuito'],
                informacion_a_actualizar['nombre_circuito_original'],
                informacion_a_actualizar['descripcion_circuito_original']
                ))
            db.commit()
            return informacion_a_actualizar

#Funcion editar circuito
@mod.route('/gestion_inventario_admin/actualizar_informacion_circuito', methods = ['POST'])
def funcion_editar_circuito():
    if request.method == 'POST':
        informacion_a_actualizar = request.form.to_dict()
        editar_circuito(informacion_a_actualizar)
        print(informacion_a_actualizar)
        return redirect("/gestion_inventario_admin")


#Consulta eliminar circuito
def eliminar_circuito(circuito):
    query = ('''
        DELETE Circuito
        FROM Circuito
        WHERE Circuito.nombre = %s
        AND Circuito.descripcion = %s
    ''')
    cursor.execute(query,(
    circuito['nombre_circuito'],
    circuito['descripcion_circuito']
    ))
    db.commit()
    return 'ok'


#Funcion eliminar circuito

@mod.route("/gestion_inventario_admin/delete_circuito",methods=["POST"])
def funcion_eliminar_circuito():
    if request.method == 'POST':
        equipo_a_eliminar = request.form.to_dict()
        eliminar_circuito(equipo_a_eliminar)
        return redirect("/gestion_inventario_admin")




#Modificar Wifi

def consultar_datos_wifi():
    query = ('''
        SELECT *
        FROM Wifi
    '''
    )
    cursor.execute(query)
    wifi = cursor.fetchone()
    return wifi

@mod.route("/modificar_wifi")
def modificar_wifi():
    if 'usuario' not in session or session["usuario"]["id_credencial"] != 3:
        return redirect('/')
    else:
        datos = consultar_datos_wifi()
        return render_template('vistas_gestion_inventario/modificar_wifi.html',
            datos_wifi = datos )

def editar_datos_wifi(informacion_a_actualizar):  # Query UPDATE
            query = ('''
                UPDATE Wifi
                SET Wifi.ssid = %s,
                    Wifi.bssid = %s,
                    Wifi.password = %s
                WHERE Wifi.ssid = %s
                AND Wifi.bssid = %s

            ''')
            cursor.execute(query,(
                informacion_a_actualizar['ssid'],
                informacion_a_actualizar['bssid'],
                informacion_a_actualizar['contraseña'],
                informacion_a_actualizar['ssid_original'],
                informacion_a_actualizar['bssid_original']
                ))
            db.commit()
            return informacion_a_actualizar

@mod.route('/modificar_wifi/actualizar', methods = ['POST'])
def funcion_editar_wifi():
    if request.method == 'POST':
        informacion_a_actualizar = request.form.to_dict()
        editar_datos_wifi(informacion_a_actualizar)
        print(informacion_a_actualizar)
        return redirect("/modificar_wifi")

@mod.route('/download_test')
def test():
        codigo = []
        marca = []
        modelo = []
        equipos = consultar_lista_equipos_general()
        for i in equipos:
            codigo.append(i["codigo"])
            marca.append(i["marca"])
            modelo.append(i["modelo"])
        return send_csv([{"codigo": codigo, "marca":marca, "modelo":modelo}],
            "testing.csv", ["codigo","marca","modelo"])


@mod.route('/csv')
def download_csv():
    csv = ' Codigo, Nombre, Modelo, Marca, Dias de prestamo, Prestados, Funcional, Total\n'

    equipos = consultar_lista_equipos_general()
    for i in equipos:
          csv += i["codigo"] + "," + i["nombre"] + "," + i["modelo"] + "," + i["marca"] + "," + str(i["dias_max_prestamo"]) + "," + str(i["en_prestamo"]) + "," + str(i["disponibles"]) + "," + str(i["total_equipos"]) + "\n"
##        csv.append(i["codigo"],i["nombre"],i["modelo"],i["marca"],i["dias_max_prestamo"],i["en_prestamo"],i["disponibles"],i["total_equipos"])
    response = make_response(csv)
    cd = 'attachment; filename=mycsv.csv'
    response.headers['Content-Disposition'] = cd
    response.mimetype='text/csv'

    return response
