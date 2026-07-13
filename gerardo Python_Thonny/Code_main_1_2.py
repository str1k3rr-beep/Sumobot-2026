import board
import keypad
from ideaboard import IdeaBoard
from time import sleep
import time
import digitalio
import random

ib = IdeaBoard()
sleep(1.0)                                           

keys = keypad.Keys((board.IO0,), value_when_pressed=False, pull=True)

sen1 = ib.AnalogIn(board.IO36)                                         
sen2 = ib.AnalogIn(board.IO39)                                         
sen3 = ib.AnalogIn(board.IO34)                                         
sen4 = ib.AnalogIn(board.IO35)                                         

infrarrojos = [sen1, sen2, sen3, sen4]
umbrales = [0, 0, 0, 0]

trigger = digitalio.DigitalInOut(board.IO25)
trigger.direction = digitalio.Direction.OUTPUT
trigger.value = False

echo = digitalio.DigitalInOut(board.IO26)
echo.direction = digitalio.Direction.INPUT

DISTANCIA_RIVAL_CM = 50

COLORES_RONDA = {
    1: (255, 100, 0),
    2: (0, 255, 100),
    3: (0, 100, 255),
}

_direccion_giro_busqueda = 1
_tiempo_ultimo_cambio = 0
_barridos_sin_rival = 0
_rival_perdido_count = 0
_tiempo_inicio_borde = None                                  

MAX_PERDIDO = 3
INTERVALO_CAMBIO_GIRO = 0.15

_m1 = ib.motor_1
_m2 = ib.motor_2

def medir_distancia_cm():
    trigger.value = True
    time.sleep(0.00001)
    trigger.value = False

    start = time.monotonic()
    while not echo.value:
        if time.monotonic() - start > 0.006:
            return 999

    t_inicio = time.monotonic()
    while echo.value:
        if time.monotonic() - t_inicio > 0.004:
            return 999
        if time.monotonic() - start > 0.05:
            return 999

    t_fin = time.monotonic()
    return (t_fin - t_inicio) * 34300 / 2

def rival_detectado():
    return medir_distancia_cm() < DISTANCIA_RIVAL_CM

def boton_presionado():
    event = keys.events.get()
    return bool(event and event.released)

def arrancar_motores(m1, m2):
    _m1.throttle = -m1
    _m2.throttle = -m2

def frenar():
    _m1.throttle = 0
    _m2.throttle = 0

def esperar_boton_y_leer(color_led):
    ib.pixel = color_led
    while True:
        event = keys.events.get()
        if event and event.released:
            lecturas = [sen.value for sen in infrarrojos]
            ib.pixel = (0, 0, 0)
            return lecturas

def calibracion_por_pasos():
    UMBRAL_FIJO = 4000
    for i in range(4):
        umbrales[i] = UMBRAL_FIJO
    print(f"Umbrales fijos establecidos: {umbrales}")

    print("¡CALIBRACIÓN LISTA! Presiona BOOT para combate.")
    esperar_boton_y_leer((0, 255, 0))

    print("Iniciando...")

def _leer_sensores():
    return [sen.value < umbrales[i] for i, sen in enumerate(infrarrojos)]

def leer_borde_mejorado():
    detectados = _leer_sensores()
                                                                              
    if not any(detectados):
        return None
                                                                          
    detectados2 = _leer_sensores()
                                                              
    detectados = [detectados[i] and detectados2[i] for i in range(4)]
    if not any(detectados):
        return None
                                                                                        
    if detectados[1] and detectados[3] and not detectados[0] and not detectados[2]:
        return "EMPUJE_IZQUIERDA"

    if detectados[0] and detectados[2] and not detectados[1] and not detectados[3]:
        return "EMPUJE_DERECHA"

    if detectados[0] and detectados[1]:
        return "FRENTE"
    elif detectados[0] and detectados[2]:
        return "IZQUIERDA"
    elif detectados[0] and not detectados[2]:
        return "FRENTE_IZQ"
    elif detectados[1] or detectados[3]:
        return "DERECHA"
    elif detectados[2]:
        return "IZQUIERDA"

    return None

def maniobra_escape(direccion):
    global _tiempo_inicio_borde
    ib.pixel = (255, 0, 255)

    if direccion == "EMPUJE_IZQUIERDA":
                                                                               
        ib.pixel = (0, 255, 255)
                                                 
        arrancar_motores(1.0, 1.0)
        start = time.monotonic()
        while time.monotonic() - start < 0.35:
            if boton_presionado(): return True
                                                     
        arrancar_motores(-1.0, 1.0)
        start = time.monotonic()
        while time.monotonic() - start < 0.35:
            if boton_presionado(): return True
                                  
        arrancar_motores(1.0, 1.0)
        start = time.monotonic()
        while time.monotonic() - start < 0.3:
            if boton_presionado(): return True
        _tiempo_inicio_borde = None
        frenar()
        return False

    if direccion == "EMPUJE_DERECHA":
                                                                                 
        ib.pixel = (0, 255, 255)
                                                 
        arrancar_motores(1.0, 1.0)
        start = time.monotonic()
        while time.monotonic() - start < 0.35:
            if boton_presionado(): return True
                                                       
        arrancar_motores(1.0, -1.0)
        start = time.monotonic()
        while time.monotonic() - start < 0.35:
            if boton_presionado(): return True
                                  
        arrancar_motores(1.0, 1.0)
        start = time.monotonic()
        while time.monotonic() - start < 0.3:
            if boton_presionado(): return True
        _tiempo_inicio_borde = None
        frenar()
        return False

    ahora = time.monotonic()

    if _tiempo_inicio_borde is None:
        _tiempo_inicio_borde = ahora

    tiempo_en_borde = ahora - _tiempo_inicio_borde

    if tiempo_en_borde > 0.4 and not rival_detectado():

        if direccion == "IZQUIERDA":
            ib.pixel = (0, 255, 255)                                   
                                                          
            arrancar_motores(1.0, -1.0)
            start = time.monotonic()
            while time.monotonic() - start < 0.3:
                if boton_presionado(): return True
                if leer_borde_mejorado() is None: break
                              
            arrancar_motores(1.0, 1.0)
            start = time.monotonic()
            while time.monotonic() - start < 0.25:
                if boton_presionado(): return True
                if leer_borde_mejorado() is not None: break

        elif direccion == "DERECHA":
            ib.pixel = (0, 255, 255)                                 
                                                            
            arrancar_motores(-1.0, 1.0)
            start = time.monotonic()
            while time.monotonic() - start < 0.3:
                if boton_presionado(): return True
                if leer_borde_mejorado() is None: break
                              
            arrancar_motores(1.0, 1.0)
            start = time.monotonic()
            while time.monotonic() - start < 0.25:
                if boton_presionado(): return True
                if leer_borde_mejorado() is not None: break
                
        else:
            ib.pixel = (255, 255, 0)                                 
            lado = random.choice([1, -1])
            arrancar_motores(1.0 * lado, -1.0 * lado)
            start = time.monotonic()
            while time.monotonic() - start < 0.35:
                if boton_presionado(): return True
                if leer_borde_mejorado() is None: break
            arrancar_motores(1.0, 1.0)
            start = time.monotonic()
            while time.monotonic() - start < 0.2:
                if boton_presionado(): return True
                if leer_borde_mejorado() is not None: break

        _tiempo_inicio_borde = None
        frenar()
        return False

    arrancar_motores(1.0, -1.0)
    start = time.monotonic()
    while time.monotonic() - start < 0.15:
        if boton_presionado(): return True
        if leer_borde_mejorado() is not None: break

    frenar()

    if direccion in ("FRENTE", "FRENTE_IZQ"):
        arrancar_motores(1.0, -1.0)
        start = time.monotonic()
        while time.monotonic() - start < 0.45:
            if boton_presionado(): return True
            if leer_borde_mejorado() is not None: break

    elif direccion == "IZQUIERDA":
        arrancar_motores(-1.0, 1.0)
        start = time.monotonic()
        while time.monotonic() - start < 0.3:
            if boton_presionado(): return True
            if leer_borde_mejorado() is not None: break

    elif direccion == "DERECHA":
        arrancar_motores(1.0, -1.0)
        start = time.monotonic()
        while time.monotonic() - start < 0.3:
            if boton_presionado(): return True
            if leer_borde_mejorado() is not None: break

    frenar()
    return False

def buscar_y_atacar():
    global _direccion_giro_busqueda, _tiempo_ultimo_cambio, _barridos_sin_rival, _rival_perdido_count

    if boton_presionado(): return True

    if rival_detectado():
        _rival_perdido_count = 0
        ib.pixel = (0, 255, 0)
                                                                                           
        arrancar_motores(1.0, 1.0)
        start = time.monotonic()
        while time.monotonic() - start < 0.15:                               
            if boton_presionado(): return True
            b1 = leer_borde_mejorado()                                       
            if b1 is not None: return False

    else:
        _rival_perdido_count += 1

        if _rival_perdido_count < MAX_PERDIDO:
                                                    
            ib.pixel = (0, 0, 255)
            arrancar_motores(1.0, 1.0)
            start = time.monotonic()
            while time.monotonic() - start < 0.05:
                if boton_presionado(): return True
                if leer_borde_mejorado() is not None: return False
            return False

        ib.pixel = (255, 165, 0)

        ahora = time.monotonic()
        if ahora - _tiempo_ultimo_cambio > INTERVALO_CAMBIO_GIRO:
            _barridos_sin_rival += 1
            if _barridos_sin_rival % 3 == 0:
                _direccion_giro_busqueda *= -1
            _tiempo_ultimo_cambio = ahora

        arrancar_motores(1.0 * _direccion_giro_busqueda, -1.0 * _direccion_giro_busqueda)
        start = time.monotonic()
                                                           
        while time.monotonic() - start < 0.25:
            if boton_presionado(): return True
            if rival_detectado():
                _rival_perdido_count = 0
                return False
            if leer_borde_mejorado() is not None: return False

    return False

def inicio_ronda(ronda):
    if ronda == 1:
        ib.pixel = COLORES_RONDA[1]
        arrancar_motores(1.0, 1.0)
        start = time.monotonic()
        while time.monotonic() - start < 0.3:
            if leer_borde_mejorado() is not None: break
            if rival_detectado():
                arrancar_motores(1.0, 1.0)
                break

    elif ronda == 2:
        ib.pixel = COLORES_RONDA[2]
        arrancar_motores(1.0, -1.0)
        start = time.monotonic()
        while time.monotonic() - start < 0.33:
            if leer_borde_mejorado() is not None: break
            
    elif ronda == 3:
        ib.pixel = COLORES_RONDA[3]
        arrancar_motores(1.0, -1.0)
        start = time.monotonic()
        while time.monotonic() - start < 0.65:
            if leer_borde_mejorado() is not None: break

    frenar()
    ib.pixel = (0, 0, 0)

frenar()
ronda = 1

while ronda <= 3:

    print(f"=== RONDA {ronda} ===")
    for _ in range(ronda):
        ib.pixel = COLORES_RONDA[ronda]
        sleep(0.3)
        ib.pixel = (0, 0, 0)
        sleep(0.3)

    calibracion_por_pasos()
    inicio_ronda(ronda)

    _rival_perdido_count = 0
    _barridos_sin_rival = 0
    _direccion_giro_busqueda = 1
    _tiempo_ultimo_cambio = time.monotonic()

    while True:

        if boton_presionado():
            frenar()
            print(f"Ronda {ronda} terminada.")
            break

        borde = leer_borde_mejorado()
        if borde is not None:
            if maniobra_escape(borde):
                frenar()
                print(f"Ronda {ronda} terminada.")
                break
        else:
            _tiempo_inicio_borde = None                                      
            if buscar_y_atacar():
                frenar()
                print(f"Ronda {ronda} terminada.")
                break

    ronda += 1
    sleep(0.5)                           

frenar()
ib.pixel = (200, 200, 200)
print("Partida completa.")
