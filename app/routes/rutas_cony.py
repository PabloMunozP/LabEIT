from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify
from config import db,cursor
import os,time,bcrypt

mod = Blueprint("rutas_cony",__name__)

def redirect_url(default='index'): # Redireccionamiento desde donde vino la request
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

@mod.route("/busqueda-solicitudes",methods=["GET"])
def principal():
    return render_template('busqueda-solicitudes\test.html')
