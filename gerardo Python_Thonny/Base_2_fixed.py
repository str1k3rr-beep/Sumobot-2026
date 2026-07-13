# Tomás de Camino Beck / Mod: Evasión Direccional Corregida y Nueva Distribución
# Escuela de Sistemas Inteligentes - Universidad Cenfotec
# === MÓDULO AÑADIDO: Búsqueda activa con ultrasonido (sin modificar base) ===

import board
import keypad
from ideaboard import IdeaBoard
from time import sleep
import time
import random

# --- NUEVO: Ultrasonido ---
import pulseio
import digitalio

ib = IdeaBoard()

keys = keypad.Keys((board.IO0,), value_when_pressed=False, pull=True)

# Tu nueva distribución conceptual:
sen1 = ib.AnalogIn(board.IO36) # Frontal / Lateral Izquierdo (Índice 0)
sen2 = ib.AnalogIn(board.IO39) # Frontal / Lateral Derecho   (Índice 1)
sen3 = ib.AnalogIn(board.IO34) # Apoyo Izquierdo             (Índice 2)
sen4 = ib.AnalogIn(board.IO35) # Apoyo Derecho               (Índice 3)

infrarrojos = [sen1, sen2, sen3, sen4]
umbrales = [0, 0, 0, 0]


# ============================================================
# NUEVO: Configuración del sensor ultrasonido HC-SR04
# Ajusta los pines según tu cableado real en la IdeaBoard
# ============================================================
trigger = digitalio.DigitalInOut(board.IO25)
trigger.direction = digitalio.Direction.OUTPUT
trigger.value = False

echo = digitalio.DigitalInOut(board.IO26)
echo.direction = digitalio.Direction.INPUT

# Distancia en cm por debajo de la cual se considera que hay rival
DISTANCIA_RIVAL_CM = 60

# Tiempo máximo de búsqueda rotando antes de avanzar de todas formas (segundos)
TIMEOUT_BUSQUEDA = 0.6


def medir_distancia_cm():
    """Dispara el ultrasonido y retorna distancia en cm. Retorna 999 si falla."""
    # Pulso de disparo
    trigger.value = True
    time.sleep(0.00001)  # 10 µs
    trigger.value = False

    # Esperar flanco de subida del echo
    start = time.monotonic()
    while not echo.value:
        if time.monotonic() - start > 0.006:
            return 999  # timeout sin respuesta

    t_inicio = time.monotonic()

    # Esperar flanco de bajada
    while echo.value:
        if time.monotonic() - t_inicio > 0.004:
            return 999  # timeout eco demasiado largo

    t_fin = time.monotonic()

    duracion = t_fin - t_inicio
    distancia = (duracion * 34300) / 2  # cm
    return distancia


def rival_detectado():
    """Retorna True si el ultrasonido ve al rival dentro del rango."""
    d = medir_distancia_cm()
    return d < DISTANCIA_RIVAL_CM


# ============================================================
# BASE SIN TOCAR — funciones originales
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

    print("Iniciando cuenta regresiva de 3 segundos...")
    for i in range(2, 0, -1):
        ib.pixel = (255, 255, 0)
        sleep(0.5)
        ib.pixel = (0, 0, 0)
        sleep(0.5)


def leer_borde_mejorado():
    """
    Doble lectura para confirmar y distinguir frontal de lateral en sen1.
    """
    def leer():
        return [sen.value < umbrales[i] for i, sen in enumerate(infrarrojos)]

    # Primera lectura
    d1 = leer()
    sleep(0.005)
    # Segunda lectura para confirmar (elimina falsos positivos)
    d2 = leer()

    # Solo cuenta si ambas lecturas coinciden
    detectados = [d1[i] and d2[i] for i in range(4)]

    # Frente: sen1 Y sen2
    if detectados[0] and detectados[1]:
        return "FRENTE"

    # sen1 activado: distinguir si es frontal o lateral izquierdo
    # Si sen3 también se activa → claramente lateral izquierdo
    # Si solo sen1 → asumir frontal (más seguro que asumir lateral)
    elif detectados[0] and detectados[2]:
        return "IZQUIERDA"   # Confirmado lateral
    elif detectados[0] and not detectados[2]:
        return "FRENTE_IZQ"  # Ambiguo → tratar como frontal

    # Derecha: sen2 O sen4
    elif detectados[1] or detectados[3]:
        return "DERECHA"

    # Solo sen3 activado sin sen1
    elif detectados[2]:
        return "IZQUIERDA"

    return None


def maniobra_escape(direccion):
    ib.pixel = (255, 0, 255)

    ib.motor_1.throttle = 0
    ib.motor_2.throttle = 0
    sleep(0.05)

    # Retroceso base
    ib.motor_1.throttle = 1.0
    ib.motor_2.throttle = -1.0
    sleep(0.15)
    ib.motor_1.throttle = 0
    ib.motor_2.throttle = 0
    sleep(0.05)

    if direccion in ("FRENTE", "FRENTE_IZQ"):
        # Giro vigilando el borde continuamente
        start = time.monotonic()
        while time.monotonic() - start < 0.45:
            if leer_borde_mejorado() is not None:
                break
            ib.motor_1.throttle = -1.0
            ib.motor_2.throttle = -1.0
            sleep(0.01)

    elif direccion == "IZQUIERDA":
        start = time.monotonic()
        while time.monotonic() - start < 0.3:
            if leer_borde_mejorado() is not None:
                break
            ib.motor_1.throttle = 1.0
            ib.motor_2.throttle = 1.0
            sleep(0.01)

    elif direccion == "DERECHA":
        start = time.monotonic()
        while time.monotonic() - start < 0.3:
            if leer_borde_mejorado() is not None:
                break
            ib.motor_1.throttle = -1.0
            ib.motor_2.throttle = -1.0
            sleep(0.01)

    ib.motor_1.throttle = 0
    ib.motor_2.throttle = 0
    sleep(0.005)

# ============================================================
# NUEVO: Lógica de búsqueda activa con ultrasonido
# Sustituye el bloque "else / ataque frontal" del loop original
# ============================================================

# Dirección actual de giro de búsqueda (-1 izq / 1 der)
# Variables globales necesarias (ponlas junto a las otras globales al inicio del archivo)
_direccion_giro_busqueda = 1
_tiempo_ultimo_cambio = time.monotonic()
_barridos_sin_rival = 0
_rival_perdido_count = 0

MAX_PERDIDO = 3          # Fallos consecutivos antes de abandonar persecución
INTERVALO_CAMBIO_GIRO = 0.2  # Reducido de 0.4 a 0.2 para no pasarte del rival

def buscar_y_atacar():
    global _direccion_giro_busqueda, _tiempo_ultimo_cambio, _barridos_sin_rival, _rival_perdido_count

    if rival_detectado():
        # ---- RIVAL A LA VISTA: ataque directo ----
        _rival_perdido_count = 0  # Resetear contador de pérdida
        ib.pixel = (0, 255, 0)
        ib.motor_1.throttle = -1.0
        ib.motor_2.throttle = 1.0
        sleep(0.02)

    else:
        # ---- RIVAL NO DETECTADO ----
        _rival_perdido_count += 1

        if _rival_perdido_count < MAX_PERDIDO:
            # Probablemente ruido del sensor, seguir atacando brevemente
            ib.pixel = (0, 0, 255)  # Verde más oscuro = "creo que sigo viéndolo"
            ib.motor_1.throttle = -1.0
            ib.motor_2.throttle = 1.0
            sleep(0.02)
            return

        # ---- SIN RIVAL CONFIRMADO: girar buscando ----
        ib.pixel = (255, 165, 0)  # Naranja = modo búsqueda

        ahora = time.monotonic()
        if ahora - _tiempo_ultimo_cambio > INTERVALO_CAMBIO_GIRO:
            _barridos_sin_rival += 1
            if _barridos_sin_rival % 3 == 0:  # Invertir dirección cada 3 barridos
                _direccion_giro_busqueda *= -1
            _tiempo_ultimo_cambio = ahora

        # Microgiro consistente en la dirección actual
        ib.motor_1.throttle = 0.8 * _direccion_giro_busqueda
        ib.motor_2.throttle = -0.8 * _direccion_giro_busqueda
        sleep(0.02)


###### EJECUCIÓN PRINCIPAL #######
ib.motor_1.throttle = 0
ib.motor_2.throttle = 0

calibracion_por_pasos()

while True:
    # PRIORIDAD 1: borde siempre manda (lógica base intacta)
    direccion_impacto = leer_borde_mejorado()

    if direccion_impacto is not None:
        maniobra_escape(direccion_impacto)
    else:
        # PRIORIDAD 2: buscar/atacar con ultrasonido (módulo nuevo)
        buscar_y_atacar()
        