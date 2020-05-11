# Statement for enabling the development environment
DEBUG = True

# Define the application directory
import os,mysql.connector
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# ----------------------- Conexión a base de datos MySQL ------------------------------------------------------------
#db = mysql.connector.connect(user="...",passwd="...",host="...",port="...",database="...",autocommit=True)
#cursor = db.cursor(dictionary=True,buffered=True)
#cursor.execute("SET NAMES utf8mb4;")

# -----------------------------------------------------------------------

# Configuraciones de archivos
UPLOAD_FOLDER = 'static/upload_folder'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'xlsx', 'xls'}

# Application threads. A common general assumption is
# using 2 per available processor cores - to handle
# incoming requests using one and performing background
# operations using the other.
THREADS_PER_PAGE = 2

# Enable protection agains *Cross-site Request Forgery (CSRF)*
CSRF_ENABLED     = True

# Use a secure, unique and absolutely secret key for
# signing the data.
CSRF_SESSION_KEY = os.urandom(24)

# Secret key for signing cookies
SECRET_KEY = os.urandom(24)
