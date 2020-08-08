from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import os
import time
from multiprocessing import Lock, Process
from threading import Thread

import queue
ABSOLUTE_PATH = os.path.dirname(os.path.abspath(__file__)) # obtiene la direccion absuluta
CHROMEDRIVE_PATH = os.path.join(ABSOLUTE_PATH, "chromedriver.exe") # Le da direccion al ejecutable
SESSION_PATH = os.path.join(ABSOLUTE_PATH, "session\\")
WSP_WEB_MSG_DIR_CHILE = "https://web.whatsapp.com/send?phone=56" # "https://web.whatsapp.com/send?phone=numero_de_telefono"
TEXT_MESSAGE = "Esto es un mensaje de prueba" # borrar?

CHROME_BROWSER = None
#  https://wa.me/56977540310
# https://web.whatsapp.com/send?phone=56977540310


MENSAJES_USUARIOS = queue.Queue() # cola que se sencarga de administrar mensajes para que no colapse wsp web
LOCK = Lock() # Lock para sincronizar




def añadir_mensaje_a_la_cola(numero_telefono = None, mensaje = None):
    global MENSAJES_USUARIOS, LOCK
    # LOCK.acquire()
    if MENSAJES_USUARIOS.empty(): # si la cola esta vacia, este la inicia

        MENSAJES_USUARIOS.put((numero_telefono,numero_telefono)) # agrega el mensaje a la cola como una tupla
        WSP_PROCESS = Thread(target = wsp_bot_process, args = (MENSAJES_USUARIOS,)) # thread encargado del proceso de enviar mensajes
        WSP_PROCESS.start()
    else:
        MENSAJES_USUARIOS.put((numero_telefono,mensaje)) # agrega el mensaje a la cola
    # time.sleep(10)
    # LOCK.release()


def wsp_bot_process(COLA_MENSAJES):
    print("thread iniciado!!!")
    print(list(COLA_MENSAJES.queue))
    time.sleep(10)
    print(list(COLA_MENSAJES.queue))
    print(COLA_MENSAJES.get()) # get elimina y retorna el primer elemento
    print(list(COLA_MENSAJES.queue))
    return
    

def init_wsp_web():
    global CHROME_BROWSER
    CHROME_BROWSER = webdriver.Chrome(CHROMEDRIVE_PATH) # ejecuta chromedriver.exe
    # CHROME_BROWSER.set_page_load_timeout(1)
    # print("pagina ready")
    CHROME_BROWSER.get("https://web.whatsapp.com/")
    print("Para ingresar use el código QR")
    
def enviar_mensaje_a_usuario(user_phone = None, mensaje = None):  # Debe ingresar un numero de 9 dígitos
    
    global CHROME_BROWSER
    inp_xpath = '//div[@class="_3FRCZ copyable-text selectable-text"][@contenteditable="true"][@data-tab="1"]' # Clase del input text
    CHROME_BROWSER.get(WSP_WEB_MSG_DIR_CHILE + user_phone) # abre la pagina
    try:
        WebDriverWait(CHROME_BROWSER, 30).until(EC.visibility_of_element_located((By.XPATH, inp_xpath))) # espera hasta que se encuentre el input
        input_box = CHROME_BROWSER.find_element_by_xpath(inp_xpath) # selecciona la casilla de mensaje para enviar
        time.sleep(2) # un pequeño retraso para el input
        input_box.send_keys(TEXT_MESSAGE + Keys.ENTER)
        print("Page loaded")
    except:
        # posibles errores, Whatsapp a cambiado lo algo del HTML
        # O el numero no es valido
        print("Whatsapp web se ha demorado mucho tiempo en iniciar")
        print("por favor revisar el servidor")


def quite_wsp_web():
    global CHROME_BROWSER
    CHROME_BROWSER.quit()