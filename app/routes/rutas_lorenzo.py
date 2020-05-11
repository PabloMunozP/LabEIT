from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify
#from config import db,cursor
import os,time,bcrypt

mod = Blueprint("rutas_lorenzo",__name__)

@mod.route("/lorenzo",methods=["GET"])
def principal():
    return "OK"
