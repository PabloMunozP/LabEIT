import os,time
from config import db
from datetime import datetime,timedelta
from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify

mod = Blueprint("rutas_solicitud_prestamos_equipos",__name__)

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
    """
    #cursor.execute(sql_query,(session["usuario"]["rut"],))
    cursor = db.query(sql_query,(session["usuario"]["rut"],))
    sancion = cursor.fetchone()

    # Se obtiene la lista de detalles que se encuentran con sanción activa
    sql_query = """
        SELECT Detalle_solicitud.*,Equipo.codigo AS codigo_equipo,Equipo.nombre AS nombre_equipo,Equipo.marca AS marca_equipo,
            Equipo.modelo AS modelo_equipo
            FROM Detalle_solicitud,Solicitud,Equipo
                WHERE Detalle_solicitud.id_solicitud = Solicitud.id
                AND Detalle_solicitud.id_equipo = Equipo.id
                AND Solicitud.rut_alumno = %s
                AND Detalle_solicitud.sancion_activa = 1
    """
    #cursor.execute(sql_query,(session["usuario"]["rut"],))
    cursor = db.query(sql_query,(session["usuario"]["rut"],))

    lista_detalles_sancionados = cursor.fetchall()

    if sancion is not None:
        # Se eliminan los elementos del carro en caso de existir con anterioridad
        if "carro_pedidos" in session.keys():
            del session["carro_pedidos"]

        return render_template("/solicitudes_prestamos/notificacion_sancion.html",
            sancion=sancion,
            lista_detalles_sancionados=lista_detalles_sancionados)

    # Se obtiene la lista de equipos desde la base de datos
    sql_query = """
        SELECT * FROM Equipo
    """
    #cursor.execute(sql_query)
    cursor = db.query(sql_query,None)

    lista_equipos = cursor.fetchall()

    for equipo in lista_equipos:
        # Cantidad de equipos disponibles (en préstamo + inventario)
        sql_query = """
            SELECT COUNT(*) AS cantidad_total
                FROM Equipo_diferenciado
                    WHERE codigo_equipo = %s
                    AND activo = 1
        """
        #cursor.execute(sql_query,(equipo["codigo"],))
        cursor = db.query(sql_query,(equipo["codigo"],))

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
        #cursor.execute(sql_query,(equipo["codigo"],equipo["codigo"]))
        cursor = db.query(sql_query,(equipo["codigo"],equipo["codigo"]))
        
        equipo["cantidad_equipos_prestados"] = cursor.fetchone()["cantidad_equipos_prestados"]
        if equipo["cantidad_equipos_prestados"] is None:
            equipo["cantidad_equipos_prestados"] = 0

        if equipo["cantidad_total"] is not None and equipo["cantidad_equipos_prestados"] is not None:
            equipo["cantidad_disponible"] = equipo["cantidad_total"] - equipo["cantidad_equipos_prestados"]

    # Se crea el carro de pedidos en la sesión del usuario en caso de no existir
    if "carro_pedidos" not in session.keys():
        session["carro_pedidos"] = []

    # Se obtienen los datos de los equipos pedidos para luego mostrar la lista en el front-end
    lista_carro = []
    for index,pedido in enumerate(session["carro_pedidos"]):
        # Se obtiene (para pedido con asignatura asociada o sin asignatura)
        # los datos del equipo solicitado
        sql_query = """
            SELECT id,nombre,marca,modelo
                FROM Equipo
                    WHERE id = %s
        """
        #cursor.execute(sql_query,(pedido[0],))
        cursor = db.query(sql_query,(pedido[0],))

        equipo = cursor.fetchone()

        if equipo is not None:
            # Se agrega el index
            equipo["index_pedido"] = index
            # Se agrega la cantidad pedida
            equipo["cantidad_pedidos"] = pedido[1]
            # Si el pedido tiene asociado una asignatura, se agrega
            if pedido[2] is not None:
                sql_query = """
                    SELECT nombre AS nombre_curso
                        FROM Curso
                            WHERE id = %s
                """
                #cursor.execute(sql_query,(pedido[2],))
                cursor = db.query(sql_query,(pedido[2],))

                curso = cursor.fetchone()

                if curso is not None:
                    # Se agrega la información del curso al equipo
                    equipo.update(curso)
            lista_carro.append(equipo) # Se agrega el pedido final al carro para la vista
    
    # Se obtienen los cursos registrados
    query="""
        SELECT Curso.id,Curso.codigo_udp,Curso.nombre
            FROM Curso
                ORDER BY Curso.nombre
    """
    #cursor.execute(query)
    cursor = db.query(query,None)

    lista_cursos = cursor.fetchall()

    return render_template("/solicitudes_prestamos/solicitud_equipos.html",
        lista_equipos=lista_equipos,lista_carro=lista_carro,lista_cursos=lista_cursos)

@mod.route("/agregar_al_carro",methods=["POST"])
def agregar_al_carro():
    datos_equipo = request.form.to_dict()

    # Se agrega el nuevo equipo según las características
    # Cada uno de los registros de la lista de carro x su cantidad corresponden a los
    # detalles de la solicitud

    # Estructura de cada pedido (tuple)
    # (id_equipo,cantidad,id_asignatura_asociada)
    # cantidad: Cantidad de equipos con id_equipo solicitados
    # id_asignatura_asociada: ID de la asignatura si se asoció, de lo contrario None 

    if "carro_pedidos" in session.keys():
        if not datos_equipo["id_asignatura_asociada"]:
            # Se setea a None si no se asoció una asignatura
            datos_equipo["id_asignatura_asociada"] = None

        session["carro_pedidos"].append((datos_equipo["id_equipo"],datos_equipo["cantidad_pedidos"],datos_equipo["id_asignatura_asociada"]))
    
    # Se obtienen los datos de los equipos pedidos para luego mostrar la lista en el front-end
    lista_carro = []
    for index,pedido in enumerate(session["carro_pedidos"]):
        # Se obtiene (para pedido con asignatura asociada o sin asignatura)
        # los datos del equipo solicitado
        sql_query = """
            SELECT id,nombre,marca,modelo
                FROM Equipo
                    WHERE id = %s
        """
        #cursor.execute(sql_query,(pedido[0],))
        cursor = db.query(sql_query,(pedido[0],))

        equipo = cursor.fetchone()

        if equipo is not None:
            # Se agrega el index
            equipo["index_pedido"] = index
            # Se agrega la cantidad pedida
            equipo["cantidad_pedidos"] = pedido[1]
            # Si el pedido tiene asociado una asignatura, se agrega
            if pedido[2] is not None:
                sql_query = """
                    SELECT nombre AS nombre_curso
                        FROM Curso
                            WHERE id = %s
                """
                #cursor.execute(sql_query,(pedido[2],))
                cursor = db.query(sql_query,(pedido[2],))

                curso = cursor.fetchone()

                if curso is not None:
                    # Se agrega la información del curso al equipo
                    equipo.update(curso)
            lista_carro.append(equipo) # Se agrega el pedido final al carro para la vista

    return render_template("/solicitudes_prestamos/seccion_carro_pedidos.html",
        lista_carro=lista_carro)

@mod.route("/eliminar_del_carro",methods=["POST"])
def eliminar_del_carro():
    # Si vaciar_carro es 1, se vacía el carro. En caso contrario, se elimina el pedido seleccionado.
    datos_formulario = request.form.to_dict()
    vaciar_carro = bool(int(datos_formulario["vaciar_carro"]))

    if not vaciar_carro:
        # Se busca en la lista según el código del equipo y se borra junto a la cantidad.
        index_pedido = datos_formulario["index_pedido"]

        if "carro_pedidos" in session.keys():
            # Se elimina según el índice de pedido en el carro
            session["carro_pedidos"].pop(int(index_pedido))
    else:
        session["carro_pedidos"] = []
    
    # Se obtienen los datos de los equipos pedidos para luego mostrar la lista en el front-end
    lista_carro = []
    for index,pedido in enumerate(session["carro_pedidos"]):
        # Se obtiene (para pedido con asignatura asociada o sin asignatura)
        # los datos del equipo solicitado
        sql_query = """
            SELECT id,nombre,marca,modelo
                FROM Equipo
                    WHERE id = %s
        """
        #cursor.execute(sql_query,(pedido[0],))
        cursor = db.query(sql_query,(pedido[0],))

        equipo = cursor.fetchone()

        if equipo is not None:
            # Se agrega el index
            equipo["index_pedido"] = index
            # Se agrega la cantidad pedida
            equipo["cantidad_pedidos"] = pedido[1]
            # Si el pedido tiene asociado una asignatura, se agrega
            if pedido[2] is not None:
                sql_query = """
                    SELECT nombre AS nombre_curso
                        FROM Curso
                            WHERE id = %s
                """
                #cursor.execute(sql_query,(pedido[2],))
                cursor = db.query(sql_query,(pedido[2],))

                curso = cursor.fetchone()

                if curso is not None:
                    # Se agrega la información del curso al equipo
                    equipo.update(curso)
            lista_carro.append(equipo) # Se agrega el pedido final al carro para la vista

    return render_template("/solicitudes_prestamos/seccion_carro_pedidos.html",
        lista_carro=lista_carro)

@mod.route("/registrar_solicitud",methods=["POST"])
def registrar_solicitud():
    # Se registra la solicitud con cada detalle según los pedidos del carro de pedidos

    if "carro_pedidos" in session.keys():
        # Se registra la solicitud
        fecha_registro = datetime.now().replace(microsecond=0)
        sql_query = """
            INSERT INTO Solicitud (rut_alumno,fecha_registro)
                VALUES (%s,%s)
        """
        #cursor.execute(sql_query,(session["usuario"]["rut"],fecha_registro))
        cursor = db.query(sql_query,(session["usuario"]["rut"],fecha_registro))
        
        id_solicitud = cursor.lastrowid # Se obtiene el id de solicitud recién creada

        # Se registran los detalles de solicitud por cada pedido (unitario)
        # con el enlace a la solicitud generada previamente
        error_equipo_inexistente = False
        for pedido in session["carro_pedidos"]:         
            # Se verifica que el equipo aún se encuentre registrado
            sql_query = """
                SELECT id
                    FROM Equipo
                        WHERE id = %s
            """
            #cursor.execute(sql_query,(pedido[0],))
            cursor = db.query(sql_query,(pedido[0],))
            registro_equipo = cursor.fetchone()

            # Si no existe, se omite el detalle y se notifica
            if registro_equipo is None:
                error_equipo_inexistente = True
                continue

            # En caso de que exista, se realiza la creación del detalle de solicitud
            # Se agregan los N detalles
            for i in range(int(pedido[1])):
                # Se verifica si existe la relación con la asignatura
                if pedido[2] is not None:
                    # Existe una relación con una asignatura
                    sql_query = """
                        INSERT INTO Detalle_solicitud (id_solicitud,id_equipo,id_curso_asociado,estado)
                            VALUES (%s,%s,%s,0)
                    """
                    #cursor.execute(sql_query,(id_solicitud,pedido[0],pedido[2]))
                    db.query(sql_query,(id_solicitud,pedido[0],pedido[2]))
                else:
                    sql_query = """
                        INSERT INTO Detalle_solicitud (id_solicitud,id_equipo,estado)
                            VALUES (%s,%s,0)
                    """
                    #cursor.execute(sql_query,(id_solicitud,pedido[0]))
                    db.query(sql_query,(id_solicitud,pedido[0]))
                
        # En caso de que no se haya podido registrar ningún detalle
        # se elimina el encabezado de solicitud
        sql_query = """
            SELECT COUNT(*) AS cantidad_detalles
                FROM Detalle_solicitud
                    WHERE id_solicitud = %s
        """
        #cursor.execute(sql_query,(id_solicitud,))
        cursor = db.query(sql_query,(id_solicitud,))

        cantidad_detalles_generados = cursor.fetchone()

        if cantidad_detalles_generados is not None:
            cantidad_detalles_generados = cantidad_detalles_generados["cantidad_detalles"]
            if cantidad_detalles_generados == 0:
                sql_query = """
                    DELETE FROM Solicitud
                        WHERE id = %s
                """
                #cursor.execute(sql_query,(id_solicitud,))
                db.query(sql_query,(id_solicitud,))

                flash("error-general-detalles") # Ningún detalle pudo ser registrado
        
        if error_equipo_inexistente:
            # Error para alertar que hubieron problemas al registrar detalles
            flash("error-equipos-inexistentes")

    # Se vacía el carro de pedidos una vez registrada la solicitud completa
    session["carro_pedidos"] = []

    flash("solicitud-registrada")
    return redirect("/solicitudes_prestamos")
