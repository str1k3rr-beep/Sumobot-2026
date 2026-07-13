import board
import keypad
from ideaboard import IdeaBoard
from time import sleep
import time
import digitalio

ib = IdeaBoard()
sleep(1.0)  

keys = keypad.Keys((board.IO0,), value_when_pressed=False, pull=True)

sen1 = ib.AnalogIn(board.IO36) # Frontal / Lateral Izquierdo (Índice 0)
sen2 = ib.AnalogIn(board.IO39) # Frontal / Lateral Derecho   (Índice 1)
sen3 = ib.AnalogIn(board.IO34) # Apoyo Izquierdo             (Índice 2)
sen4 = ib.AnalogIn(board.IO35) # Apoyo Derecho               (Índice 3)

infrarrojos = [sen1, sen2, sen3, sen4]
umbrales = [0, 0, 0, 0]

trigger = digitalio.DigitalInOut(board.IO25)
trigger.direction = digitalio.Direction.OUTPUT
trigger.value = False

echo = digitalio.DigitalInOut(board.IO26)
echo.direction = digitalio.Direction.INPUT

DISTANCIA_RIVAL_CM = 60

COLORES_RONDA = {
    1: (255, 100, 0),   
    2: (0, 255, 100),   
    3: (0, 100, 255),   
}

_direccion_giro_busqueda = 1
_tiempo_ultimo_cambio = 0
_barridos_sin_rival = 0
_rival_perdido_count = 0

MAX_PERDIDO = 3
INTERVALO_CAMBIO_GIRO = 0.2


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


def arrancar_motores(m1, m2, duracion=0.05):
    """Sube throttle de 0 a target de forma continua, sin saltos."""
    start = time.monotonic()
    while True:
        transcurrido = time.monotonic() - start
        if transcurrido >= duracion:
            break
        progreso = transcurrido / duracion  
        ib.motor_1.throttle = m1 * progreso
        ib.motor_2.throttle = m2 * progreso
    
    ib.motor_1.throttle = m1
    ib.motor_2.throttle = m2


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

    print("Iniciando en 1 segundo...")
    for _ in range(0):
        ib.pixel = (255, 255, 0)
        sleep(0.4)
        ib.pixel = (0, 0, 0)
        sleep(0.4)
    sleep(0.3)  


def leer_borde_mejorado():
    def leer():
        return [sen.value < umbrales[i] for i, sen in enumerate(infrarrojos)]

    d1 = leer()
    sleep(0.002)  
    d2 = leer()

    detectados = [d1[i] and d2[i] for i in range(4)]

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
    ib.pixel = (255, 0, 255)

    ib.motor_1.throttle = 0
    ib.motor_2.throttle = 0
    sleep(0.05)

    
    arrancar_motores(1.0, -1.0)
    start = time.monotonic()
    while time.monotonic() - start < 0.15:
        if boton_presionado(): return True
        if leer_borde_mejorado() is not None: break
        pass  

    ib.motor_1.throttle = 0
    ib.motor_2.throttle = 0
    sleep(0.05)

    if direccion in ("FRENTE", "FRENTE_IZQ"):
        arrancar_motores(-1.0, -1.0)
        start = time.monotonic()
        while time.monotonic() - start < 0.45:
            if boton_presionado(): return True
            if leer_borde_mejorado() is not None: break

    elif direccion == "IZQUIERDA":
        arrancar_motores(1.0, 1.0)
        start = time.monotonic()
        while time.monotonic() - start < 0.3:
            if boton_presionado(): return True
            if leer_borde_mejorado() is not None: break

    elif direccion == "DERECHA":
        arrancar_motores(-1.0, -1.0)
        start = time.monotonic()
        while time.monotonic() - start < 0.3:
            if boton_presionado(): return True
            if leer_borde_mejorado() is not None: break

    ib.motor_1.throttle = 0
    ib.motor_2.throttle = 0
    sleep(0.005)
    return False


def buscar_y_atacar():
    global _direccion_giro_busqueda, _tiempo_ultimo_cambio, _barridos_sin_rival, _rival_perdido_count

    if boton_presionado(): return True

    if rival_detectado():
        _rival_perdido_count = 0
        ib.pixel = (0, 255, 0)
        wiggle_interval = 0.18
        wiggle_strength = 0.9
        wiggle_start = time.monotonic()
        if int((time.monotonic() - wiggle_start) / wiggle_interval) % 2 == 0:
            arrancar_motores(-1.0, 1.0 - wiggle_strength)
        else:
            arrancar_motores(-1.0 + wiggle_strength, 1.0)
        start = time.monotonic()
        while time.monotonic() - start < 0.02:
            if boton_presionado(): return True
            if leer_borde_mejorado() is not None: return False

    else:
        _rival_perdido_count += 1

        if _rival_perdido_count < MAX_PERDIDO:
            ib.pixel = (0, 0, 255)
            arrancar_motores(-1.0, 1.0)
            start = time.monotonic()
            while time.monotonic() - start < 0.02:
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

        arrancar_motores(0.8 * _direccion_giro_busqueda, -0.8 * _direccion_giro_busqueda)
        start = time.monotonic()
        while time.monotonic() - start < 0.02:
            if boton_presionado(): return True
            if leer_borde_mejorado() is not None: return False

    return False


def inicio_ronda(ronda):
    sleep(0.2)

    if ronda == 1:
        ib.pixel = COLORES_RONDA[1]
        arrancar_motores(-1.0, 1.0)
        start = time.monotonic()
        while time.monotonic() - start < 0.3:
            if leer_borde_mejorado() is not None: break
            if rival_detectado():                  
                arrancar_motores(-1.0, 1.0)        
                break                              

    elif ronda == 2:
        ib.pixel = COLORES_RONDA[2]
        arrancar_motores(-1.0, -1.0)
        start = time.monotonic()
        while time.monotonic() - start < 0.25:
            if leer_borde_mejorado() is not None: break
            if rival_detectado():
                arrancar_motores(-1.0, 1.0)
                break

    elif ronda == 3:
        ib.pixel = COLORES_RONDA[3]
        arrancar_motores(1.0, 1.0)
        start = time.monotonic()
        while time.monotonic() - start < 0.6:
            if leer_borde_mejorado() is not None: break
            if rival_detectado():
                arrancar_motores(-1.0, 1.0)
                break

    ib.motor_1.throttle = 0
    ib.motor_2.throttle = 0
    sleep(0.05)
    ib.pixel = (0, 0, 0)


# ============================================================
# EJECUCIÓN PRINCIPAL
# ============================================================

ib.motor_1.throttle = 0
ib.motor_2.throttle = 0

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
            ib.motor_1.throttle = 0
            ib.motor_2.throttle = 0
            print(f"Ronda {ronda} terminada.")
            break

        
        borde = leer_borde_mejorado()
        if borde is not None:
            if maniobra_escape(borde):
                ib.motor_1.throttle = 0
                ib.motor_2.throttle = 0
                print(f"Ronda {ronda} terminada.")
                break
        else:
            if buscar_y_atacar():
                ib.motor_1.throttle = 0
                ib.motor_2.throttle = 0
                print(f"Ronda {ronda} terminada.")
                break

    ronda += 1
    sleep(0.5)

ib.motor_1.throttle = 0
ib.motor_2.throttle = 0
ib.pixel = (200, 200, 200)
print("Partida completa.")
