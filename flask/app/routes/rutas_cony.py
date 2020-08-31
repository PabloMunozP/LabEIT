from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify
from config import db,cursor
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
            INSERT INTO Solicitud (rut_alumno)
                VALUES (%s)
        """
        cursor.execute(sql_query,(session["usuario"]["rut"],))
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
#*********************************************************************************************#

# == VISTA PRINCIPAL GESTION DE CURSOS

# Consulta una lista con todos los cursos
def consultar_lista_cursos():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")
    query = ('''
    SELECT *
        FROM Curso
    ''')
    cursor.execute(query)
    cursos = cursor.fetchall()
    return cursos
def consultar_lista_cursos_secciones():
    query = ("""
        SELECT
            Seccion.id,
            Seccion.rut_profesor,
            Seccion.codigo AS codigo_seccion,
            Seccion.id_curso,
            Curso.codigo_udp,
            Curso.nombre
            FROM Seccion
            LEFT JOIN Curso ON Curso.id = Seccion.id_curso
    """)
    cursor.execute(query)
    secciones = cursor.fetchall()
    return secciones

@mod.route("/gestion_cursos")
def gestion_cursos():
    if 'usuario' not in session or session["usuario"]["id_credencial"] != 3:
        return redirect('/')
    else:
        cursos = consultar_lista_cursos()
        secciones = consultar_lista_cursos_secciones()
        return render_template('gestion_cursos/ver_cursos.html', cursos = cursos, secciones = secciones)

def consultar_curso(codigo):
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")
    query = ('''
        SELECT
            Curso.id as curso_id,
            Curso.codigo_udp,
            Curso.nombre,
            Curso.descripcion
            FROM Curso
            WHERE Curso.codigo_udp = %s
    ''')
    cursor.execute(query,(codigo,))
    curso = cursor.fetchone()
    return curso

def consultar_curso_secciones(codigo):
    query = ('''
        SELECT
            Seccion.id,
            Seccion.rut_profesor,
            Usuario.nombres AS nombres_profesor, Usuario.apellidos AS apellidos_profesor,
            Seccion.codigo AS codigo_seccion,
            Seccion.id_curso,
            Curso.codigo_udp,
            Curso.nombre
            FROM Seccion
            LEFT JOIN Curso ON Curso.id = Seccion.id_curso
            LEFT JOIN Usuario On Usuario.rut = Seccion.rut_profesor
            WHERE Curso.codigo_udp = %s
    ''')
    cursor.execute(query,(codigo,))
    secciones = cursor.fetchall()
    return secciones

def consultar_profesores():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")
    query = ('''
        SELECT *
            FROM Usuario
            WHERE Usuario.id_credencial = 2
    ''')
    cursor.execute(query)
    profesores = cursor.fetchall()
    return profesores

@mod.route("/gestion_cursos/detalles_curso/<string:codigo_udp>",methods=["GET"])
def secciones_curso(codigo_udp):
    curso = consultar_curso(codigo_udp)
    secciones = consultar_curso_secciones(codigo_udp)
    profesores = consultar_profesores()
    return render_template("/gestion_cursos/detalles_curso.html", curso=curso, secciones=secciones,profesores=profesores)
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
        agregar_curso(valores)
        flash("El curso fue agregado correctamente")
        cursos = consultar_lista_cursos()
        return redirect('/gestion_cursos')

def agregar_curso_seccion(val):
    query = ('''
    INSERT INTO Seccion (id_curso, rut_profesor, codigo)
    VALUES (%s, %s, %s);
    ''')
    cursor.execute(query, (
        val['id_curso'],
        val['rut_profesor'],
        val['codigo']))
    db.commit()
    return 'OK'

def redirigir_detalle(val):
    query = ('''
        SELECT codigo_udp FROM Curso WHERE Curso.id = %s
    ''')
    cursor.execute(query, (val,))
    resultado = cursor.fetchone()
    return resultado

@mod.route("/gestion_cursos/agregar_seccion", methods = ['POST'])
def agregar_curso_seccion_form():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")
    if request.method == 'POST':
        valores = request.form.to_dict()
        agregar_curso_seccion(valores)
        curso = redirigir_detalle(valores["id_curso"])
        flash("La seccion fue agregada correctamente")
        return redirect('/gestion_cursos/detalles_curso/'+curso['codigo_udp'])


# == VISTA PRINCIPAL/MODAL "EDITAR CURSO" ==

def editar_curso(val):
    query = ('''
        UPDATE Curso
        SET codigo_udp = %s,
            nombre = %s,
            descripcion = %s
        WHERE Curso.id = %s
    ''')
    cursor.execute(query, (
        val['codigo_udp'],
        val['nombre'],
        val['descripcion'],
        val['id']
        ))
    db.commit()
    return val

@mod.route('/gestion_cursos/editar_curso', methods = ['POST'])
def editar_curso_form():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")
    if request.method=='POST':
        val=request.form.to_dict()
        print(val)
        query = ('''
            UPDATE Curso
            SET Curso.codigo_udp = %s,
                Curso.nombre = %s,
                Curso.descripcion = %s
            WHERE Curso.id = %s
        ''')
        cursor.execute(query, (
            val['nuevo_codigo_udp'],
            val['nombre'],
            val['descripcion'],
            val['id']
            ))
        db.commit()
        flash("El curso se ha actualizado correctamente")
        #se redirige de vuelta a la pagina principal de gestion usuarios
        return redirect("/gestion_cursos")

def editar_curso_form2():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")
    if request.method == 'POST':
        valores = request.form.to_dict()
        editar_curso(valores)
        flash("El curso se ha actualizado correctamente")
        return redirect("/gestion_cursos")

@mod.route('/gestion_cursos/editar_seccion', methods = ['POST'])
def editar_seccion_form():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")
    if request.method=='POST':
        val=request.form.to_dict()
        query = ('''
            UPDATE Seccion
            SET Seccion.rut_profesor = %s,
                Seccion.codigo = %s
            WHERE Seccion.id = %s
        ''')
        cursor.execute(query, (
            val['rut_profesor'],
            val['codigo_seccion'],
            val['id']
            ))
        db.commit()
        curso = redirigir_detalle(val["id_curso"])
        flash("La sección se ha actualizado correctamente")
        return redirect('/gestion_cursos/detalles_curso/'+curso['codigo_udp'])

# == VISTA PRINCIPAL/MODAL "BORRAR CURSO" ==

def eliminar_curso(curso):
    query0 = ('''
        DELETE Seccion_alumno FROM Seccion_alumno, Seccion WHERE Seccion.id_curso = %s AND Seccion.id = Seccion_alumno.id_seccion
    ''')
    query1 = ('''
        DELETE Seccion FROM Seccion WHERE Seccion.id_curso = %s
    ''')
    query2 = ('''
        DELETE Curso FROM Curso WHERE Curso.id = %s
    ''')
    cursor.execute(query0,(curso['id'],))
    cursor.execute(query1,(curso['id'],))
    cursor.execute(query2,(curso['id'],))
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
        eliminar_curso(curso_por_eliminar)
        flash("El curso fue eliminado correctamente")
        return redirect("/gestion_cursos")

def eliminar_seccion(seccion):
    print(seccion['id'])
    query1 = ('''
        DELETE Seccion_alumno FROM Seccion_alumno WHERE Seccion_alumno.id_seccion = %s
    ''')

    query2 = ('''
        DELETE Seccion FROM Seccion WHERE Seccion.id = %s
    ''')
    cursor.execute(query1,(seccion['id'],))
    cursor.execute(query2,(seccion['id'],))
    db.commit()
    return 'OK'

@mod.route("/gestion_cursos/eliminar_seccion",methods=["POST"])
def eliminar_seccion_form():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")
    if request.method == 'POST':
        seccion_por_eliminar = request.form.to_dict()
        eliminar_seccion(seccion_por_eliminar)
        curso = redirigir_detalle(seccion_por_eliminar["id_curso"])
        flash("La sección se ha eliminado correctamente")
        return redirect('/gestion_cursos/detalles_curso/'+curso['codigo_udp'])
# == VISTA DETALLES CURSO ==
def consultar_curso_descripcion(codigo_curso):
    query = ('''
        SELECT *
        FROM Curso
        WHERE Curso.codigo_udp = %s
    ''')
    cursor.execute(query,(codigo_curso,))
    curso_detalle = cursor.fetchone()
    return curso_detalle
@mod.route("/gestion_cursos/detalles_curso/<string:codigo_udp>",methods=["GET"])
def detalle_info_curso(codigo_udp):
    curso_desc = consultar_curso_descripcion(codigo_udp)
    return render_template("/gestion_cursos/detalles_curso.html", curso_desc=curso_desc)

# GESTION ALUMNOS Seccion
def obtener_seccion_id(codigo_udp,codigo_seccion):
    query = ('''
        SELECT Seccion.id FROM Seccion
        LEFT JOIN Curso ON Curso.id = Seccion.id_curso
        WHERE Curso.codigo_udp = %s AND Seccion.codigo = %s
    ''')
    cursor.execute(query,(codigo_udp,codigo_seccion,))
    seccion_id = cursor.fetchone()
    return seccion_id
def consultar_alumnos_seccion(id_seccion):
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")
    query = ('''
        SELECT
            Seccion_alumno.rut_alumno AS rut_alumno,
            Usuario.nombres AS nombres_alumno,
            Usuario.apellidos AS apellidos_alumno
            FROM Seccion_alumno
            LEFT JOIN Usuario ON Usuario.rut = Seccion_alumno.rut_alumno
            WHERE Seccion_alumno.id_seccion = %s
    ''')
    cursor.execute(query,(id_seccion,))
    alumnos = cursor.fetchall()
    return alumnos

@mod.route("/gestion_cursos/detalles_curso/<string:codigo_udp>/<string:codigo_seccion>",methods=["GET"])
def alumnos_seccion(codigo_udp,codigo_seccion):
    seccion_id = obtener_seccion_id(codigo_udp,codigo_seccion)
    alumnos_seccion = consultar_alumnos_seccion(seccion_id['id'])
    todos_los_alumnos = consultar_alumnos(seccion_id['id'])
    curso = consultar_curso_descripcion(codigo_udp)
    return render_template("gestion_cursos/detalles_seccion.html",seccion_id=seccion_id,alumnos=alumnos_seccion,lista_alumnos=todos_los_alumnos,curso=curso)

def consultar_alumnos(id_seccion):
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")
    query = ('''
        SELECT *
            FROM Usuario
            WHERE Usuario.id_credencial = 1
            AND Usuario.rut NOT IN (SELECT Seccion_alumno.rut_alumno FROM Seccion_alumno WHERE Seccion_alumno.id_seccion=%s)
    ''')
    cursor.execute(query,(id_seccion,))
    alumnos = cursor.fetchall()
    return alumnos

def agregar_alumno(val):
    query = ('''
    INSERT INTO Seccion_alumno (id_seccion, rut_alumno)
    VALUES (%s,%s);
    ''')
    cursor.execute(query, (val['id'],val['rut_alumno']))
    db.commit()
    return 'OK'

@mod.route("/gestion_cursos/agregar_alumno", methods = ['POST'])
def agregar_alumno_form():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")
    if request.method == 'POST':
        valores = request.form.to_dict()
        agregar_alumno(valores)
        seccion = obtener_seccion(valores['id'])
        curso = obtener_curso(seccion['id_curso'])
        flash("El alumno se ha agregado correctamente")
        return redirect('/gestion_cursos/detalles_curso/'+curso['codigo_udp']+'/'+str(seccion['codigo']))

def obtener_seccion(id):
    query = ('''
        SELECT * FROM Seccion
        WHERE Seccion.id = %s
    ''')
    cursor.execute(query,(id,))
    seccion = cursor.fetchone()
    return seccion
def obtener_curso(id):
    query = ('''
        SELECT * FROM Curso
        WHERE Curso.id = %s
    ''')
    cursor.execute(query,(id,))
    curso = cursor.fetchone()
    return curso
@mod.route('/gestion_cursos/editar_alumno', methods = ['POST'])
def editar_alumno_form():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")
    if request.method=='POST':
        val=request.form.to_dict()
        query = ('''
            UPDATE Seccion_alumno
            SET Seccion_alumno.rut_alumno = %s
            WHERE Seccion_alumno.id_seccion = %s AND Seccion_alumno.rut_alumno = %s
        ''')
        cursor.execute(query, (
            val['rut_alumno'],
            val['id'],
            val['rut_original']
            ))
        db.commit()
        seccion = obtener_seccion(val['id'])
        curso = obtener_curso(seccion['id_curso'])
        flash("El alumno se ha actualizado correctamente")
        return redirect('/gestion_cursos/detalles_curso/'+curso['codigo_udp']+'/'+str(seccion['codigo']))

def eliminar_alumno(alumno):
    query = ('''
        DELETE Seccion_alumno FROM Seccion_alumno WHERE Seccion_alumno.rut_alumno = %s
    ''')
    cursor.execute(query,(alumno['rut_alumno'],))
    db.commit()
    return 'OK'

@mod.route("/gestion_cursos/eliminar_alumno",methods=["POST"])
def eliminar_alumno_form():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")
    if request.method == 'POST':
        val = request.form.to_dict()
        eliminar_alumno(val)
        seccion = obtener_seccion(val['id'])
        curso = obtener_curso(seccion['id_curso'])
        flash("El alumno se ha eliminado correctamente")
        return redirect('/gestion_cursos/detalles_curso/'+curso['codigo_udp']+'/'+str(seccion['codigo']))
