# Tomás de Camino Beck / Mod: Evasión Direccional Corregida y Nueva Distribución
# Escuela de Sistemas Inteligentes - Universidad Cenfotec
# === MÓDULO AÑADIDO: Búsqueda activa con ultrasonido (sin modificar base) ===

import board
import keypad
from ideaboard import IdeaBoard
from time import sleep
import time
import random
import digitalio

ib = IdeaBoard()
sleep(1.0)  # Estabilizar voltaje de batería al arrancar

keys = keypad.Keys((board.IO0,), value_when_pressed=False, pull=True)

# Sensores infrarrojos
sen1 = ib.AnalogIn(board.IO36) # Frontal / Lateral Izquierdo (Índice 0)
sen2 = ib.AnalogIn(board.IO39) # Frontal / Lateral Derecho   (Índice 1)
sen3 = ib.AnalogIn(board.IO34) # Apoyo Izquierdo             (Índice 2)
sen4 = ib.AnalogIn(board.IO35) # Apoyo Derecho               (Índice 3)

infrarrojos = [sen1, sen2, sen3, sen4]
umbrales = [0, 0, 0, 0]

# Ultrasonido HC-SR04
trigger = digitalio.DigitalInOut(board.IO25)
trigger.direction = digitalio.Direction.OUTPUT
trigger.value = False

echo = digitalio.DigitalInOut(board.IO26)
echo.direction = digitalio.Direction.INPUT

# Distancia en cm por debajo de la cual se considera que hay rival
DISTANCIA_RIVAL_CM = 60

# Colores por ronda
COLORES_RONDA = {
    1: (255, 100, 0),   # Naranja = Ronda 1
    2: (0, 255, 100),   # Verde   = Ronda 2
    3: (0, 100, 255),   # Celeste = Ronda 3
}

# Variables de búsqueda
_direccion_giro_busqueda = 1
_tiempo_ultimo_cambio = 0  # Cambiado de time.monotonic() a 0 para estabilidad con batería
_barridos_sin_rival = 0
_rival_perdido_count = 0

MAX_PERDIDO = 3
INTERVALO_CAMBIO_GIRO = 0.2


# ============================================================
# ULTRASONIDO
# ============================================================

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
        if time.monotonic() - start > 0.05:  # Guard total
            return 999

    t_fin = time.monotonic()
    return (t_fin - t_inicio) * 34300 / 2


def rival_detectado():
    return medir_distancia_cm() < DISTANCIA_RIVAL_CM


# ============================================================
# BOTÓN BOOT — revisable desde cualquier función
# ============================================================

def boton_presionado():
    """Retorna True si soltaron BOOT. Llamar desde cualquier parte del código."""
    event = keys.events.get()
    return bool(event and event.released)


# ============================================================
# CALIBRACIÓN
# ============================================================

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
    ib.pixel = (255, 255, 0)
    sleep(0.5)
    ib.pixel = (0, 0, 0)
    sleep(0.5)


# ============================================================
# SENSORES DE BORDE
# ============================================================

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
    elif detectados[0] and not detectados[2]:
        return "FRENTE_IZQ"
    elif detectados[1] or detectados[3]:
        return "DERECHA"
    elif detectados[2]:
        return "IZQUIERDA"

    return None


# ============================================================
# ESCAPE
# ============================================================

def maniobra_escape(direccion):
    ib.pixel = (255, 0, 255)

    ib.motor_1.throttle = 0
    ib.motor_2.throttle = 0
    sleep(0.05)

    # Retroceso base — igual que code_1 original, sin interrupciones
    ib.motor_1.throttle = 1.0
    ib.motor_2.throttle = -1.0
    sleep(0.15)
    ib.motor_1.throttle = 0
    ib.motor_2.throttle = 0
    sleep(0.05)

    if direccion in ("FRENTE", "FRENTE_IZQ"):
        start = time.monotonic()
        while time.monotonic() - start < 0.45:
            if boton_presionado(): return True
            if leer_borde_mejorado() is not None: break
            ib.motor_1.throttle = -1.0
            ib.motor_2.throttle = -1.0  # igual que code_1 original
            sleep(0.01)

    elif direccion == "IZQUIERDA":
        start = time.monotonic()
        while time.monotonic() - start < 0.3:
            if boton_presionado(): return True
            if leer_borde_mejorado() is not None: break
            ib.motor_1.throttle = 1.0
            ib.motor_2.throttle = 1.0  # igual que code_1 original
            sleep(0.01)

    elif direccion == "DERECHA":
        start = time.monotonic()
        while time.monotonic() - start < 0.3:
            if boton_presionado(): return True
            if leer_borde_mejorado() is not None: break
            ib.motor_1.throttle = -1.0
            ib.motor_2.throttle = -1.0  # igual que code_1 original
            sleep(0.01)

    ib.motor_1.throttle = 0
    ib.motor_2.throttle = 0
    sleep(0.005)
    return False


# ============================================================
# BÚSQUEDA Y ATAQUE
# ============================================================

def buscar_y_atacar():
    global _direccion_giro_busqueda, _tiempo_ultimo_cambio, _barridos_sin_rival, _rival_perdido_count

    if boton_presionado(): return True

    if rival_detectado():
        _rival_perdido_count = 0
        ib.pixel = (0, 255, 0)
        ib.motor_1.throttle = -1.0
        ib.motor_2.throttle = 1.0
        sleep(0.02)

    else:
        _rival_perdido_count += 1

        if _rival_perdido_count < MAX_PERDIDO:
            ib.pixel = (0, 0, 255)
            ib.motor_1.throttle = -1.0
            ib.motor_2.throttle = 1.0
            sleep(0.02)
            return False

        ib.pixel = (255, 165, 0)

        ahora = time.monotonic()
        if ahora - _tiempo_ultimo_cambio > INTERVALO_CAMBIO_GIRO:
            _barridos_sin_rival += 1
            if _barridos_sin_rival % 3 == 0:
                _direccion_giro_busqueda *= -1
            _tiempo_ultimo_cambio = ahora

        ib.motor_1.throttle =  0.8 * _direccion_giro_busqueda
        ib.motor_2.throttle = -0.8 * _direccion_giro_busqueda
        sleep(0.02)

    return False


# ============================================================
# INICIO POR RONDA
# ============================================================

def inicio_ronda(ronda):
    if ronda == 1:
        ib.pixel = COLORES_RONDA[1]
        ib.motor_1.throttle = -1.0
        ib.motor_2.throttle = 1.0
        sleep(0.3)

    elif ronda == 2:
        ib.pixel = COLORES_RONDA[2]
        ib.motor_1.throttle = -1.0
        ib.motor_2.throttle = -1.0
        sleep(0.35)  # Ajustar en pruebas para 90° exacto

    elif ronda == 3:
        ib.pixel = COLORES_RONDA[3]
        ib.motor_1.throttle = 1.0
        ib.motor_2.throttle = 1.0
        sleep(0.7)   # Ajustar en pruebas para 180° exacto

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

    # Resetear variables de búsqueda
    _rival_perdido_count = 0
    _barridos_sin_rival = 0
    _direccion_giro_busqueda = 1
    _tiempo_ultimo_cambio = time.monotonic()

    # Loop de combate
    while True:

        if boton_presionado():
            ib.motor_1.throttle = 0
            ib.motor_2.throttle = 0
            print(f"Ronda {ronda} terminada.")
            break

        direccion_impacto = leer_borde_mejorado()
        if direccion_impacto is not None:
            if maniobra_escape(direccion_impacto):
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

# Fin de las 3 rondas
ib.motor_1.throttle = 0
ib.motor_2.throttle = 0
ib.pixel = (255, 255, 255)  # Blanco fijo = partida completa
print("Partida completa.")
