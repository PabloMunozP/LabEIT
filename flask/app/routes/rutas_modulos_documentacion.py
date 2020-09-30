from jinja2 import Environment
from datetime import datetime,timedelta
from werkzeug.utils import secure_filename
import os,time,bcrypt,random,timeago,shutil
from config import db,cursor,BASE_DIR,ALLOWED_EXTENSIONS,MAX_CONTENT_LENGTH
from flask import Flask,Blueprint,render_template,request,redirect,url_for,flash,session,jsonify,send_file

mod = Blueprint("rutas_modulos_documentacion",__name__)

def redirect_url(default='index'): # Redireccionamiento desde donde vino la request
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

# Reglamento LabEIT
@mod.route("/reglamento_interno_labeit",methods=["GET"])
def descargar_reglamento_interno():
    if "usuario" not in session.keys():
        return redirect("/")

    ruta_reglamento_labeit = os.path.normpath(os.path.join(BASE_DIR,"app/static/files/reglamentos/reglamento_labeit.pdf"))
    return send_file(ruta_reglamento_labeit,as_attachment=True)

# =============== Sistema de archivos (documentación) para softwares académicos ==============
@mod.route("/documentacion_softwares",methods=["GET"])
def documentacion_softwares():
    # Se muestra la lista con tutoriales/guías de softwares
    if "usuario" not in session.keys():
        return redirect("/")
    
    # Se verifica el tipo de cuenta del usuario
    # Si es administrador, puede ver módulos ocultos y también los visibles
    # En caso contrario, se muestran solo los módulos visibles

    if session["usuario"]["id_credencial"] == 3:
        # Se obtiene la lista de módulos
        sql_query = """
            SELECT * FROM Modulo
                ORDER BY fecha_registro DESC
        """
    else:
        # Se obtiene la lista de módulos
        sql_query = """
            SELECT * FROM Modulo
                WHERE visible = 1
                ORDER BY fecha_registro DESC
        """

    cursor.execute(sql_query)
    lista_modulos = cursor.fetchall()

    # Se obtienen los archivos registrados para cada módulo
    lista_archivos = {} # Se almacenan los archivos, donde la key es el ID del módulo
    for modulo in lista_modulos:
        sql_query = """
            SELECT *
                FROM Documentacion_software
                    WHERE id_modulo = %s
        """
        cursor.execute(sql_query,(modulo["id"],))
        lista_archivos[modulo["id"]] = cursor.fetchall()
    
    return render_template("/vistas_softwares/documentacion_softwares.html",
        lista_modulos=lista_modulos,
        lista_archivos=lista_archivos)

@mod.route("/registrar_modulo",methods=["POST"])
def registrar_modulo():
    datos_formulario = request.form.to_dict()
    datos_formulario["descripcion"] = datos_formulario["descripcion"].strip()
    fecha_actual = datetime.now().replace(microsecond=0)

    # Se registra el módulo en la base de datos
    sql_query = """
        INSERT INTO Modulo (titulo,descripcion,visible,fecha_registro)
            VALUES (%s,%s,%s,%s)
    """
    cursor.execute(sql_query,(datos_formulario["titulo"],datos_formulario["descripcion"],datos_formulario["visible"],fecha_actual))
    id_modulo = cursor.lastrowid

    # Se crea la sub-carpeta en la carpeta de documentación
    nombre_carpeta = "M"+str(id_modulo)
    ruta_carpeta = os.path.normpath(os.path.join(os.getcwd(),"app/static/files/documentacion_softwares/"+nombre_carpeta))

    # Se verifica que la carpeta no exista
    if not os.path.exists(ruta_carpeta):
        # Si no existe, se crea la nueva carpeta para archivos del módulo
        os.makedirs(ruta_carpeta)
        flash("carpeta-registrada")

        # Se actualiza el nombre de la carpeta en el registro del módulo
        # en la base de datos
        sql_query = """
            UPDATE Modulo
                SET nombre_carpeta = %s
                    WHERE id = %s
        """
        cursor.execute(sql_query,(nombre_carpeta,id_modulo))

    flash("modulo-agregado")
    return redirect(redirect_url())

@mod.route("/eliminar_modulo/<string:id_modulo>",methods=["POST"])
def eliminar_modulo(id_modulo):
    # Se obtiene el nombre de la carpeta correspondiente al módulo
    sql_query = """
        SELECT nombre_carpeta
            FROM Modulo
                WHERE id = %s
    """
    cursor.execute(sql_query,(id_modulo,))
    data_modulo = cursor.fetchone()

    if data_modulo is None:
        # Si el registro se eliminó inesperadamente, se retorna a la lista.
        flash("error-inesperado")
        return redirect(redirect_url())
    
    # Se construye la ruta según el nombre de la carpeta
    ruta_carpeta_modulo = os.path.normpath(os.path.join(os.getcwd(),"app/static/files/documentacion_softwares/"+data_modulo["nombre_carpeta"]))

    # Se verifica si la carpeta existe
    if os.path.exists(ruta_carpeta_modulo):
        # En caso de que exista la carpeta, se elimina recursivamente el directorio
        # y los archivos registrados al interior
        shutil.rmtree(ruta_carpeta_modulo)
        
    # Se elimina el módulo y los archivos que tenga asociados
    sql_query = """
        DELETE FROM Modulo
            WHERE id = %s
    """
    cursor.execute(sql_query,(id_modulo,))

    sql_query = """
        DELETE FROM Documentacion_software
            WHERE id_modulo = %s
    """
    cursor.execute(sql_query,(id_modulo,))

    flash("modulo-eliminado")
    return redirect(redirect_url())

@mod.route("/modificar_modulo/<string:id_modulo>",methods=["POST"])
def modificar_modulo(id_modulo):
    datos_form = request.form.to_dict()

    # Se realizan las modificaciones en la base de datos
    sql_query = """
        UPDATE Modulo
            SET titulo=%s,descripcion=%s,visible=%s
                WHERE id = %s
    """
    cursor.execute(sql_query,(datos_form["titulo"],datos_form["descripcion"],datos_form["visible"],id_modulo))

    flash("modulo-modificado")
    return redirect(redirect_url())

@mod.route("/subir_documentacion_software/<string:id_modulo>",methods=["POST"])
def subir_documentacion_software(id_modulo):

    def get_size(fobj): # Permite obtener el tamaño de un archivo
        if fobj.content_length:
            return fobj.content_length
        try:
            pos = fobj.tell()
            fobj.seek(0, 2)  #seek to end
            size = fobj.tell()
            fobj.seek(pos)  # back to original position
            return size
        except (AttributeError, IOError):
            pass

        # in-memory file object that doesn't support seeking or tell
        return 0  #assume small enough

    def allowed_file(filename): # Función para determinar si la extensión del archivo corresponde a una que esté permitida.
        return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    # Se obtiene el archivo de la request
    archivo = request.files["archivo"]

    # Si se envía un archivo sin el nombre
    if archivo.filename == "":
        flash("archivo-sin-nombre")
        return redirect(redirect_url())
    
    if archivo and allowed_file(archivo.filename):
        nombre_archivo = secure_filename(archivo.filename)

        # Se comprueba si el tamaño cumple con el tamaño máximo (25mb)
        if get_size(archivo) > 1024*1024*25:
            flash("error-max-size")
            return redirect(redirect_url())
    
        # Se verifica si el archivo ya se encuentra registrado en la base de datos.
        # En caso de que se encuentre registrado, se reemplazará automáticamente en la carpeta el archivo
        # y se debe omitir la inserción en la base de datos
        archivo_existente_bd = False

        sql_query = """
            SELECT id
                FROM Documentacion_software
                    WHERE nombre = %s
                    AND id_modulo = %s
        """
        cursor.execute(sql_query,(nombre_archivo,id_modulo))
        registro_archivo = cursor.fetchone()

        if registro_archivo is not None:
            # Si existe (se está sobrescribiendo)
            # se omite la inserción en la base de datos
            archivo_existente_bd = True

        # Se obtiene el nombre de la carpeta correspondiente al módulo
        sql_query = """
            SELECT nombre_carpeta
                FROM Modulo
                    WHERE id = %s
        """
        cursor.execute(sql_query,(id_modulo,))
        data_modulo = cursor.fetchone()

        if data_modulo is None:
            # Si el registro se eliminó inesperadamente, se retorna a la lista.
            flash("error-inesperado")
            return redirect(redirect_url())

        # Se obtiene la carpeta donde se encuentra registrada la documentación
        ruta_carpeta_documentos = os.path.normpath(os.path.join(os.getcwd(),"app/static/files/documentacion_softwares/"+data_modulo["nombre_carpeta"]))
        # Se guarda el archivo
        archivo.save(os.path.normpath(os.path.join(ruta_carpeta_documentos, nombre_archivo)))

        # Se agrega el registro a la base de datos sólo si no se está sobrescribiendo
        if not archivo_existente_bd:
            fecha_registro = datetime.now().replace(microsecond=0)
            sql_query = """
                INSERT INTO Documentacion_software (nombre,fecha_registro,id_modulo)
                    VALUES (%s,%s,%s)
            """
            cursor.execute(sql_query,(nombre_archivo,fecha_registro,id_modulo))
            flash("archivo-agregado")
        else:
            flash("archivo-sobrescrito")
    else:
        flash("extension-no-valida")

    return redirect(redirect_url())

@mod.route("/eliminar_archivo/<string:id_archivo>",methods=["GET"])
def eliminar_archivo(id_archivo):
    if "usuario" not in session.keys():
        return redirect("/")
    if session["usuario"]["id_credencial"] != 3: # El usuario debe ser un administrador (Credencial = 3)
        return redirect("/")

    # Se obtiene la ruta del archivo y módulo
    sql_query = """
        SELECT Documentacion_software.nombre AS nombre_archivo,Documentacion_software.id_modulo,
               Modulo.nombre_carpeta
                FROM Documentacion_software,Modulo
                    WHERE Documentacion_software.id = %s
                    AND Documentacion_software.id_modulo = Modulo.id
    """
    cursor.execute(sql_query,(id_archivo,))
    data_modulo_archivo = cursor.fetchone()

    if data_modulo_archivo is None:
        # Si el registro se eliminó inesperadamente, se retorna a la lista.
        flash("error-inesperado")
        return redirect(redirect_url())
    
    # Se construye la ruta hacia el archivo
    ruta_archivo = os.path.normpath(os.path.join(os.getcwd(),"app/static/files/documentacion_softwares/"+data_modulo_archivo["nombre_carpeta"]+"/"+data_modulo_archivo["nombre_archivo"]))

    # Se verifica si existe el archivo en la carpeta
    if os.path.exists(ruta_archivo):
        # En caso de que exista, se elimina el archivo de la carpeta
        os.remove(ruta_archivo)

        # Se remueve el registro en la base de datos
        sql_query = """
            DELETE FROM Documentacion_software
                WHERE id = %s
        """
        cursor.execute(sql_query,(id_archivo,))
    
    flash("archivo-eliminado")
    return redirect(redirect_url())

@mod.route("/descargar_archivo_documentacion/<string:id_archivo>",methods=["GET"])
def descargar_archivo_modulo(id_archivo):
    if "usuario" not in session.keys():
        return redirect("/")

    # Se obtiene el registro del módulo y el archivo
    sql_query = """
        SELECT Documentacion_software.nombre AS nombre_archivo,Modulo.nombre_carpeta
            FROM Documentacion_software,Modulo
                WHERE Documentacion_software.id_modulo = Modulo.id
                AND Documentacion_software.id = %s
    """
    cursor.execute(sql_query,(id_archivo,))
    datos_modulo = cursor.fetchone()

    if datos_modulo is None:
            # Si el registro se eliminó inesperadamente, se retorna a la lista.
            flash("error-inesperado")
            return redirect(redirect_url())
    
    # Se arma la ruta hacia el archivo
    ruta_archivo = os.path.normpath(os.path.join(os.getcwd(),"app/static/files/documentacion_softwares/"+datos_modulo["nombre_carpeta"]+"/"+datos_modulo["nombre_archivo"]))

    # Se verifica que el archivo exista, verificando la ruta
    if not os.path.exists(ruta_archivo):
        flash("error-inesperado")
        return redirect(redirect_url())
    
    # Se envía el archivo
    return send_file(ruta_archivo,as_attachment=True)

@mod.route("/eliminar_archivos_modulo/<string:id_modulo>",methods=["POST"])
def eliminar_archivos_modulo(id_modulo):
    # Se eliminan todos los archivos al interior de la carpeta correspondiente al módulo

    # Se obtiene el nombre de carpeta del módulo
    sql_query = """
        SELECT nombre_carpeta
            FROM Modulo
                WHERE id = %s
    """
    cursor.execute(sql_query,(id_modulo,))
    data_modulo = cursor.fetchone()

    if data_modulo is None:
        # Si el registro se eliminó inesperadamente, se retorna a la lista.
        flash("error-inesperado")
        return redirect(redirect_url())

    # Se obtiene la lista de nombres de archivos registrados en el módulo
    sql_query = """
        SELECT nombre
            FROM Documentacion_software
                WHERE id_modulo = %s
    """
    cursor.execute(sql_query,(id_modulo,))
    lista_nombres_archivos = cursor.fetchall()

    # Se elimina cada uno de los archivos si existen en la carpeta
    for archivo in lista_nombres_archivos:
        # Se construye la ruta de la carpeta del módulo
        ruta_carpeta_modulo = os.path.normpath(os.path.join(os.getcwd(),"app/static/files/documentacion_softwares/"+data_modulo["nombre_carpeta"]))

        # Se construye la ruta del archivo a partir de la ruta del módulo    
        ruta_archivo = os.path.normpath(os.path.join(ruta_carpeta_modulo,archivo["nombre"]))

        # Si la ruta existe, entonces se elimina el archivo
        if os.path.exists(ruta_archivo):
            os.remove(ruta_archivo)
    
    # Se eliminan los archivos registrados en la base de datos
    sql_query = """
        DELETE FROM Documentacion_software
            WHERE id_modulo = %s
    """
    cursor.execute(sql_query,(id_modulo,))

    flash("archivos-modulo-eliminados")
    return redirect(redirect_url())

@mod.route("/documentacion_softwares/visualizar_documento/<string:id_archivo>",methods=["GET"])
def visualizar_documento(id_archivo):
    if "usuario" not in session.keys():
        return redirect("/")
        
    # Se obtienen los datos del archivo
    sql_query = """
        SELECT Documentacion_software.*,Modulo.nombre_carpeta
             FROM Documentacion_software,Modulo
                WHERE Documentacion_software.id = %s
                AND Modulo.id = Documentacion_software.id_modulo
    """
    cursor.execute(sql_query,(id_archivo,))
    datos_archivo = cursor.fetchone()

    if datos_archivo is None:
        # Si el registro se eliminó inesperadamente, se retorna a la lista.
        flash("error-inesperado")
        return redirect(redirect_url())
    
    # Se obtiene la extensión del archivo
    datos_archivo["extension"] = os.path.splitext(datos_archivo["nombre"])[1]

    return render_template("/vistas_softwares/visualizacion_documento.html",
        datos_archivo=datos_archivo)

