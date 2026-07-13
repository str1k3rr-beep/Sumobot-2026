import board
import keypad
from ideaboard import IdeaBoard
from time import sleep
import time
import digitalio
import random

ib = IdeaBoard()
sleep(1.0)  # Necesario para que el hardware arranque

keys = keypad.Keys((board.IO0,), value_when_pressed=False, pull=True)

sen1 = ib.AnalogIn(board.IO36) # Frontal / Lateral Izquierdo (Índice 0)
sen2 = ib.AnalogIn(board.IO39) # Frontal / Lateral Derecho   (Índice 1)
sen3 = ib.AnalogIn(board.IO34) # Apoyo Izquierdo             (Índice 2)
sen4 = ib.AnalogIn(board.IO35) # Apoyo Derecho               (Índice 3)

infrarrojos = [sen1, sen2, sen3, sen4]

TH1 = 13931
TH2 = 14864
TH3 = 3991
TH4 = 14189

umbrales = [TH1, TH2, TH3, TH4]

trigger = digitalio.DigitalInOut(board.IO25)
trigger.direction = digitalio.Direction.OUTPUT
trigger.value = False

echo = digitalio.DigitalInOut(board.IO26)
echo.direction = digitalio.Direction.INPUT

DISTANCIA_RIVAL_CM = 40

COLORES_RONDA = {
    1: (255, 100, 0),
    2: (0, 255, 100),
    3: (0, 100, 255),
}

_direccion_giro_busqueda = 1
_tiempo_ultimo_cambio = 0
_barridos_sin_rival = 0
_rival_perdido_count = 0
_tiempo_inicio_borde = None  # Para detectar borde prolongado

MAX_PERDIDO = 1
INTERVALO_CAMBIO_GIRO = 0.15

# Referencias directas a los throttles — evita lookup de atributos en cada ciclo
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


# Sin ramp-up: arranca directo a full potencia
def arrancar_motores(m1, m2):
    _m1.throttle = m1
    _m2.throttle = m2


def frenar():
    _m1.throttle = 0
    _m2.throttle = 0


# Lectura de borde sin sleep — una sola lectura por ciclo es suficiente
# Si hay falsos positivos, se puede volver a 0.001
def leer_borde_mejorado():
    detectados = [sen.value < umbrales[i] for i, sen in enumerate(infrarrojos)]
    # [0]=sen1 frontal izq, [1]=sen2 frontal der, [2]=sen3 apoyo izq, [3]=sen4 apoyo der

    # sen2(IO39) y sen4(IO35) ven blanco = lado derecho en borde = rival empuja desde IZQUIERDA
    if detectados[1] and detectados[3] and not detectados[0] and not detectados[2]:
        return "EMPUJE_IZQUIERDA"

    # sen1(IO36) y sen3(IO34) ven blanco = lado izquierdo en borde = rival empuja desde DERECHA
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

    # Empuje lateral inmediato — reacciona sin esperar 0.4s
    if direccion == "EMPUJE_IZQUIERDA":
        ib.pixel = (0, 255, 255)
        # Rival empuja desde izquierda, lado derecho en borde → gira izquierda para salir del blanco
        arrancar_motores(1.0, 1.0)
        start = time.monotonic()
        while time.monotonic() - start < 0.3:
            if boton_presionado(): return True
            if leer_borde_mejorado() is None: break
        # Avanza al centro
        arrancar_motores(-1.0, 1.0)
        start = time.monotonic()
        while time.monotonic() - start < 0.25:
            if boton_presionado(): return True
            if leer_borde_mejorado() is not None: break
        _tiempo_inicio_borde = None
        frenar()
        return False

    if direccion == "EMPUJE_DERECHA":
        ib.pixel = (0, 255, 255)
        # Rival empuja desde derecha, lado izquierdo en borde → gira derecha para salir del blanco
        arrancar_motores(-1.0, -1.0)
        start = time.monotonic()
        while time.monotonic() - start < 0.3:
            if boton_presionado(): return True
            if leer_borde_mejorado() is None: break
        # Avanza al centro
        arrancar_motores(-1.0, 1.0)
        start = time.monotonic()
        while time.monotonic() - start < 0.25:
            if boton_presionado(): return True
            if leer_borde_mejorado() is not None: break
        _tiempo_inicio_borde = None
        frenar()
        return False

    ahora = time.monotonic()

    # Registrar cuándo empezó a ver el borde
    if _tiempo_inicio_borde is None:
        _tiempo_inicio_borde = ahora

    tiempo_en_borde = ahora - _tiempo_inicio_borde

    # Si lleva más de 0.4s en borde y no hay rival → está atascado
    if tiempo_en_borde > 0.2 and not rival_detectado():

        # Empuje por lado IZQUIERDO: sen3 solo (IO34)
        if direccion == "IZQUIERDA":
            ib.pixel = (0, 255, 255)  # Cyan = empuje lateral izquierdo
            # Gira hacia la derecha para meterse al tatami
            arrancar_motores(-1.0, -1.0)
            start = time.monotonic()
            while time.monotonic() - start < 0.3:
                if boton_presionado(): return True
                if leer_borde_mejorado() is None: break
            # Avanza al centro
            arrancar_motores(-1.0, 1.0)
            start = time.monotonic()
            while time.monotonic() - start < 0.25:
                if boton_presionado(): return True
                if leer_borde_mejorado() is not None: break

        # Empuje por lado DERECHO: sen4 solo (IO35)
        elif direccion == "DERECHA":
            ib.pixel = (0, 255, 255)  # Cyan = empuje lateral derecho
            # Gira hacia la izquierda para meterse al tatami
            arrancar_motores(1.0, 1.0)
            start = time.monotonic()
            while time.monotonic() - start < 0.3:
                if boton_presionado(): return True
                if leer_borde_mejorado() is None: break
            # Avanza al centro
            arrancar_motores(-1.0, 1.0)
            start = time.monotonic()
            while time.monotonic() - start < 0.25:
                if boton_presionado(): return True
                if leer_borde_mejorado() is not None: break

        # Borde frontal prolongado sin rival → escape lateral al azar
        else:
            ib.pixel = (255, 255, 0)  # Amarillo = atascado al frente
            lado = random.choice([1, -1])
            arrancar_motores(-1.0 * lado, -1.0 * lado)
            start = time.monotonic()
            while time.monotonic() - start < 0.35:
                if boton_presionado(): return True
                if leer_borde_mejorado() is None: break
            arrancar_motores(-1.0, 1.0)
            start = time.monotonic()
            while time.monotonic() - start < 0.2:
                if boton_presionado(): return True
                if leer_borde_mejorado() is not None: break

        _tiempo_inicio_borde = None
        frenar()
        return False

    # Escape normal
    # Giro sobre el eje para alejarse del borde
    arrancar_motores(1.0, -1.0)
    start = time.monotonic()
    while time.monotonic() - start < 0.15:
        if boton_presionado(): return True
        if leer_borde_mejorado() is not None: break

    frenar()

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

    frenar()
    return False


def buscar_y_atacar():
    global _direccion_giro_busqueda, _tiempo_ultimo_cambio, _barridos_sin_rival, _rival_perdido_count

    if boton_presionado(): return True

    if rival_detectado():
        _rival_perdido_count = 0
        ib.pixel = (0, 255, 0)
        # Ataque directo a máxima velocidad
        arrancar_motores(-1.0, 1.0)
        start = time.monotonic()
        while time.monotonic() - start < 0.05:  # más tiempo de empuje antes de re-evaluar
            if boton_presionado(): return True
            if leer_borde_mejorado() is not None: return False

    else:
        _rival_perdido_count += 1

        if _rival_perdido_count < MAX_PERDIDO:
            # Sigue en la última dirección del rival
            ib.pixel = (0, 0, 255)
            arrancar_motores(-1.0, 1.0)
            start = time.monotonic()
            while time.monotonic() - start < 0.05:
                if boton_presionado(): return True
                if leer_borde_mejorado() is not None: return False
            return False

        # Búsqueda: giro en arco amplio
        ib.pixel = (255, 165, 0)

        ahora = time.monotonic()
        if ahora - _tiempo_ultimo_cambio > INTERVALO_CAMBIO_GIRO:
            _barridos_sin_rival += 1
            if _barridos_sin_rival % 3 == 0:
                _direccion_giro_busqueda *= -1
            _tiempo_ultimo_cambio = ahora

        # Motor invertido considerado — mismo signo = giro correcto para tu hardware
        arrancar_motores(-1.0 * _direccion_giro_busqueda, -1.0 * _direccion_giro_busqueda)
        start = time.monotonic()
        # 0.25s = ~90° de giro real; si querés 180° usá 0.5
        while time.monotonic() - start < 0.25:
            if boton_presionado(): return True
            if rival_detectado():
                _rival_perdido_count = 0
                return False
            if leer_borde_mejorado() is not None: return False

    return False


def inicio_ronda(ronda):
    sleep(0.2)  # Pausa reglamentaria

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

    frenar()
    ib.pixel = (0, 0, 0)


# ============================================================
# EJECUCIÓN PRINCIPAL
# ============================================================

frenar()
ronda = 1

while ronda <= 3:

    print(f"=== RONDA {ronda} ===")
    for _ in range(ronda):
        ib.pixel = COLORES_RONDA[ronda]
        sleep(0.3)
        ib.pixel = (0, 0, 0)
        sleep(0.3)

    print(f"Presiona BOOT para iniciar ronda {ronda}.")
    ib.pixel = COLORES_RONDA[ronda]
    while True:
        event = keys.events.get()
        if event and event.released:
            break
    ib.pixel = (0, 0, 0)
    sleep(0.3)

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
            _tiempo_inicio_borde = None  # Salió del borde, resetear contador
            if buscar_y_atacar():
                frenar()
                print(f"Ronda {ronda} terminada.")
                break

    ronda += 1
    sleep(0.5)  # Separación entre rondas

frenar()
ib.pixel = (200, 200, 200)
print("Partida completa.")
