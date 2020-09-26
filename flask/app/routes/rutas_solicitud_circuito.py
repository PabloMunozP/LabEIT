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
        generar_solicitud_alumno(session["usuario"]["rut"],
                                 datos_solicitud["descripcion_motivo"],
                                 datos_solicitud["curso_id"],
                                 None)
        del session["carro_circuito"]
        return redirect('/solicitudes_prestamos_circuitos')
    return jsonify({'error':'missing data!'})





# ---------------------------------------------------------------- #

def consultar_solictudes_por_id(IDS):
    query = ('''
            SELECT Detalle_solicitud_circuito.id AS IDD,
                Detalle_solicitud_circuito.id_solicitud_circuito AS IDS,
                Detalle_solicitud_circuito.cantidad,
                Detalle_solicitud_circuito.id_circuito AS id_componente,
                Detalle_solicitud_circuito.fecha_inicio,
                Detalle_solicitud_circuito.fecha_termino,
                Detalle_solicitud_circuito.fecha_vencimiento,
                Detalle_solicitud_circuito.renovaciones,
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
            WHERE Solicitud_circuito.id = %s
             ''')
    cursor.execute(query,(IDS,))
    return cursor.fetchall()

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
                Detalle_solicitud_circuito.fecha_vencimiento,
                Detalle_solicitud_circuito.renovaciones,
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

def consultar_solictudes_historial():
    query = ('''
            SELECT Detalle_solicitud_circuito.id AS IDD,
                Detalle_solicitud_circuito.id_solicitud_circuito AS IDS,
                Detalle_solicitud_circuito.cantidad,
                Detalle_solicitud_circuito.id_circuito AS id_componente,
                Detalle_solicitud_circuito.fecha_inicio,
                Detalle_solicitud_circuito.fecha_termino,
                Detalle_solicitud_circuito.fecha_vencimiento,
                Detalle_solicitud_circuito.fecha_devolucion,
                Detalle_solicitud_circuito.renovaciones,
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
            WHERE Detalle_solicitud_circuito.estado NOT IN (0,1,2,3)
             ''')
    cursor.execute(query)
    return cursor.fetchall()

def consultar_solcitudes_prestamos():
    cursor.execute('''
                SELECT Solicitud_circuito.id,
                    Solicitud_circuito.rut_alumno,
                    Solicitud_circuito.motivo,
                    Solicitud_circuito.id_curso_motivo,
                    Solicitud_circuito.fecha_registro,
                    Usuario.email,
                    CONCAT(Usuario.nombres, ' ',Usuario.apellidos) AS nombre,
                    COUNT(Detalle_solicitud_circuito.id_solicitud_circuito) AS componentes_solicitados,
                    CASE WHEN Solicitud_circuito.id_curso_motivo = 0 THEN 'Personal'
                        ELSE CONCAT(Curso.codigo_udp, ' ',Curso.nombre)
                        END AS curso_motivo
                FROM Solicitud_circuito
                LEFT JOIN Usuario 
                    ON Usuario.rut = Solicitud_circuito.rut_alumno
                LEFT JOIN Detalle_solicitud_circuito
                    ON Detalle_solicitud_circuito.id_solicitud_circuito = Solicitud_circuito.id
                LEFT JOIN Curso
                    ON Solicitud_circuito.id_curso_motivo = Curso.id
                GROUP BY Detalle_solicitud_circuito.id_solicitud_circuito
                   ''')
    return cursor.fetchall()

@mod.route("/gestion_solicitudes_prestamos_circuitos")
def gestion_solicitudes_prestamos_circuitos():
    if 'usuario' not in session or session["usuario"]["id_credencial"] != 3: # Si no es administrador
        return redirect('/')
    if 'carro_circuito_admin' in session:
        del session["carro_circuito_admin"] 
    return render_template('vistas_gestion_solicitudes_circuitos/main.html',
                           lista_solicitudes_pendientes = consultar_solictudes_pendientes(),
                           lista_solicitudes_activas = consultar_solictudes_activas(),
                           lista_solicitudes_historial = consultar_solictudes_historial(),
                           lista_solicitudes_prestamos = consultar_solcitudes_prestamos(),
                           lista_componentes = consultar_lista_circuito(),
                           lista_cursos = consultar_cursos())
    

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

        if circuito_data["disponibles"] >= circuito_data["solicitados"]:
            cursor.execute('UPDATE Circuito SET prestados = %s WHERE id = %s;', (int(circuito_data["solicitados"]) + int(circuito_data["prestados"]),circuito_data["id"]))
            db.commit()
            vencimiento = datetime.now()+timedelta(days=7)
            cursor.execute('UPDATE Detalle_solicitud_circuito SET estado = 1, fecha_vencimiento = %s WHERE id = %s;',(vencimiento.replace(hour=18, minute=30, second = 0, microsecond = 0), IDD))
            db.commit()
            return jsonify({'nice':'nice!'})
        return jsonify({'error':'no hay suficientes componentes!'})
    return jsonify({'error':'missing data!'})

@mod.route("/gestion_solicitudes_prestamos_circuitos/rechazar_solicitud_detalle",methods=['POST']) # AJAX
def rechazar_solcitud_detalle():
    if request.method == 'POST':
        IDD = request.form["id_solicitud_detalle"]
        motivo = request.form["motivo"]
        cursor.execute('UPDATE Detalle_solicitud_circuito SET estado = 5, fecha_rechazo = %s, fecha_vencimiento = %s WHERE id = %s;',(datetime.now(), None,IDD))
        db.commit()
        return jsonify({'nice':'nice!'})
    return jsonify({'error':'missing data!'})

@mod.route("/gestion_solicitudes_prestamos_circuitos/entregar_solicitud_detalle",methods=['POST']) # AJAX
def entregar_solicitud_detalle():
    if request.method == 'POST':
        IDD = request.form["id_solicitud_detalle"]
        query = ('''
                SELECT Circuito.id,
                    Circuito.dias_max_prestamo
                FROM Circuito
                RIGHT JOIN Detalle_solicitud_circuito
                    ON Detalle_solicitud_circuito.id_circuito = Circuito.id
                WHERE Detalle_solicitud_circuito.id = %s
                 ''')
        cursor.execute(query,(IDD,))
        circuito_data = cursor.fetchone()
        fecha_inicio = datetime.now()
        fecha_termino = datetime.now() + timedelta(days=int(circuito_data["dias_max_prestamo"]))
        cursor.execute('''
                    UPDATE Detalle_solicitud_circuito 
                    SET estado = 2,
                        fecha_inicio = %s,
                        fecha_termino = %s, 
                        fecha_vencimiento = %s
                    WHERE id = %s;''',(fecha_inicio,
                                       fecha_termino.replace(hour=18, minute=30, second = 0, microsecond = 0),
                                       None,
                                       IDD))
        db.commit()
        return jsonify({'nice':'nice!'})
    return jsonify({'error':'missing data!'})



@mod.route("/gestion_solicitudes_prestamos_circuitos/devolver_solicitud_detalle",methods=['POST']) # AJAX
def devolver_solicitud_detalle():
    if request.method == 'POST':
        IDD = request.form["id_solicitud_detalle"]
        fecha_devolucion = request.form["fecha_devolucion"]
        query = ('''
                SELECT Circuito.id,
                    Circuito.prestados,
                    Detalle_solicitud_circuito.cantidad AS solicitados
                FROM Circuito
                LEFT JOIN Detalle_solicitud_circuito
                    ON Detalle_solicitud_circuito.id_circuito = Circuito.id
                WHERE Detalle_solicitud_circuito.id = %s
                 ''') # Query para obtener datos de la solicitud y componente
        cursor.execute(query,(IDD,))
        circuito_data = cursor.fetchone() 
        query = ('''
                UPDATE Detalle_solicitud_circuito
                    SET estado = 4,
                        fecha_devolucion = %s
                    WHERE id = %s;
                ''') # Actualiza la solicitud detalle como devuelto
        if fecha_devolucion == '': # Si en el formulario no hay una fecha designada
            cursor.execute(query,(datetime.now(), # Le da fecha y hora actual
                                  IDD))
        else:                      # Si en el formario hay una fecha designada
            cursor.execute(query,(fecha_devolucion, # Usa la fecha del formulario
                                  IDD))
        cursor.execute('UPDATE Circuito SET Circuito.prestados = %s WHERE Circuito.id = %s',(int(circuito_data["prestados"])-int(circuito_data["solicitados"]),
                                                                                             circuito_data["id"]))
        # Actualiza los prestados = prestados - solicitados (los devuelve)
        return jsonify({'nice':'nice!'})
    return jsonify({'error':'missing data!'})       
    
@mod.route("/gestion_solicitudes_prestamos_circuitos/cancelar_activa_solicitud_detalle",methods=['POST']) # AJAX
def cancelar_solicitud_detalle():
    if request.method == 'POST':
        IDD = request.form["id_solicitud_detalle"]
        motivo = request.form["motivo"]
        query = ('''
                SELECT Circuito.id,
                    Circuito.prestados,
                    Detalle_solicitud_circuito.cantidad AS solicitados
                FROM Circuito
                LEFT JOIN Detalle_solicitud_circuito
                    ON Detalle_solicitud_circuito.id_circuito = Circuito.id
                WHERE Detalle_solicitud_circuito.id = %s
                 ''') # Query para obtener datos de la solicitud y componente
        cursor.execute(query,(IDD,)) # Ejecuta la query
        circuito_data = cursor.fetchone() # Almacena el resutado
        query = (''' 
                UPDATE Detalle_solicitud_circuito
                    SET estado = 7,
                        fecha_cancelacion = %s,
                        fecha_vencimiento = NULL
                    WHERE id = %s;
                ''') # Actualiza la solicitud detalle como cancelada 
        cursor.execute(query,(datetime.now(),IDD)) # Establece la fecha para la solicitud
        cursor.execute('UPDATE Circuito SET Circuito.prestados = %s WHERE Circuito.id = %s',
                       (int(circuito_data["prestados"])-int(circuito_data["solicitados"]),
                        circuito_data["id"])) # Actualiza los prestados = prestados - solicitados (los devuelve)
        return jsonify({'nice':'nice!'})
    return jsonify({'error':'missing data!'})



@mod.route("/gestion_solicitudes_prestamos_circuitos/consultar_tabla_solicitud",methods=['POST']) # AJAX
def consultar_tabla_solicitud():
    if request.method == 'POST':
        IDS = request.form["id_solicitud"]
        return render_template('vistas_gestion_solicitudes_circuitos/tablas/sub_detalle.html',
                               solicitudes = consultar_solictudes_por_id(IDS))
    return jsonify({'error':'missing data!'})




@mod.route("/gestion_solicitudes_prestamos_circuitos/agregar_carro",methods=['POST'])
def gestion_agregar_carro():
    if request.method == "POST":
        id_circuito = request.form["id_circuito"]
        disponibles = request.form["disponibles"]
        cantidad = 0
        nombre = request.form["nombre_circuito"]
        if id_circuito and nombre:
            if 'carro_circuito_admin' not in session: # si no hay carrito
                session["carro_circuito_admin"] = {}
            
            if id_circuito not in session["carro_circuito_admin"].keys(): # Si el circuito no esta en el carro, lo agrega
                session["carro_circuito_admin"][id_circuito] = {} # Crea un diccionario carro = { id : {}}
                session["carro_circuito_admin"][id_circuito]['id'] = str(id_circuito) # carro = { id : {'id': 'id'}}
                session["carro_circuito_admin"][id_circuito]['cantidad'] = int(cantidad)  # carro = { id : {'id': str , 'cantidad' : int}}
                session["carro_circuito_admin"][id_circuito]['nombre'] = nombre #agrega el nombre
                session["carro_circuito_admin"][id_circuito]['disponibles'] = disponibles # determina la disponibilidad
            else: # Si el circuito está en el carro, le suma la cantidad
                session["carro_circuito_admin"][id_circuito]['cantidad'] = int(cantidad)    
            return render_template("vistas_gestion_solicitudes_circuitos/tablas/sub_solicitud_agil.html")
        else:
            return jsonify({'error':'missing data!'})
    
    return jsonify({'error':'missing data!'})


@mod.route("/gestion_solicitudes_prestamos_circuitos/eliminar_carro",methods=['POST'])
def gestion_eliminar_carro():
    if request.method == "POST":
        id_circuito = request.form["id_circuito"]
        del session["carro_circuito_admin"][id_circuito]
        if len(session["carro_circuito_admin"]) == 0:
            del session["carro_circuito_admin"]
        return render_template("vistas_gestion_solicitudes_circuitos/tablas/sub_solicitud_agil.html")
    return jsonify({'error':'missing data!'})


@mod.route("/gestion_solicitudes_prestamos_circuitos/actualizar_carro",methods=['POST'])
def gestion_actualizar_carro():
    if request.method == "POST":
        id_circuito = request.form["id_circuito"]
        cantidad = request.form["cantidad"]
        if int(cantidad) > int(session["carro_circuito_admin"][id_circuito]['disponibles']):
            return jsonify({'error':'data error!'})
        else:
            session["carro_circuito_admin"][id_circuito]['cantidad'] = int(cantidad)
            return jsonify({'nice':'nice!'})
        
    


def generar_solicitud_agil(rut_alumno, motivo, id_curso_motivo, rut_profesor): # funcion para generar la solicitud de circuitos
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


@mod.route("/gestion_solicitudes_prestamos_circuitos/confirmar_solicitud_agil",methods=['POST']) # AJAX
def confirmar_solicitud_agil():
    if request.method == "POST":
        datos_solicitud = request.form.to_dict()
        fecha_registro = datetime.now()
        cursor.execute(''' SELECT rut FROM Usuario WHERE rut = %s''',(datos_solicitud['rut_usuario'],)) # Consulta para comprobar que el usuario existe
        if len(cursor.fetchall()) > 0:
            
            
            query_insert_sol = ('''INSERT INTO Solicitud_circuito (rut_alumno, motivo, id_curso_motivo, rut_profesor, fecha_registro) VALUES (%s, %s, %s, %s,  %s)''') # Query agregar una solicitud
            query_select_circuito_data = ('''SELECT * FROM Circuito WHERE id = %s''') # Query para consultar la informacion del componente
            query_insert_detalle = ('''INSERT INTO Detalle_solicitud_circuito (id_solicitud_circuito, id_circuito, cantidad, estado, fecha_inicio, fecha_termino) VALUES (%s,%s,%s,2,%s,%s)''')
            query_update_prestados = ('UPDATE Circuito SET Circuito.prestados = %s WHERE Circuito.id = %s')
            
            cursor.execute(query_insert_sol,(datos_solicitud['rut_usuario'],None,datos_solicitud['curso_id'],None,fecha_registro)) # Agrega la solictud a la base de dato
            id_solicitud = cursor.lastrowid # Se obtiene el id de solicitud recién creada
        
            
            for ID,item in session["carro_circuito_admin"].items():
                if item['cantidad'] > 0: # Si la cantidad solicitada es < 0 la registra
                    
                    cursor.execute(query_select_circuito_data,(ID,)) # Obtiene los datos del componente
                    circuito_data = cursor.fetchone() # Almacena los datos del componente
                    
                    fecha_termino = fecha_registro+timedelta(days=int(circuito_data["dias_max_prestamo"])) # Obtiene la fecha de termino
                    cursor.execute( query_insert_detalle, (id_solicitud,ID,item["cantidad"],fecha_registro,fecha_termino.replace(hour=18, minute=30, second = 0, microsecond = 0))) # Genera el registro de la solictud_detalle_circuito
                    
                    cursor.execute(query_update_prestados, (int(circuito_data["cantidad"]) + int(circuito_data["prestados"]), ID))
                    
            return jsonify({'nice':'nice!'})
        else:
            return jsonify({'error':'user'})
        
    return jsonify({'error':'missing data!'})