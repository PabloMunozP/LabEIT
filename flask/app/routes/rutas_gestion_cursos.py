from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify
from config import db,cursor
from datetime import datetime,timedelta
import os,time

mod = Blueprint("rutas_gestion_cursos",__name__)

def redirect_url(default='index'): # Redireccionamiento desde donde vino la request
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

#*********************************************************************************************#

# == VISTA PRINCIPAL GESTION DE CURSOS

# Consulta una lista con todos los cursos
def consultar_lista_cursos():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")
    query = ('''
    SELECT *
        FROM Curso
    ''')
    cursor.execute(query)
    cursos = cursor.fetchall()
    return cursos
def consultar_lista_cursos_secciones():
    query = ("""
        SELECT
            Seccion.id,
            Seccion.rut_profesor,
            Seccion.codigo AS codigo_seccion,
            Seccion.id_curso,
            Curso.codigo_udp,
            Curso.nombre
            FROM Seccion
            LEFT JOIN Curso ON Curso.id = Seccion.id_curso
    """)
    cursor.execute(query)
    secciones = cursor.fetchall()
    return secciones

@mod.route("/gestion_cursos")
def gestion_cursos():
    if 'usuario' not in session or session["usuario"]["id_credencial"] != 3:
        return redirect('/')
    else:
        cursos = consultar_lista_cursos()
        secciones = consultar_lista_cursos_secciones()
        return render_template('gestion_cursos/ver_cursos.html', cursos = cursos, secciones = secciones)

def consultar_curso(codigo):
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")
    query = ('''
        SELECT
            Curso.id as curso_id,
            Curso.codigo_udp,
            Curso.nombre,
            Curso.descripcion
            FROM Curso
            WHERE Curso.codigo_udp = %s
    ''')
    cursor.execute(query,(codigo,))
    curso = cursor.fetchone()
    return curso

def consultar_curso_secciones(codigo):
    query = ('''
        SELECT
            Seccion.id,
            Seccion.rut_profesor,
            Usuario.nombres AS nombres_profesor, Usuario.apellidos AS apellidos_profesor,
            Seccion.codigo AS codigo_seccion,
            Seccion.id_curso,
            Curso.codigo_udp,
            Curso.nombre
            FROM Seccion
            LEFT JOIN Curso ON Curso.id = Seccion.id_curso
            LEFT JOIN Usuario On Usuario.rut = Seccion.rut_profesor
            WHERE Curso.codigo_udp = %s
    ''')
    cursor.execute(query,(codigo,))
    secciones = cursor.fetchall()
    return secciones

def consultar_profesores():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")
    query = ('''
        SELECT *
            FROM Usuario
            WHERE Usuario.id_credencial = 2 AND Usuario.activo = 1
    ''')
    cursor.execute(query)
    profesores = cursor.fetchall()
    return profesores

@mod.route("/gestion_cursos/detalles_curso/<string:codigo_udp>",methods=["GET"])
def secciones_curso(codigo_udp):
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3: # El usuario debe ser un administrador (Credencial = 3)
        return redirect("/")

    curso = consultar_curso(codigo_udp)
    secciones = consultar_curso_secciones(codigo_udp)
    profesores = consultar_profesores()
    return render_template("/gestion_cursos/detalles_curso.html", curso=curso, secciones=secciones,profesores=profesores)
# == VISTA PRINCIPAL/MODAL "AGREGAR CURSO" ==

def agregar_curso(val):
    query = ('''
    INSERT INTO Curso (codigo_udp, nombre, descripcion)
    VALUES (%s, %s, %s);
    ''')
    cursor.execute(query, (
        val['codigo_udp'],
        val['nombre'],
        val['descripcion']))
    db.commit()
    return 'OK'

@mod.route("/gestion_cursos/agregar_curso", methods = ['POST'])
def agregar_curso_form():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")
    if request.method == 'POST':
        valores = request.form.to_dict()
        agregar_curso(valores)
        flash("El curso fue agregado correctamente")
        cursos = consultar_lista_cursos()
        return redirect('/gestion_cursos')

def agregar_curso_seccion(val):
    query = ('''
    INSERT INTO Seccion (id_curso, rut_profesor, codigo)
    VALUES (%s, %s, %s);
    ''')
    cursor.execute(query, (
        val['id_curso'],
        val['rut_profesor'],
        val['codigo']))
    db.commit()
    return 'OK'

def redirigir_detalle(val):
    query = ('''
        SELECT codigo_udp FROM Curso WHERE Curso.id = %s
    ''')
    cursor.execute(query, (val,))
    resultado = cursor.fetchone()
    return resultado

@mod.route("/gestion_cursos/agregar_seccion", methods = ['POST'])
def agregar_curso_seccion_form():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")
    if request.method == 'POST':
        valores = request.form.to_dict()
        agregar_curso_seccion(valores)
        curso = redirigir_detalle(valores["id_curso"])
        flash("La seccion fue agregada correctamente")
        return redirect('/gestion_cursos/detalles_curso/'+curso['codigo_udp'])


# == VISTA PRINCIPAL/MODAL "EDITAR CURSO" ==

def editar_curso(val):
    query = ('''
        UPDATE Curso
        SET codigo_udp = %s,
            nombre = %s,
            descripcion = %s
        WHERE Curso.id = %s
    ''')
    cursor.execute(query, (
        val['codigo_udp'],
        val['nombre'],
        val['descripcion'],
        val['id']
        ))
    db.commit()
    return val

@mod.route('/gestion_cursos/editar_curso', methods = ['POST'])
def editar_curso_form():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")
    if request.method=='POST':
        val=request.form.to_dict()
        query = ('''
            UPDATE Curso
            SET Curso.codigo_udp = %s,
                Curso.nombre = %s,
                Curso.descripcion = %s
            WHERE Curso.id = %s
        ''')
        cursor.execute(query, (
            val['nuevo_codigo_udp'],
            val['nombre'],
            val['descripcion'],
            val['id']
            ))
        db.commit()
        flash("El curso se ha actualizado correctamente")
        #se redirige de vuelta a la pagina principal de gestion usuarios
        return redirect("/gestion_cursos")

def editar_curso_form2():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")
    if request.method == 'POST':
        valores = request.form.to_dict()
        editar_curso(valores)
        flash("El curso se ha actualizado correctamente")
        return redirect("/gestion_cursos")

@mod.route('/gestion_cursos/editar_seccion', methods = ['POST'])
def editar_seccion_form():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")
    if request.method=='POST':
        val=request.form.to_dict()
        query = ('''
            UPDATE Seccion
            SET Seccion.rut_profesor = %s,
                Seccion.codigo = %s
            WHERE Seccion.id = %s
        ''')
        cursor.execute(query, (
            val['rut_profesor'],
            val['codigo_seccion'],
            val['id']
            ))
        db.commit()
        curso = redirigir_detalle(val["id_curso"])
        flash("La sección se ha actualizado correctamente")
        return redirect('/gestion_cursos/detalles_curso/'+curso['codigo_udp'])

# == VISTA PRINCIPAL/MODAL "BORRAR CURSO" ==

def eliminar_curso(curso):
    query0 = ('''
        DELETE Seccion_alumno FROM Seccion_alumno, Seccion WHERE Seccion.id_curso = %s AND Seccion.id = Seccion_alumno.id_seccion
    ''')
    query1 = ('''
        DELETE Seccion FROM Seccion WHERE Seccion.id_curso = %s
    ''')
    query2 = ('''
        DELETE Curso FROM Curso WHERE Curso.id = %s
    ''')
    cursor.execute(query0,(curso['id'],))
    cursor.execute(query1,(curso['id'],))
    cursor.execute(query2,(curso['id'],))
    db.commit()
    return 'OK'

@mod.route("/gestion_cursos/eliminar_curso",methods=["POST"])
def eliminar_curso_form():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")
    if request.method == 'POST':
        curso_por_eliminar = request.form.to_dict()
        eliminar_curso(curso_por_eliminar)

        # Se eliminan la columna de id_curso_asociado para detalles de solicitudes
        # que estén asociados a algún curso
        sql_query = """
            UPDATE Detalle_solicitud
                SET id_curso_asociado = NULL
                    WHERE id_curso_asociado = %s
        """
        cursor.execute(sql_query,(curso_por_eliminar["id"],))

        flash("El curso fue eliminado correctamente")
        return redirect("/gestion_cursos")

def eliminar_seccion(seccion):
    query1 = ('''
        DELETE Seccion_alumno FROM Seccion_alumno WHERE Seccion_alumno.id_seccion = %s
    ''')

    query2 = ('''
        DELETE Seccion FROM Seccion WHERE Seccion.id = %s
    ''')
    cursor.execute(query1,(seccion['id'],))
    cursor.execute(query2,(seccion['id'],))
    db.commit()
    return 'OK'

@mod.route("/gestion_cursos/eliminar_seccion",methods=["POST"])
def eliminar_seccion_form():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")
    if request.method == 'POST':
        seccion_por_eliminar = request.form.to_dict()
        eliminar_seccion(seccion_por_eliminar)
        curso = redirigir_detalle(seccion_por_eliminar["id_curso"])
        flash("La sección se ha eliminado correctamente")
        return redirect('/gestion_cursos/detalles_curso/'+curso['codigo_udp'])
# == VISTA DETALLES CURSO ==
def consultar_curso_descripcion(codigo_curso):
    query = ('''
        SELECT *
        FROM Curso
        WHERE Curso.codigo_udp = %s
    ''')
    cursor.execute(query,(codigo_curso,))
    curso_detalle = cursor.fetchone()
    return curso_detalle
@mod.route("/gestion_cursos/detalles_curso/<string:codigo_udp>",methods=["GET"])
def detalle_info_curso(codigo_udp):
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3: # El usuario debe ser un administrador (Credencial = 3)
        return redirect("/")

    curso_desc = consultar_curso_descripcion(codigo_udp)
    return render_template("/gestion_cursos/detalles_curso.html", curso_desc=curso_desc)

# GESTION ALUMNOS Seccion
def obtener_seccion_id(codigo_udp,codigo_seccion):
    query = ('''
        SELECT Seccion.id FROM Seccion
        LEFT JOIN Curso ON Curso.id = Seccion.id_curso
        WHERE Curso.codigo_udp = %s AND Seccion.codigo = %s
    ''')
    cursor.execute(query,(codigo_udp,codigo_seccion,))
    seccion_id = cursor.fetchone()
    return seccion_id
def consultar_alumnos_seccion(id_seccion):
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")
    query = ('''
        SELECT
            Seccion_alumno.rut_alumno AS rut_alumno,
            Usuario.nombres AS nombres_alumno,
            Usuario.apellidos AS apellidos_alumno
            FROM Seccion_alumno
            LEFT JOIN Usuario ON Usuario.rut = Seccion_alumno.rut_alumno
            WHERE Seccion_alumno.id_seccion = %s
    ''')
    cursor.execute(query,(id_seccion,))
    alumnos = cursor.fetchall()
    return alumnos

@mod.route("/gestion_cursos/detalles_curso/<string:codigo_udp>/<string:codigo_seccion>",methods=["GET"])
def alumnos_seccion(codigo_udp,codigo_seccion):
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3: # El usuario debe ser un administrador (Credencial = 3)
        return redirect("/")

    seccion_id = obtener_seccion_id(codigo_udp,codigo_seccion)
    alumnos_seccion = consultar_alumnos_seccion(seccion_id['id'])
    todos_los_alumnos = consultar_alumnos(seccion_id['id'])
    curso = consultar_curso_descripcion(codigo_udp)
    return render_template("gestion_cursos/detalles_seccion.html",seccion_id=seccion_id,alumnos=alumnos_seccion,lista_alumnos=todos_los_alumnos,curso=curso)

def consultar_alumnos(id_seccion):
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")
    query = ('''
        SELECT *
            FROM Usuario
            WHERE Usuario.id_credencial = 1 AND Usuario.activo = 1
            AND Usuario.rut NOT IN (SELECT Seccion_alumno.rut_alumno FROM Seccion_alumno WHERE Seccion_alumno.id_seccion=%s)
    ''')
    cursor.execute(query,(id_seccion,))
    alumnos = cursor.fetchall()
    return alumnos

def agregar_alumno(val):
    query = ('''
    INSERT INTO Seccion_alumno (id_seccion, rut_alumno)
    VALUES (%s,%s);
    ''')
    cursor.execute(query, (val['id'],val['rut_alumno']))
    db.commit()
    return 'OK'

@mod.route("/gestion_cursos/agregar_alumno", methods = ['POST'])
def agregar_alumno_form():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")
    if request.method == 'POST':
        valores = request.form.to_dict()
        agregar_alumno(valores)
        seccion = obtener_seccion(valores['id'])
        curso = obtener_curso(seccion['id_curso'])
        flash("El alumno se ha agregado correctamente")
        return redirect('/gestion_cursos/detalles_curso/'+curso['codigo_udp']+'/'+str(seccion['codigo']))

def obtener_seccion(id):
    query = ('''
        SELECT * FROM Seccion
        WHERE Seccion.id = %s
    ''')
    cursor.execute(query,(id,))
    seccion = cursor.fetchone()
    return seccion
def obtener_curso(id):
    query = ('''
        SELECT * FROM Curso
        WHERE Curso.id = %s
    ''')
    cursor.execute(query,(id,))
    curso = cursor.fetchone()
    return curso
@mod.route('/gestion_cursos/editar_alumno', methods = ['POST'])
def editar_alumno_form():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")
    if request.method=='POST':
        val=request.form.to_dict()
        query = ('''
            UPDATE Seccion_alumno
            SET Seccion_alumno.rut_alumno = %s
            WHERE Seccion_alumno.id_seccion = %s AND Seccion_alumno.rut_alumno = %s
        ''')
        cursor.execute(query, (
            val['rut_alumno'],
            val['id'],
            val['rut_original']
            ))
        db.commit()
        seccion = obtener_seccion(val['id'])
        curso = obtener_curso(seccion['id_curso'])
        flash("El alumno se ha actualizado correctamente")
        return redirect('/gestion_cursos/detalles_curso/'+curso['codigo_udp']+'/'+str(seccion['codigo']))

def eliminar_alumno(alumno):
    query = ('''
        DELETE Seccion_alumno FROM Seccion_alumno WHERE Seccion_alumno.rut_alumno = %s
    ''')
    cursor.execute(query,(alumno['rut_alumno'],))
    db.commit()
    return 'OK'

@mod.route("/gestion_cursos/eliminar_alumno",methods=["POST"])
def eliminar_alumno_form():
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3:
        return redirect("/")
    if request.method == 'POST':
        val = request.form.to_dict()
        eliminar_alumno(val)
        seccion = obtener_seccion(val['id'])
        curso = obtener_curso(seccion['id_curso'])
        flash("El alumno se ha eliminado correctamente")
        return redirect('/gestion_cursos/detalles_curso/'+curso['codigo_udp']+'/'+str(seccion['codigo']))