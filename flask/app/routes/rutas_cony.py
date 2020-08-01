from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify
from config import db,cursor
<<<<<<< HEAD
from datetime import datetime
=======
>>>>>>> jun
import os,time,bcrypt

mod = Blueprint("rutas_cony",__name__)

def redirect_url(default='index'): # Redireccionamiento desde donde vino la request
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

@mod.route("/solicitudes_prestamos",methods=["GET"])
def solicitudes_prestamos():
    if "usuario" not in session.keys():
        return redirect("/")

    # Se revisa si el usuario presenta sanciones.
    # En caso de tener una sanción activa, se notifica y no se permite el acceso.
    sql_query = """
        SELECT *
            FROM Sanciones
                WHERE rut_alumno = %s
                AND activa = 1
    """
    cursor.execute(sql_query,(session["usuario"]["rut"],))
    sancion = cursor.fetchone()

    if sancion is not None:
        return render_template("/solicitudes_prestamos/notificacion_sancion.html",
            sancion=sancion)

    # Se obtiene la lista de equipos desde la base de datos
    sql_query = """
        SELECT * FROM Equipo
    """
    cursor.execute(sql_query)
    lista_equipos = cursor.fetchall()

    for equipo in lista_equipos:
        # Cantidad de equipos disponibles (en préstamo + inventario)
        sql_query = """
            SELECT COUNT(*) AS cantidad_total
                FROM Equipo_diferenciado
                    WHERE codigo_equipo = %s
                    AND activo = 1
        """
        cursor.execute(sql_query,(equipo["codigo"],))
        equipo["cantidad_total"] = cursor.fetchone()["cantidad_total"]

        if equipo["cantidad_total"] is None:
            equipo["cantidad_total"] = 0

        # Cantidad de equipos prestados
        sql_query = """
            SELECT COUNT(*) AS cantidad_equipos_prestados
                FROM Equipo_diferenciado
                    WHERE codigo_equipo = %s
                    AND codigo_sufijo IN (
                        SELECT codigo_sufijo_equipo
                            FROM Detalle_solicitud,Equipo
                                WHERE Detalle_solicitud.id_equipo = Equipo.id
                                AND Equipo.codigo = %s
                    )
        """
        cursor.execute(sql_query,(equipo["codigo"],equipo["codigo"]))
        equipo["cantidad_equipos_prestados"] = cursor.fetchone()["cantidad_equipos_prestados"]
        if equipo["cantidad_equipos_prestados"] is None:
            equipo["cantidad_equipos_prestados"] = 0

        if equipo["cantidad_total"] is not None and equipo["cantidad_equipos_prestados"] is not None:
            equipo["cantidad_disponible"] = equipo["cantidad_total"] - equipo["cantidad_equipos_prestados"]

    # Se crea el carro de pedidos en la sesión del usuario en caso de no existir
    if "carro_pedidos" not in session.keys():
        session["carro_pedidos"] = []

    # Se obtienen los datos de los equipos pedidos para luego mostrar en la lista en el front-end
    lista_carro = []
    for pedido in session["carro_pedidos"]:
        sql_query = """
            SELECT id,nombre,marca,modelo,codigo
                FROM Equipo
                    WHERE id = %s
        """
        cursor.execute(sql_query,(pedido[0],))
        equipo = cursor.fetchone()
        equipo["cantidad_pedidos"] = pedido[1]
        lista_carro.append(equipo)

    return render_template("/solicitudes_prestamos/solicitud_equipos.html",
        lista_equipos=lista_equipos,lista_carro=lista_carro)

@mod.route("/agregar_al_carro",methods=["POST"])
def agregar_al_carro():
    datos_equipo = request.form.to_dict()
    # Al agregar al carro, se almacena el código del equipo y la cantidad en forma de tupla
    # dentro de la lista en la sesión. Ej: [('AAXXDD',3),('ABCDEF',2),...]
    # Se verifica si ya se ha agregado al carro. Si ya se encuentra, se suma la cantidad.
    # En caso contrario, se agrega la tupla al carro
    if "carro_pedidos" in session.keys():
        existe_pedido = False
        for i in range(len(session["carro_pedidos"])):
            if session["carro_pedidos"][i][0] == datos_equipo["id_equipo"]:
                copia_pedido = list(session["carro_pedidos"][i])
                copia_pedido[1] += int(datos_equipo["cantidad_pedidos"])
                session["carro_pedidos"][i] = tuple(copia_pedido)
                existe_pedido = True
                break

        if not existe_pedido:
            session["carro_pedidos"].append((datos_equipo["id_equipo"],int(datos_equipo["cantidad_pedidos"])))

    # Se obtienen los datos de los equipos pedidos para luego mostrar la lista en el front-end
    lista_carro = []
    for pedido in session["carro_pedidos"]:
        sql_query = """
            SELECT id,nombre,marca,modelo,codigo
                FROM Equipo
                    WHERE id = %s
        """
        cursor.execute(sql_query,(pedido[0],))
        equipo = cursor.fetchone()
        equipo["cantidad_pedidos"] = pedido[1]
        lista_carro.append(equipo)

    return render_template("/solicitudes_prestamos/seccion_carro_pedidos.html",
        lista_carro=lista_carro)

@mod.route("/eliminar_del_carro",methods=["POST"])
def eliminar_del_carro():
    # Si vaciar_carro es 1, se vacía el carro. En caso contrario, se elimina el pedido seleccionado.
    datos_formulario = request.form.to_dict()
    vaciar_carro = bool(int(datos_formulario["vaciar_carro"]))

    if not vaciar_carro:
        # Se busca en la lista según el código del equipo y se borra junto a la cantidad.
        id_equipo = datos_formulario["id_equipo"]

        if "carro_pedidos" in session.keys():
            indice_pedido = None
            for i in range(len(session["carro_pedidos"])):
                if session["carro_pedidos"][i][0] == id_equipo:
                    indice_pedido = i
                    break

            if indice_pedido is not None:
                session["carro_pedidos"].pop(indice_pedido)
    else:
        session["carro_pedidos"] = []

    # Se obtienen los datos de los equipos pedidos para luego mostrar en la lista en el front-end
    lista_carro = []
    for pedido in session["carro_pedidos"]:
        sql_query = """
            SELECT id,nombre,marca,modelo,codigo
                FROM Equipo
                    WHERE id = %s
        """
        cursor.execute(sql_query,(pedido[0],))
        equipo = cursor.fetchone()
        equipo["cantidad_pedidos"] = pedido[1]
        lista_carro.append(equipo)

    return render_template("/solicitudes_prestamos/seccion_carro_pedidos.html",
        lista_carro=lista_carro)

@mod.route("/registrar_solicitud",methods=["POST"])
def registrar_solicitud():
    # Se registra la solicitud con cada detalle según los pedidos del carro de pedidos

    if "carro_pedidos" in session.keys():
        # Se registra la solicitud
        sql_query = """
<<<<<<< HEAD
            INSERT INTO Solicitud (rut_alumno,fecha_registro)
                VALUES (%s,%s)
        """
        cursor.execute(sql_query,(session["usuario"]["rut"],datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
=======
            INSERT INTO Solicitud (rut_alumno)
                VALUES (%s)
        """
        cursor.execute(sql_query,(session["usuario"]["rut"],))
>>>>>>> jun
        id_solicitud = cursor.lastrowid # Se obtiene el id de solicitud recién creada

        # Se registran los detalles de solicitud por cada pedido (unitario)
        # con el enlace a la solicitud generada previamente
        for pedido in session["carro_pedidos"]:
            # Formato de pedido: (<id>,<cantidad>)
            sql_query = """
                INSERT INTO Detalle_solicitud (id_solicitud,id_equipo,estado)
                    VALUES (%s,%s,0)
            """
            for i in range(pedido[1]):
                cursor.execute(sql_query,(id_solicitud,pedido[0]))

    # Se vacía el carro de pedidos una vez registrada la solicitud completa
    session["carro_pedidos"] = []

    flash("solicitud-registrada")
    return redirect("/solicitudes_prestamos")
<<<<<<< HEAD
=======
#*********************************************************************************************#

# == VISTA PRINCIPAL GESTION DE CURSOS

# Consulta una lista con todos los cursos
def consultar_lista_cursos():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")
    query = ('''
    SELECT
        Curso.codigo_udp,
        Curso.nombre,
        Curso.descripcion
        FROM Curso
    ''')
    cursor.execute(query)
    cursos = cursor.fetchall()
    return cursos

@mod.route("/gestion_cursos")
def gestion_cursos():
    if 'usuario' not in session or session["usuario"]["id_credencial"] != 3:
        return redirect('/')
    else:
        cursos = consultar_lista_cursos()
        return render_template('gestion_cursos/ver_cursos.html', cursos = cursos)

# == VISTA PRINCIPAL/MODAL "AGREGAR CURSO" ==

def agregar_curso(val):
    query = ('''
    INSERT INTO Curso (codigo_udp, nombre, descripcion)
    VALUES (%s, %s, %s);
    ''')
    cursor.execute(query, (
        val['codigo_udp'],
        val['nombre'],
        val['descripcion']))
    db.commit()
    return 'OK'

@mod.route("/gestion_cursos/agregar_curso", methods = ['POST'])
def agregar_curso_form():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")
    if request.method == 'POST':
        valores = request.form.to_dict()
        agregar_curso(valores_ins)
        flash("El curso fue agregado correctamente")
        cursos = consultar_lista_cursos()
        return redirect('/gestion_cursos')

# == VISTA PRINCIPAL/MODAL "EDITAR CURSO" ==

def editar_curso(val):
    query = ('''
        UPDATE Curso
        SET codigo_udp = %s,
            nombre = %s,
            descripcion = %s
        WHERE Curso.codigo_udp = %s
    ''')
    cursor.execute(query, (
        val['codigo_udp'],
        val['nombre'],
        val['descripcion']
        ))
    db.commit()
    return val

@mod.route('/gestion_cursos/editar_curso', methods = ['POST'])
def editar_curso_form():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")
    if request.method == 'POST':
        valores = request.form.to_dict()
        editar_curso(valores)
        flash("El curso se ha actualizado correctamente")
        return redirect("/gestion_cursos")

# == VISTA PRINCIPAL/MODAL "BORRAR CURSO" ==

def eliminar_curso(curso):
    query = ('''
        DELETE Curso FROM Curso WHERE Curso.codigo_udp = %s
    ''')
    print(curso)
    cursor.execute(query,(curso['codigo_udp'],))
    db.commit()
    return 'OK'

@mod.route("/gestion_cursos/eliminar_curso",methods=["POST"])
def eliminar_curso_form():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")
    if request.method == 'POST':
        curso_por_eliminar = request.form.to_dict()
        print(curso_por_eliminar)
        eliminar_curso(curso_por_eliminar)
        flash("El curso fue eliminado correctamente")
        return redirect("/gestion_cursos")
# == VISTA DETALLES CURSO ==
def consultar_curso_descripcion(codigo_curso):
    query = ('''
        SELECT *
        FROM CURSO
        WHERE Curso.codigo_udp = %s
    ''')
    cursor.execute(query,(codigo_curso,))
    curso_detalle = cursos.fetchone()
    return curso_detalle
@mod.route("/gestion_cursos/detalles_curso/<string:codigo_udp>",methods=["GET"])
def detalle_info_curso(codigo_udp):
    curso_desc = consultar_curso_descripcion(codigo_udp)
    return render_template("/gestion_cursos/detalles_curso.html", curso_desc=curso_desc)
>>>>>>> jun
