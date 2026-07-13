# Código corregido - evita bloqueos por ultrasonido y mejora estabilidad en baterías

import board
import keypad
from ideaboard import IdeaBoard
from time import sleep
import time
import random
import digitalio

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
    try:
        trigger.value = True
        time.sleep(0.00001)
        trigger.value = False

        start = time.monotonic()

        while not echo.value:
            if time.monotonic() - start > 0.01:
                return 999

        t_inicio = time.monotonic()

        while echo.value:
            if time.monotonic() - t_inicio > 0.01:
                return 999

        t_fin = time.monotonic()
        return (t_fin - t_inicio) * 34300 / 2

    except:
        return 999


def rival_detectado():
    return medir_distancia_cm() < DISTANCIA_RIVAL_CM


def boton_presionado():
    event = keys.events.get()
    return bool(event and event.released)


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
    print("PASO 1: NEGRO")
    valores_negro = esperar_boton_y_leer((255, 0, 0))

    print("PASO 2: BLANCO")
    valores_blanco = esperar_boton_y_leer((255, 255, 255))

    for i in range(4):
        umbrales[i] = (valores_negro[i] + valores_blanco[i]) // 2

    print("LISTO")
    esperar_boton_y_leer((0, 255, 0))

    print("Iniciando...")
    for _ in range(2):
        ib.pixel = (255, 255, 0)
        sleep(0.4)
        ib.pixel = (0, 0, 0)
        sleep(0.4)

    sleep(0.3)


def leer_borde_mejorado():
    def leer():
        return [sen.value < umbrales[i] for i, sen in enumerate(infrarrojos)]

    d1 = leer()
    sleep(0.005)
    d2 = leer()

    detectados = [d1[i] and d2[i] for i in range(4)]

    if detectados[0] and detectados[1]:
        return "FRENTE"
    elif detectados[0] and detectados[2]:
        return "IZQUIERDA"
    elif detectados[1] or detectados[3]:
        return "DERECHA"
    elif detectados[2]:
        return "IZQUIERDA"

    return None


def inicio_ronda(ronda):
    sleep(0.2)

    if ronda == 1:
        ib.pixel = COLORES_RONDA[1]
        ib.motor_1.throttle = -1.0
        ib.motor_2.throttle = 1.0
        sleep(0.3)

    elif ronda == 2:
        ib.pixel = COLORES_RONDA[2]
        ib.motor_1.throttle = -1.0
        ib.motor_2.throttle = -1.0
        sleep(0.35)

    elif ronda == 3:
        ib.pixel = COLORES_RONDA[3]
        ib.motor_1.throttle = 1.0
        ib.motor_2.throttle = 1.0
        sleep(0.7)

    ib.motor_1.throttle = 0
    ib.motor_2.throttle = 0
    sleep(0.05)
    ib.pixel = (0, 0, 0)


def buscar_y_atacar():
    global _direccion_giro_busqueda, _tiempo_ultimo_cambio, _barridos_sin_rival, _rival_perdido_count

    if boton_presionado(): return True

    if rival_detectado():
        _rival_perdido_count = 0
        ib.pixel = (0, 255, 0)
        ib.motor_1.throttle = -1.0
        ib.motor_2.throttle = 1.0
        sleep(0.05)

    else:
        _rival_perdido_count += 1

        if _rival_perdido_count < MAX_PERDIDO:
            ib.pixel = (0, 0, 255)
            ib.motor_1.throttle = -1.0
            ib.motor_2.throttle = 1.0
            sleep(0.05)
            return False

        ib.pixel = (255, 165, 0)

        ahora = time.monotonic()
        if ahora - _tiempo_ultimo_cambio > INTERVALO_CAMBIO_GIRO:
            _barridos_sin_rival += 1
            if _barridos_sin_rival % 3 == 0:
                _direccion_giro_busqueda *= -1
            _tiempo_ultimo_cambio = ahora

        ib.motor_1.throttle = 0.8 * _direccion_giro_busqueda
        ib.motor_2.throttle = -0.8 * _direccion_giro_busqueda
        sleep(0.05)

    return False


ib.motor_1.throttle = 0
ib.motor_2.throttle = 0

ronda = 1

while ronda <= 3:
    print(f"RONDA {ronda}")

    calibracion_por_pasos()
    inicio_ronda(ronda)

    _rival_perdido_count = 0
    _barridos_sin_rival = 0
    _direccion_giro_busqueda = 1
    _tiempo_ultimo_cambio = time.monotonic()

    while True:
        if boton_presionado():
            break

        direccion = leer_borde_mejorado()
        if direccion is not None:
            ib.motor_1.throttle = 0
            ib.motor_2.throttle = 0
            break
        else:
            if buscar_y_atacar():
                break

    ronda += 1
    sleep(0.5)

ib.motor_1.throttle = 0
ib.motor_2.throttle = 0
ib.pixel = (255, 255, 255)

print("FIN")
