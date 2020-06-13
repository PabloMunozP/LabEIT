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
    query="""
        SELECT Equipo.codigo AS codigo, Equipo.marca AS marca, Equipo.modelo AS modelo, Equipo.descripcion AS descripcion, Equipo.stock AS stock FROM Equipo
          """
    cursor.execute(query)
    equipos=cursor.fetchall()
    return render_template("/busqueda-solicitudes/ver_equipos.html",equipos=equipos)
