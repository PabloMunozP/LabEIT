from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify
from config import db,cursor
import os, time, bcrypt
import mysql.connector
import rut_chile
import glob
from datetime import datetime, timedelta  

mod = Blueprint("rutas_solicitud_circuito",__name__)

def redirect_url(default='index'): # Redireccionamiento desde donde vino la request
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)


def consultar_lista_circuito():
    query = ('''
        SELECT *
        FROM Circuito
    ''')
    cursor.execute(query)
    return cursor.fetchall()


def consultar_cursos():
    query = ('''
        SELECT id,
            codigo_udp,
            nombre
        FROM Curso
    ''')
    cursor.execute(query)
    return cursor.fetchall()
    
    
@mod.route("/solicitudes_prestamos_circuitos")
def solicitudes_prestamos_circuitos():
    return render_template('solicitudes_prestamos_circuitos/preview.html',
                           lista_circuitos = consultar_lista_circuito(),
                           lista_cursos = consultar_cursos())

@mod.route("/eliminar_carro_circuito",methods=['POST'])
def eliminar_carro_circuito():
    if request.method == "POST":
        id_circuito = request.form["id_circuito"]
        print(session["carro_circuito"][id_circuito])
        del session["carro_circuito"][id_circuito]
        if len(session["carro_circuito"]) == 0:
            del session["carro_circuito"]
        return render_template("solicitudes_prestamos_circuitos/tablas/lista_carro_circuito.html")
    return jsonify({'error':'missing data!'})


@mod.route("/vaciar_carro_circuito",methods=['POST'])
def vaciar_carro_circuito():
    if request.method == "POST":
        del session["carro_circuito"]
        return render_template("solicitudes_prestamos_circuitos/tablas/lista_carro_circuito.html")
    return jsonify({'error':'missing data!'})


@mod.route("/agregar_al_carro_circuito",methods=['POST'])
def agregar_al_carro_circuito():
    if request.method == "POST":
        id_circuito = request.form["id_circuito"]
        cantidad = request.form["cantidad"]
        nombre = request.form["nombre_circuito"]
        if id_circuito and cantidad:
            if 'carro_circuito' not in session: # si no hay carrito
                session["carro_circuito"] = {}
            
            if id_circuito not in session["carro_circuito"].keys(): # Si el circuito no esta en el carro, lo agrega
                session["carro_circuito"][id_circuito] = {} # Crea un diccionario carro = { id : {}}
                session["carro_circuito"][id_circuito]['id'] = str(id_circuito) # carro = { id : {'id': 'id'}}
                session["carro_circuito"][id_circuito]['cantidad'] = int(cantidad)  # carro = { id : {'id': str , 'cantidad' : int}}
                session["carro_circuito"][id_circuito]['nombre'] = nombre #agrega el nombre
            else: # Si el circuito está en el carro, le suma la cantidad
                session["carro_circuito"][id_circuito]['cantidad'] = int(cantidad)    
            return render_template("solicitudes_prestamos_circuitos/tablas/lista_carro_circuito.html")
        else:
            return jsonify({'error':'missing data!'})
    
    return jsonify({'error':'missing data!'})
  
def generar_solicitud_alumno(rut_alumno, motivo, id_curso_motivo, rut_profesor): # funcion para generar la solicitud de circuitos
    # generar Solicitud_circuito
    hora_registro = datetime.now()
    query = ('''
            INSERT INTO Solicitud_circuito (rut_alumno, motivo, id_curso_motivo, rut_profesor, fecha_registro)
            VALUES (%s, %s, %s, %s,  %s)
            ''')
    cursor.execute(query,(rut_alumno,
                          motivo,
                          id_curso_motivo,
                          rut_profesor,
                          hora_registro))
    id_solicitud = cursor.lastrowid # Se obtiene el id de solicitud recién creada
    
    db.commit()
    query = (''' 
             INSERT INTO Detalle_solicitud_circuito (id_solicitud_circuito, id_circuito, cantidad, estado)
             VALUES (%s,%s,%s,0)
             ''')
    for ID,item in session["carro_circuito"].items():
        cursor.execute(query,(id_solicitud,ID,item["cantidad"]))
        db.commit()
    return  


@mod.route("/registrar_solicitud_circuito",methods=['POST'])
def registrar_solicitud_circuito():
    if request.method == "POST":
        datos_solicitud = request.form.to_dict()
        print(datos_solicitud)
        generar_solicitud_alumno(session["usuario"]["rut"],
                                 datos_solicitud["descripcion_motivo"],
                                 datos_solicitud["curso_id"],
                                 None)
        del session["carro_circuito"]
        return redirect('/solicitudes_prestamos_circuitos')
    return jsonify({'error':'missing data!'})





# ---------------------------------------------------------------- #


def consultar_solictudes_pendientes():
    query = ('''
            SELECT Detalle_solicitud_circuito.id AS IDD,
                Detalle_solicitud_circuito.id_solicitud_circuito AS IDS,
                Detalle_solicitud_circuito.cantidad,
                Detalle_solicitud_circuito.id_circuito AS id_componente,
                Solicitud_circuito.fecha_registro,
                Solicitud_circuito.rut_alumno AS rut,
                CASE WHEN Solicitud_circuito.id_curso_motivo = 0 THEN 'Personal'
                    ELSE CONCAT(Curso.codigo_udp, ' ',Curso.nombre)
                    END AS curso_motivo,
                Solicitud_circuito.motivo,
                Usuario.nombres,
                Usuario.apellidos,
                Usuario.email,
                Circuito.nombre as componente,
                Circuito.cantidad - Circuito.prestados AS disponibles,
                Circuito.cantidad AS total,
                Circuito.dias_max_prestamo,
                Circuito.dias_renovacion,
                Circuito.descripcion
            FROM Detalle_solicitud_circuito
                LEFT JOIN Solicitud_circuito 
                    ON Solicitud_circuito.id = Detalle_solicitud_circuito.id_solicitud_circuito
                LEFT JOIN Usuario 
                    ON Usuario.rut = Solicitud_circuito.rut_alumno
                LEFT JOIN Circuito
                    ON Circuito.id = Detalle_solicitud_circuito.id_circuito
                LEFT JOIN Curso
                    ON Solicitud_circuito.id_curso_motivo = Curso.id
            WHERE Detalle_solicitud_circuito.estado = 0
             ''')
    cursor.execute(query)
    return cursor.fetchall()

def consultar_solictudes_activas():
    query = ('''
            SELECT Detalle_solicitud_circuito.id AS IDD,
                Detalle_solicitud_circuito.id_solicitud_circuito AS IDS,
                Detalle_solicitud_circuito.cantidad,
                Detalle_solicitud_circuito.id_circuito AS id_componente,
                Detalle_solicitud_circuito.fecha_inicio,
                Detalle_solicitud_circuito.fecha_termino,
                Solicitud_circuito.fecha_registro,
                Solicitud_circuito.rut_alumno AS rut,
                Estado_detalle_solicitud.nombre AS estado,
                CASE WHEN Solicitud_circuito.id_curso_motivo = 0 THEN 'Personal'
                    ELSE CONCAT(Curso.codigo_udp, ' ',Curso.nombre)
                    END AS curso_motivo,
                Solicitud_circuito.motivo,
                Usuario.nombres,
                Usuario.apellidos,
                Usuario.email,
                Circuito.nombre as componente,
                Circuito.cantidad - Circuito.prestados AS disponibles,
                Circuito.cantidad AS total,
                Circuito.dias_max_prestamo,
                Circuito.dias_renovacion,
                Circuito.descripcion
            FROM Detalle_solicitud_circuito
                LEFT JOIN Solicitud_circuito 
                    ON Solicitud_circuito.id = Detalle_solicitud_circuito.id_solicitud_circuito
                LEFT JOIN Usuario 
                    ON Usuario.rut = Solicitud_circuito.rut_alumno
                LEFT JOIN Circuito
                    ON Circuito.id = Detalle_solicitud_circuito.id_circuito
                LEFT JOIN Curso
                    ON Solicitud_circuito.id_curso_motivo = Curso.id
                LEFT JOIN Estado_detalle_solicitud
                    ON Estado_detalle_solicitud.id = Detalle_solicitud_circuito.estado
            WHERE Detalle_solicitud_circuito.estado IN (1,2,3)
             ''')
    cursor.execute(query)
    return cursor.fetchall()
@mod.route("/gestion_solicitudes_prestamos_circuitos")
def gestion_solicitudes_prestamos_circuitos():
    if 'usuario' not in session or session["usuario"]["id_credencial"] != 3: # Si no es administrador
        return redirect('/')
    return render_template('vistas_gestion_solicitudes_circuitos/main.html',
                           lista_solicitudes_pendientes = consultar_solictudes_pendientes(),
                           lista_solicitudes_activas = consultar_solictudes_activas())
    

@mod.route("/gestion_solicitudes_prestamos_circuitos/borrar_solcitud_detalle",methods=['POST']) # AJAX
def gestion_borrar_solicitud_detalle():
    if request.method == "POST" :
        IDD = request.form["id_solicitud_detalle"]
        IDS = request.form["id_solicitud"]
        query = ('''
            DELETE FROM Detalle_solicitud_circuito
            WHERE Detalle_solicitud_circuito.id = %s
                ''') # borra la solicitud detalle circuit
        cursor.execute(query,(IDD,))
        db.commit()
        query = ('''
            SELECT * FROM Detalle_solicitud_circuito
            WHERE Detalle_solicitud_circuito.id_solicitud_circuito = %s
                ''') # consulta los elementos con esa ID solicutud
        cursor.execute(query,(IDS,))
        if len(cursor.fetchall()) < 1: # si de esa ID solicutud son < 1 los borra
            query = ('''
                DELETE FROM Solicitud_circuito
                WHERE Solicitud_circuito.id = %s
                    ''')
            cursor.execute(query,(IDS,))
            db.commit()
        return jsonify({'nice':'nice!'})
    return jsonify({'error':'missing data!'})
 

@mod.route("/gestion_solicitudes_prestamos_circuitos/aprobar_solcitud_detalle",methods=['POST']) # AJAX
def gestion_aprobar_solicitud_detalle():
    if request.method == "POST" :
        IDD = request.form["id_solicitud_detalle"]
        query = ('''
                SELECT Circuito.id,
                    Circuito.dias_max_prestamo,
                    Circuito.cantidad - Circuito.prestados AS disponibles,
                    Circuito.prestados,
                    Detalle_solicitud_circuito.cantidad AS solicitados
                FROM Circuito
                LEFT JOIN Detalle_solicitud_circuito
                    ON Detalle_solicitud_circuito.id_circuito = Circuito.id
                WHERE Detalle_solicitud_circuito.id = %s
                 ''')
        cursor.execute(query,(IDD,))
        circuito_data = cursor.fetchone()
        print(circuito_data)
        if circuito_data["disponibles"] >= circuito_data["solicitados"]:
            print(datetime.now() + timedelta(days=7))
            cursor.execute('UPDATE Circuito SET prestados = %s WHERE id = %s;', (int(circuito_data["solicitados"]) + int(circuito_data["prestados"]),circuito_data["id"]))
            db.commit()
            cursor.execute('UPDATE Detalle_solicitud_circuito SET estado = 1, fecha_vencimiento = %s WHERE id = %s;',(datetime.now()+timedelta(days=7), IDD))
            db.commit()
            return jsonify({'nice':'nice!'})
        return jsonify({'error':'no hay suficientes componentes!'})
    return jsonify({'error':'missing data!'})

@mod.route("/gestion_solicitudes_prestamos_circuitos/rechazar_solcitud_detalle",methods=['POST']) # AJAX
def rechazar_solcitud_detalle():
    if request.method == 'POST':
        IDD = request.form["id_solicitud_detalle"]
        motivo = request.form["motivo"]
        cursor.execute('UPDATE Detalle_solicitud_circuito SET estado = 5, fecha_rechazo = %s WHERE id = %s;',(datetime.now(),IDD))
        return jsonify({'nice':'nice!'})
    return jsonify({'error':'missing data!'})