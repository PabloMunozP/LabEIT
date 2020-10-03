import json
from jinja2 import Environment
from datetime import datetime,timedelta
from werkzeug.utils import secure_filename
import os,time,bcrypt,random,timeago,shutil
from config import db,cursor,BASE_DIR,ALLOWED_EXTENSIONS,MAX_CONTENT_LENGTH
from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify,send_file

mod = Blueprint("rutas_estadisticas_solicitudes",__name__)

def redirect_url(default='index'): # Redireccionamiento desde donde vino la request
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

# ========= ESTADÍSTICAS GENERALES ===================
@mod.route("/estadisticas_solicitudes",methods=["GET"])
def estadisticas_solicitudes():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3: # El usuario debe ser un administrador (Credencial = 3)
        return redirect("/")

    # Se obtiene las cantidades según estados de solicitudes de préstamos
    cantidades_solicitudes_estados = {}
    # Solicitudes entrantes (por revisar)
    sql_query = """
        SELECT COUNT(*) as cantidad_solicitudes_entrantes
            FROM Detalle_solicitud
                WHERE estado = 0
    """
    cursor.execute(sql_query)
    cantidades_solicitudes_estados["solicitudes_entrantes"] = cursor.fetchone()["cantidad_solicitudes_entrantes"]

    # Retiros pendientes de solicitudes aprobadas
    sql_query = """
        SELECT COUNT(*) as cantidad_retiros_pendientes
            FROM Detalle_solicitud
                WHERE estado = 1
    """
    cursor.execute(sql_query)
    cantidades_solicitudes_estados["retiros_pendientes"] = cursor.fetchone()["cantidad_retiros_pendientes"]

    # Préstamos activos (en posesión)
    sql_query = """
        SELECT COUNT(*) as cantidad_en_posesion
            FROM Detalle_solicitud
                WHERE estado = 2
    """
    cursor.execute(sql_query)
    cantidades_solicitudes_estados["en_posesion"] = cursor.fetchone()["cantidad_en_posesion"]

    # Préstamos con atrasos
    sql_query = """
        SELECT COUNT(*) as cantidad_con_atrasos
            FROM Detalle_solicitud
                WHERE estado = 3
    """
    cursor.execute(sql_query)
    cantidades_solicitudes_estados["con_atrasos"] = cursor.fetchone()["cantidad_con_atrasos"]

    # Préstamos finalizados (Se contabilizan los que se encuentran aún en estado 'devuelto')
    sql_query = """
        SELECT COUNT(*) as cantidad_finalizados
            FROM Detalle_solicitud
                WHERE estado = 4
                OR estado = 6
    """
    cursor.execute(sql_query)
    cantidades_solicitudes_estados["finalizados"] = cursor.fetchone()["cantidad_finalizados"]

    # Solicitudes rechazadas y canceladas
    # Préstamos finalizados (Se contabilizan los que se encuentran aún en estado 'devuelto')
    sql_query = """
        SELECT COUNT(*) as cantidad_rechazadas_canceladas
            FROM Detalle_solicitud
                WHERE estado = 5
                OR estado = 7
    """
    cursor.execute(sql_query)
    cantidades_solicitudes_estados["rechazadas_canceladas"] = cursor.fetchone()["cantidad_rechazadas_canceladas"]

    # Se obtiene la lista de usuarios registrados
    sql_query = """
        SELECT rut,nombres,apellidos
            FROM Usuario
                ORDER BY apellidos,nombres
    """
    cursor.execute(sql_query)
    lista_usuarios = cursor.fetchall()

    # Se obtiene la lista de asignaturas asociadas a los detalles de solicitud junto a su cantidad
    sql_query = """
        SELECT Curso.id,Curso.codigo_udp,Curso.nombre,
            (SELECT COUNT(*) FROM Detalle_solicitud WHERE id_curso_asociado = Curso.id) AS 'cantidad_detalles_asociados'
                FROM Curso
                    ORDER BY cantidad_detalles_asociados DESC
    """
    cursor.execute(sql_query)
    lista_asignaturas_asociadas = cursor.fetchall()

    return render_template("/estadisticas/estadisticas_solicitudes.html",
        cantidades_solicitudes_estados=cantidades_solicitudes_estados,
        lista_usuarios=lista_usuarios,
        lista_asignaturas_asociadas=lista_asignaturas_asociadas)

@mod.route("/consultar_estadisticas_solicitudes",methods=["POST"])
def consultar_estadisticas_solicitudes():
    # Se obtiene la lista de equipos que se han solicitado en cualquiera de los estados
    # durante las fechas "desde" (limite_inferior) y "hasta" (limite_superior) indicadas.

    datos_formulario = request.form.to_dict()
    datos_formulario["id_consulta"] = int(datos_formulario["id_consulta"])

    # Se convierte la variable JSON a una lista de Python
    datos_formulario["ids_asignaturas_filtro"] = json.loads(datos_formulario["ids_asignaturas_filtro"])

    asignaturas_asociadas = False
    # En caso de que se hayan seleccionado asignaturas para filtrar
    # se modifica la consulta
    if len(datos_formulario["ids_asignaturas_filtro"]):
        asignaturas_asociadas = True

    if datos_formulario["id_consulta"] == 1:
        # Consulta 1: Se obtienen los equipos solicitados entre los días solicitados

        # Se agrega la hora 23:59 a las fechas para cubrir los días límites en su totalidad
        datos_formulario["limite_inferior"] = datetime.strptime(datos_formulario["limite_inferior"],"%Y-%m-%d").replace(hour=0,minute=0)
        datos_formulario["limite_superior"] = datetime.strptime(datos_formulario["limite_superior"],"%Y-%m-%d").replace(hour=23,minute=59)

        limite_inferior_iteracion = datos_formulario["limite_inferior"]
        limite_superior_iteracion = limite_inferior_iteracion.replace(hour=23,minute=59)

        datos_finales_grafico = []

        sql_query = """
            SELECT Equipo.id,Equipo.nombre,Equipo.marca,Equipo.modelo
                FROM Equipo
        """
        cursor.execute(sql_query)
        lista_equipos_registrados = cursor.fetchall()

        if not len(lista_equipos_registrados):
            return jsonify([])

        # Se crea la lista con las categorías para posteriormente ponerlas en el gráfico
        lista_categorias = []
        lista_categorias.append("Equipo")
        for equipo in lista_equipos_registrados:
            label_equipo = ""+equipo["nombre"]+" "+equipo["marca"]+" "+equipo["modelo"]
            lista_categorias.append(label_equipo)
        dict_chart = {'role':'annotation'} # Necesario según documentación de Google Charts
        lista_categorias.append(dict(dict_chart))
        datos_finales_grafico.append(lista_categorias)

        while limite_inferior_iteracion <= datos_formulario["limite_superior"]:
            # Fila
            datos_fila = []
            # Se agrega la fecha en la primera columna (por documentación de Google Charts)
            datos_fila.append(str(limite_inferior_iteracion.date()))

            for equipo in lista_equipos_registrados:
                # Se seleccionan los equipos según las fechas
                # Se verifica si se filtró por asignaturas
                if asignaturas_asociadas:
                    # Se filtra en la consulta sql según las asignaturas
                    sql_query = """
                    SELECT COUNT(*) AS cantidad_equipos
                        FROM Equipo,Detalle_solicitud,Solicitud
                            WHERE Equipo.id = Detalle_solicitud.id_equipo
                            AND Detalle_solicitud.id_solicitud = Solicitud.id
                            AND Solicitud.fecha_registro >= %s
                            AND Solicitud.fecha_registro <= %s
                            AND Equipo.id = %s
                            AND Detalle_solicitud.id_curso_asociado IN {0}
                            GROUP BY Equipo.id
                    """
                    string_lista_ids = str(datos_formulario["ids_asignaturas_filtro"]).replace("[","(").replace("]",")")
                    sql_query = sql_query.format(string_lista_ids)
                    cursor.execute(sql_query,(limite_inferior_iteracion,limite_superior_iteracion,equipo["id"]))
                    registro_cantidad = cursor.fetchone()
                else:
                    sql_query = """
                    SELECT COUNT(*) AS cantidad_equipos
                        FROM Equipo,Detalle_solicitud,Solicitud
                            WHERE Equipo.id = Detalle_solicitud.id_equipo
                            AND Detalle_solicitud.id_solicitud = Solicitud.id
                            AND Solicitud.fecha_registro >= %s
                            AND Solicitud.fecha_registro <= %s
                            AND Equipo.id = %s
                            GROUP BY Equipo.id
                    """
                    cursor.execute(sql_query,(limite_inferior_iteracion,limite_superior_iteracion,equipo["id"]))
                    registro_cantidad = cursor.fetchone()

                if registro_cantidad is None:
                    cantidad_equipos = 0
                else:
                    cantidad_equipos = registro_cantidad["cantidad_equipos"]
                datos_fila.append(cantidad_equipos)
            datos_fila.append("")
            datos_finales_grafico.append(datos_fila)

            # Se aumenta 1 día a ambos límites, inferior y superior
            limite_inferior_iteracion += timedelta(days=1)
            limite_superior_iteracion += timedelta(days=1)


        return jsonify(datos_finales_grafico)

    elif datos_formulario["id_consulta"] == 2:
        # Consulta 2: Se obtienen las cantidades para cada equipo solicitado según las fechas del formulario
        # en los distintos estados de solicitudes (por revisar, por retirar, etc)

        # Se agrega la hora 23:59 a las fechas para cubrir los días límites en su totalidad
        datos_formulario["limite_inferior"] = str(datetime.strptime(datos_formulario["limite_inferior"],"%Y-%m-%d").replace(hour=0,minute=0))
        datos_formulario["limite_superior"] = str(datetime.strptime(datos_formulario["limite_superior"],"%Y-%m-%d").replace(hour=23,minute=59))

        # Se obtiene la lista de estados para poder realizar las consultar por cada una de ellas
        sql_query = """
            SELECT Estado_detalle_solicitud.id,Estado_detalle_solicitud.nombre
                FROM Estado_detalle_solicitud
        """
        cursor.execute(sql_query)
        lista_estados = cursor.fetchall()

        # Se obtienen los equipos según las fechas del formulario para categorías en el gráfico
        sql_query = """
            SELECT Equipo.id,Equipo.nombre,Equipo.marca,Equipo.modelo
                FROM Equipo,Detalle_solicitud,Solicitud
                    WHERE Equipo.id = Detalle_solicitud.id_equipo
                    AND Detalle_solicitud.id_solicitud = Solicitud.id
                    AND Solicitud.fecha_registro >= %s
                    AND Solicitud.fecha_registro <= %s
                    GROUP BY Equipo.id
        """
        cursor.execute(sql_query,(datos_formulario["limite_inferior"],datos_formulario["limite_superior"]))
        lista_equipos = cursor.fetchall()

        if not len(lista_equipos):
            return jsonify([])

        # Se crea la lista con las categorías para posteriormente ponerlas en el gráfico
        lista_categorias = []
        lista_categorias.append("Equipo")
        for equipo in lista_equipos:
            label_equipo = ""+equipo["nombre"]+" "+equipo["marca"]+" "+equipo["modelo"]
            lista_categorias.append(label_equipo)
        dict_chart = {'role':'annotation'} # Necesario según documentación de Google Charts
        lista_categorias.append(dict(dict_chart))

        # Para cada equipo y para cada estado se obtiene la cantidad de detalles de solicitudes asociados
        # según la fecha de registro

        datos_grafico = {}
        for estado in lista_estados:
            datos_grafico[estado["nombre"]] = []
            datos_grafico[estado["nombre"]].append(estado["nombre"])
            for equipo in lista_equipos:
                if asignaturas_asociadas:
                    sql_query = """
                        SELECT COUNT(*) AS cantidad_equipos
                            FROM Equipo,Detalle_solicitud,Solicitud,Estado_detalle_solicitud
                                WHERE Equipo.id = Detalle_solicitud.id_equipo
                                AND Detalle_solicitud.id_solicitud = Solicitud.id
                                AND Solicitud.fecha_registro >= %s
                                AND Solicitud.fecha_registro <= %s
                                AND Detalle_solicitud.estado = Estado_detalle_solicitud.id
                                AND Estado_detalle_solicitud.id = %s
                                AND Equipo.id = %s
                                AND Detalle_solicitud.id_curso_asociado IN {0}
                                GROUP BY Equipo.id
                    """
                    string_lista_ids = str(datos_formulario["ids_asignaturas_filtro"]).replace("[","(").replace("]",")")
                    sql_query = sql_query.format(string_lista_ids)
                    cursor.execute(sql_query,(datos_formulario["limite_inferior"],datos_formulario["limite_superior"],estado["id"],equipo["id"]))
                    cantidad_equipos = cursor.fetchone()
                else:
                    sql_query = """
                        SELECT COUNT(*) AS cantidad_equipos
                            FROM Equipo,Detalle_solicitud,Solicitud,Estado_detalle_solicitud
                                WHERE Equipo.id = Detalle_solicitud.id_equipo
                                AND Detalle_solicitud.id_solicitud = Solicitud.id
                                AND Solicitud.fecha_registro >= %s
                                AND Solicitud.fecha_registro <= %s
                                AND Detalle_solicitud.estado = Estado_detalle_solicitud.id
                                AND Estado_detalle_solicitud.id = %s
                                AND Equipo.id = %s
                                GROUP BY Equipo.id
                    """
                    cursor.execute(sql_query,(datos_formulario["limite_inferior"],datos_formulario["limite_superior"],estado["id"],equipo["id"]))
                    cantidad_equipos = cursor.fetchone()

                if cantidad_equipos is None:
                    cantidad_equipos = 0
                else:
                    cantidad_equipos = cantidad_equipos["cantidad_equipos"]

                datos_grafico[estado["nombre"]].append(cantidad_equipos)
            datos_grafico[estado["nombre"]].append("")

        # Se crea el objeto final con todos los datos según lo establecido en la API de Google Charts
        datos_finales = []
        datos_finales.append(lista_categorias)
        for estado in datos_grafico:
            datos_finales.append(datos_grafico[estado])

        return jsonify(datos_finales)