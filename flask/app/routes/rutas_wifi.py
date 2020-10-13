from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify, make_response,send_file
from flask_csv import send_csv
from config import db,BASE_DIR
import os,time,bcrypt
from datetime import datetime
import json
from jinja2 import Environment
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.styles.borders import Border, Side, BORDER_THIN

def redirect_url(default='index'): # Redireccionamiento desde donde vino la request
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

mod = Blueprint("rutas_wifi",__name__)
#Modificar Wifi

def consultar_datos_wifi():
    query = ('''
        SELECT *
        FROM Wifi
    '''
    )
    #cursor.execute(query)
    cursor = db.query(query,None)

    wifi = cursor.fetchone()
    return wifi

@mod.route("/modificar_wifi")
def modificar_wifi():
    if 'usuario' not in session or session["usuario"]["id_credencial"] != 3:
        return redirect('/')
    else:
        datos = consultar_datos_wifi()
        return render_template('vistas_gestion_inventario/modificar_wifi.html',
            datos_wifi = datos )

def editar_datos_wifi(informacion_a_actualizar):  # Query UPDATE
            query = ('''
                SELECT *
                FROM Wifi
            '''
            )
            #cursor.execute(query)
            cursor = db.query(query,None)

            wifi = cursor.fetchone()
            if wifi is None:
                query = ('''
                    INSERT INTO Wifi (ssid, bssid, password)
                    VALUES (%s, %s, %s);
                    ''')
                #cursor.execute(query,(
                #    informacion_a_actualizar['ssid'],
                #    informacion_a_actualizar['bssid'],
                #    informacion_a_actualizar['contraseña']))

                db.query(query,(informacion_a_actualizar['ssid'],informacion_a_actualizar['bssid'],informacion_a_actualizar['contraseña']))

                return "OK"
            else:
                query = ('''
                    UPDATE Wifi
                    SET Wifi.ssid = %s,
                        Wifi.bssid = %s,
                        Wifi.password = %s
                        WHERE Wifi.ssid = %s
                        AND Wifi.bssid = %s
                        ''')
                #cursor.execute(query,(
                #informacion_a_actualizar['ssid'],
                #informacion_a_actualizar['bssid'],
                #informacion_a_actualizar['contraseña'],
                #informacion_a_actualizar['ssid_original'],
                #informacion_a_actualizar['bssid_original']
                #))

                db.query(query,(informacion_a_actualizar['ssid'],informacion_a_actualizar['bssid'],informacion_a_actualizar['contraseña'],informacion_a_actualizar['ssid_original'],informacion_a_actualizar['bssid_original']))
                return "OK"

@mod.route('/modificar_wifi/actualizar', methods = ['POST'])
def funcion_editar_wifi():
    if request.method == 'POST':
        informacion_a_actualizar = request.form.to_dict()
        editar_datos_wifi(informacion_a_actualizar)
        return redirect("/modificar_wifi")
