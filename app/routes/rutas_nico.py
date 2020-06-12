from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify
from config import db,cursor
import os,time,bcrypt

def redirect_url(default='index'): # Redireccionamiento desde donde vino la request
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

mod = Blueprint("rutas_nico",__name__)

@mod.route("/nico",methods=["GET"])
def principal():
    return "OK"


@mod.route("/gestion_inventario_admin")
def gestion_inventario_admin():
    return render_template('vistas_gestion_inventario/gestion_inventario.html')