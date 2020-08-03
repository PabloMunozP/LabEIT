from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify
from config import db,cursor
import os,time,bcrypt
from datetime import datetime

mod = Blueprint("rutas_lorenzo",__name__)

def redirect_url(default='index'): # Redireccionamiento desde donde vino la request
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

@mod.route("/wishlist_usuario",methods=["GET", "POST"])
def tabla_wishlist():
    if "usuario" not in session.keys():
        return redirect("/")
        
    if request.method == "POST":
        fecha_solicitud_wishlist = datetime.now()
        form = request.form.to_dict()
        sql_query= """
            INSERT INTO Wishlist
                (rut_solicitante,nombre_equipo,marca_equipo,modelo_equipo,motivo_academico,fecha_solicitud)
                    VALUES (%s,%s,%s,%s,%s,%s)
        """
        cursor.execute(sql_query,(session["usuario"]["rut"],form["nombre"],form["marca"],form["modelo"],form["motivo"],fecha_solicitud_wishlist))
        cursor.execute("SELECT MAX(id) FROM Wishlist")
        last_id = cursor.lastrowid
        sql_query= """
            INSERT INTO Url_wishlist (url,id_wishlist)
                VALUES (%s,%s)
        """
        cursor.execute(sql_query,(form["url"],last_id))

    sql_query = """
        SELECT *
            FROM Wishlist
                WHERE estado_wishlist = 8
    """
    cursor.execute(sql_query)
    lista_wishlist_aceptada = cursor.fetchall()

    sql_query = """
        SELECT *
            FROM Wishlist
                WHERE rut_solicitante = %s
    """
    cursor.execute(sql_query,(session["usuario"]["rut"],))
    lista_solicitudes_wishlist = cursor.fetchall()
    
    return render_template("/wishlist/user_wishlist.html",
        lista_wishlist_aceptada=lista_wishlist_aceptada,
        lista_solicitudes_wishlist=lista_solicitudes_wishlist)

@mod.route("/gestion_wishlist",methods=["GET"])
def gestionar_wishlist():
    if "usuario" not in session.keys():
        return redirect("/")
    return render_template("/wishlist/admin_wishlist.html")