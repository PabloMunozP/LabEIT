import os
from app import db_wrapper

SEND_FILE_MAX_AGE_DEFAULT = 0
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500mb máximos de largo de contenido

# Statement for enabling the development environment
DEBUG = True

# Define the application directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# ----------------------- Conexión a base de datos MySQL ------------------------------------------------------------
# ---- FreeMySQLHosting:
# user="sql10342433", passwd="fCQ6jJWFUY", host="sql10.freemysqlhosting.net",
# port="3306", database="sql10342433", autocommit=True
# ---- LabEIT Host:
# user="root", passwd="@ProdLabEIT2020", host="localhost", port="3306",
# database="LabEITDB", autocommit=True

# Conexión a la base de datos mediante wrapper class
db = db_wrapper.DB(user="root",
                   passwd="@ProdLabEIT2020",
                   host="localhost",
                   port="3306",
                   database="LabEITDB",
                   autocommit=True)

# -----------------------------------------------------------------------------

# Configuraciones de archivos
UPLOAD_FOLDER = 'static/upload_folder'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif',
                      'xlsx', 'xls', 'csv', 'doc', 'docx', 'ppt',
                      'pptx', 'odp', 'svg'}

# Application threads. A common general assumption is
# using 2 per available processor cores - to handle
# incoming requests using one and performing background
# operations using the other.
THREADS_PER_PAGE = 2

# Enable protection agains *Cross-site Request Forgery (CSRF)*
CSRF_ENABLED = True

# Use a secure, unique and absolutely secret key for
# signing the data.
CSRF_SESSION_KEY = os.urandom(24)

# Secret key for signing cookies
SECRET_KEY = b'6hc/_gsh,./;2ZZx3c6_s,1//'
