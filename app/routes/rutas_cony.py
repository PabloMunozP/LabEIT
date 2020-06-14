from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify
from config import db,cursor
import os,time,bcrypt

mod = Blueprint("rutas_cony",__name__)

def redirect_url(default='index'): # Redireccionamiento desde donde vino la request
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

#@mod.route("/solicitudes_prestamos",methods=["GET"])
def principal():
    return render_template('busqueda-solicitudes/busqueda.html')

@mod.route("/solicitudes_prestamos",methods=["GET"])
def ver_equipos():
    if "usuario" not in session.keys():
        return redirect("/")
    #Query para ver la lista de equipos
    query_ver_equipos="""
        SELECT
            Equipo.id,
            Equipo.codigo,
            Equipo.modelo,
            Equipo.marca,
            Equipo.descripcion,
            Equipo.dias_max_prestamo,
            Etiqueta.descripcion AS etiqueta,
            COUNT(CASE WHEN Equipo_diferenciado.activo = 1 THEN 1 ELSE NULL END) AS disponibles,
            COUNT(Equipo_diferenciado.activo) AS total_equipos
        FROM
            Equipo
            LEFT JOIN Equipo_diferenciado ON Equipo_diferenciado.codigo_equipo = Equipo.codigo,
            Etiqueta, Etiqueta_equipo
        WHERE
            Equipo.id = Etiqueta_equipo.id_equipo AND Etiqueta.id = Etiqueta_equipo.id_etiqueta

        GROUP BY Equipo.codigo

          """
    cursor.execute(query_ver_equipos)
    equipos=cursor.fetchall()
    return render_template("/busqueda-solicitudes/busqueda.html",equipos=equipos)

@mod.route("/solicitudes_prestamos/buscar",methods=["POST"])
def buscar_equipo():
    if 'usuario' not in session:
        return redirect('/')
    if request.method == 'POST':
        busqueda_entrada = request.form.get('busqueda')
        # Query para mostrar resultados de busqueda
        query = '''
            SELECT
                Equipo.id,
                Equipo.codigo,
                Equipo.modelo,
                Equipo.marca,
                Equipo.descripcion,
                Equipo.dias_max_prestamo,
                Etiqueta.descripcion AS etiqueta,
                COUNT(CASE WHEN Equipo_diferenciado.activo = 1 THEN 1 ELSE NULL END) AS disponibles,
                COUNT(Equipo_diferenciado.activo) AS total_equipos
            FROM
                Equipo
                LEFT JOIN Equipo_diferenciado ON Equipo_diferenciado.codigo_equipo = Equipo.codigo,
                Etiqueta, Etiqueta_equipo
            WHERE
                Equipo.id = Etiqueta_equipo.id_equipo AND Etiqueta.id = Etiqueta_equipo.id_etiqueta AND (Equipo.modelo LIKE '%s' OR Equipo.marca LIKE '%s' OR Equipo.codigo LIKE '%s')
            GROUP BY Equipo.codigo'''
        cursor.execute(query,(busqueda_entrada))
        resultados = cursor.fetchall()
        return render_template("/busqueda-solicitudes/busqueda.html",equipos=resultados)
