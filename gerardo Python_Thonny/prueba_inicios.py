import board
import keypad
from ideaboard import IdeaBoard
from time import sleep
import time
import digitalio

ib = IdeaBoard()
sleep(1.0)  # Necesario para que el hardware arranque

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

DISTANCIA_RIVAL_CM = 50

COLORES_RONDA = {
    1: (255, 100, 0),
    2: (0, 255, 100),
    3: (0, 100, 255),
}

# ============================================================
# TIEMPOS AJUSTABLES — modificá estos valores entre pruebas
# ============================================================
TIEMPO_RONDA1 = 0.3
TIEMPO_RONDA2 = 0.33
TIEMPO_RONDA3 = 0.65

# Referencias directas a los throttles
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
    _m1.throttle = m1
    _m2.throttle = m2


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
    UMBRAL_FIJO = 3300
    for i in range(4):
        umbrales[i] = UMBRAL_FIJO
    print(f"Umbrales fijos establecidos: {umbrales}")
    print("¡CALIBRACIÓN LISTA! Presiona BOOT para iniciar la prueba.")
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


def inicio_ronda(ronda):
    t_inicio = time.monotonic()
    motivo_corte = "tiempo completo"

    if ronda == 1:
        ib.pixel = COLORES_RONDA[1]
        arrancar_motores(-1.0, 1.0)
        start = time.monotonic()
        while time.monotonic() - start < TIEMPO_RONDA1:
            if leer_borde_mejorado() is not None:
                motivo_corte = "borde detectado"
                break
            if rival_detectado():
                arrancar_motores(-1.0, 1.0)
                motivo_corte = "rival detectado"
                break

    elif ronda == 2:
        ib.pixel = COLORES_RONDA[2]
        arrancar_motores(-1.0, -1.0)
        start = time.monotonic()
        while time.monotonic() - start < TIEMPO_RONDA2:
            if leer_borde_mejorado() is not None:
                motivo_corte = "borde detectado"
                break

    elif ronda == 3:
        ib.pixel = COLORES_RONDA[3]
        arrancar_motores(-1.0, -1.0)
        start = time.monotonic()
        while time.monotonic() - start < TIEMPO_RONDA3:
            if leer_borde_mejorado() is not None:
                motivo_corte = "borde detectado"
                break

    frenar()
    ib.pixel = (0, 0, 0)
    duracion_real = time.monotonic() - t_inicio
    print(f"Ronda {ronda}: corte por [{motivo_corte}], duración real = {duracion_real:.3f}s")


# ============================================================
# EJECUCIÓN PRINCIPAL — prueba aislada de inicio_ronda
# ============================================================

frenar()
calibracion_por_pasos()

ronda_actual = 1

print("Probando solo maniobras de INICIO DE RONDA.")
print(f"Tiempos actuales -> R1: {TIEMPO_RONDA1}s | R2: {TIEMPO_RONDA2}s | R3: {TIEMPO_RONDA3}s")
print("Presioná BOOT para ejecutar la maniobra de la ronda actual.")

while True:
    # Parpadeo indicando qué ronda se va a probar a continuación
    for _ in range(ronda_actual):
        ib.pixel = COLORES_RONDA[ronda_actual]
        sleep(0.2)
        ib.pixel = (0, 0, 0)
        sleep(0.2)

    print(f"--- Listo para probar RONDA {ronda_actual} ---")
    esperar_boton_y_leer((50, 50, 50))

    inicio_ronda(ronda_actual)

    sleep(0.5)
    ronda_actual = (ronda_actual % 3) + 1
