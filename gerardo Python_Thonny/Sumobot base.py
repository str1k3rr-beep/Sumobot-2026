# Tomás de Camino Beck / Mod: Evasión Direccional Corregida y Nueva Distribución
# Escuela de Sistemas Inteligentes - Universidad Cenfotec

import board
import keypad
from ideaboard import IdeaBoard
from time import sleep

ib = IdeaBoard()

keys = keypad.Keys((board.IO0,), value_when_pressed=False, pull=True)

# Tu nueva distribución conceptual:
sen1 = ib.AnalogIn(board.IO36) # Frontal / Lateral Izquierdo (Índice 0)
sen2 = ib.AnalogIn(board.IO39) # Frontal / Lateral Derecho   (Índice 1)
sen3 = ib.AnalogIn(board.IO34) # Apoyo Izquierdo             (Índice 2)
sen4 = ib.AnalogIn(board.IO35) # Apoyo Derecho               (Índice 3)

infrarrojos = [sen1, sen2, sen3, sen4]
umbrales = [0, 0, 0, 0]


def esperar_boton_y_leer(color_led):
    ib.pixel = color_led
    while True:
        event = keys.events.get()
        if event and event.released:
            lecturas = [sen.value for sen in infrarrojos]
            ib.pixel = (0, 0, 0)
            sleep(0.5)
            return lecturas


def calibracion_por_pasos():
    print("PASO 1: Sensores sobre NEGRO y presiona BOOT.")
    valores_negro = esperar_boton_y_leer((255, 0, 0))

    print("PASO 2: Sensores sobre BLANCO y presiona BOOT.")
    valores_blanco = esperar_boton_y_leer((255, 255, 255))

    for i in range(4):
        umbrales[i] = (valores_negro[i] + valores_blanco[i]) // 2

    print("¡CALIBRACIÓN EXITOSA! Presiona BOOT para combate.")
    esperar_boton_y_leer((0, 255, 0))
    
    print("Iniciando cuenta regresiva de 2 segundos...")
    for i in range(2, 0, -1):
        ib.pixel = (255, 255, 0)
        sleep(0.5)
        ib.pixel = (0, 0, 0)
        sleep(0.5)


def leer_borde():
    """Evalúa la nueva distribución de sensores solicitada."""
    detectados = [False, False, False, False]
    
    for i, sen in enumerate(infrarrojos):
        if sen.value < umbrales[i]:
            sleep(0.005) 
            if sen.value < umbrales[i]:
                detectados[i] = True

    # 1. Peligro Frontal: Se activan sen1 (0) Y sen2 (1) a la vez
    if detectados[0] and detectados[1]:
        return "FRENTE"
    # 2. Lado Izquierdo: Se activa sen1 (0) O sen3 (2)
    elif detectados[0] or detectados[2]:
        return "IZQUIERDA"
    # 3. Lado Derecho: Se activa sen2 (1) O sen4 (3)
    elif detectados[1] or detectados[3]:
        return "DERECHA"
        
    return None 


def maniobra_escape(direccion):
    """Giros corregidos de forma independiente."""
    ib.pixel = (255, 0, 255)  
    
    # Freno y retroceso común
    ib.motor_1.throttle = 0
    ib.motor_2.throttle = 0
    sleep(0.10)
    ib.motor_1.throttle = 1.0
    ib.motor_2.throttle = -1.0
    sleep(0.10)
    ib.motor_1.throttle = 0
    ib.motor_2.throttle = 0
    sleep(0.10)
    
    # Giros dinámicos
    if direccion == "FRENTE":
        # Giro 180° hacia la derecha
        ib.motor_1.throttle = -1.0
        ib.motor_2.throttle = 1.0
        sleep(1) 
        
    elif direccion == "IZQUIERDA":
        # Peligro a la izquierda -> Gira a la DERECHA
        # M1 (Izq) adelante, M2 (Der) atrás
        ib.motor_1.throttle = 1.0
        ib.motor_2.throttle = 1.0
        sleep(0.5) 
        
    elif direccion == "DERECHA":
        # Peligro a la derecha -> Gira a la IZQUIERDA
        # M1 (Izq) atrás, M2 (Der) adelante
        ib.motor_1.throttle = -1.0
        ib.motor_2.throttle = -1.0
        sleep(0.5) 

    # Freno estabilizador
    ib.motor_1.throttle = 0
    ib.motor_2.throttle = 0
    sleep(0.005)


###### EJECUCIÓN PRINCIPAL #######
ib.motor_1.throttle = 0
ib.motor_2.throttle = 0

calibracion_por_pasos()

while True:
    direccion_impacto = leer_borde()
    
    if direccion_impacto is not None:
        maniobra_escape(direccion_impacto)
    else:
        # Ataque frontal
        ib.pixel = (0, 255, 255)
        ib.motor_1.throttle = -1.0
        ib.motor_2.throttle = -1.0