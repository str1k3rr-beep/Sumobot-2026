"""
TEST_ESCAPES_REAL.PY — Prueba de maniobras en movimiento real
=============================================================
Sin calibración, sin rondas. Arranca directo.

USO:
  1. Poné el robot en el tatami sobre negro.
  2. Presioná BOOT → empieza a reaccionar a los sensores.
  3. Empujalo con una caja desde cada lado y observá qué hace.
  4. Presioná BOOT de nuevo para detenerlo en cualquier momento.

LED blanco parpadeando = esperando BOOT para arrancar.
LED verde = viendo negro, todo bien.
LED magenta = detectó borde, ejecutando escape normal.
LED cyan = detectó empuje lateral, ejecutando contraataque.
LED amarillo = atascado en borde frontal sin rival, escape al azar.
"""

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

sen1 = ib.AnalogIn(board.IO36)  # Frontal / Lateral Izquierdo (Índice 0)
sen2 = ib.AnalogIn(board.IO39)  # Frontal / Lateral Derecho   (Índice 1)
sen3 = ib.AnalogIn(board.IO34)  # Apoyo Izquierdo             (Índice 2)
sen4 = ib.AnalogIn(board.IO35)  # Apoyo Derecho               (Índice 3)

infrarrojos = [sen1, sen2, sen3, sen4]

# Umbrales fijos — ajustá estos valores según tu tatami
# Si los sensores no reaccionan bien, leé los valores crudos primero
# con el bloque de calibración rápida que está al final de este archivo
UMBRAL = 3800  # valor típico entre negro (~20000) y blanco (~50000)
umbrales = [UMBRAL, UMBRAL, UMBRAL, UMBRAL]

_m1 = ib.motor_1
_m2 = ib.motor_2

_tiempo_inicio_borde = None


def arrancar_motores(m1, m2):
    _m1.throttle = m1
    _m2.throttle = m2


def frenar():
    _m1.throttle = 0
    _m2.throttle = 0


def boton_presionado():
    event = keys.events.get()
    return bool(event and event.released)


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

    # Empuje lateral inmediato — reacciona sin esperar 0.4s
    if direccion == "EMPUJE_IZQUIERDA":
        # Lado derecho del robot está en el borde (sen2 + sen4 detectan blanco)
        # Secuencia fija: avanzar → girar derecha (encarar rival) → avanzar
        ib.pixel = (0, 255, 255)
        # Paso 1: avanzar para resistir el empuje
        arrancar_motores(-1.0, 1.0)
        start = time.monotonic()
        while time.monotonic() - start < 0.35:
            if boton_presionado(): return True
        # Paso 2: girar derecha para encarar al rival
        arrancar_motores(1.0, 1.0)
        start = time.monotonic()
        while time.monotonic() - start < 0.35:
            if boton_presionado(): return True
        # Paso 3: avanzar a atacar
        arrancar_motores(-1.0, 1.0)
        start = time.monotonic()
        while time.monotonic() - start < 0.3:
            if boton_presionado(): return True
        _tiempo_inicio_borde = None
        frenar()
        return False

    if direccion == "EMPUJE_DERECHA":
        # Lado izquierdo del robot está en el borde (sen1 + sen3 detectan blanco)
        # Secuencia fija: avanzar → girar izquierda (encarar rival) → avanzar
        ib.pixel = (0, 255, 255)
        # Paso 1: avanzar para resistir el empuje
        arrancar_motores(-1.0, 1.0)
        start = time.monotonic()
        while time.monotonic() - start < 0.25:
            if boton_presionado(): return True
        # Paso 2: girar izquierda para encarar al rival
        arrancar_motores(-1.0, -1.0)
        start = time.monotonic()
        while time.monotonic() - start < 0.25:
            if boton_presionado(): return True
        # Paso 3: avanzar a atacar
        arrancar_motores(-1.0, 1.0)
        start = time.monotonic()
        while time.monotonic() - start < 0.3:
            if boton_presionado(): return True
        _tiempo_inicio_borde = None
        frenar()
        return False

    ahora = time.monotonic()

    # Registrar cuándo empezó a ver el borde
    if _tiempo_inicio_borde is None:
        _tiempo_inicio_borde = ahora

    tiempo_en_borde = ahora - _tiempo_inicio_borde

    # Si lleva más de 0.4s en borde y no hay rival → está atascado
    if tiempo_en_borde > 0.04 :

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
        # Ataque directo a máxima velocidad — solo aborta si el borde se confirma dos veces
        arrancar_motores(-1.0, 1.0)
        start = time.monotonic()
        while time.monotonic() - start < 0.15:  # ventana de ataque más larga
            if boton_presionado(): return True
            b1 = leer_borde_mejorado()  # ya tiene doble confirmación interna
            if b1 is not None: return False

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

# ── Calibración rápida de umbrales ───────────────────────────────────────────
# Descomentar este bloque si los sensores no reaccionan bien,
# ejecutarlo una vez para ver los valores crudos y ajustar UMBRAL arriba.
#
# print("Valores crudos de sensores (BOOT para salir):")
# while not boton_presionado():
#     vals = [sen.value for sen in infrarrojos]
#     print(f"  S1={vals[0]}  S2={vals[1]}  S3={vals[2]}  S4={vals[3]}")
#     sleep(0.2)


# ── Arranque ─────────────────────────────────────────────────────────────────
print("TEST ESCAPES REAL — Presioná BOOT para arrancar.")
while not boton_presionado():
    ib.pixel = (80, 80, 80)
    sleep(0.3)
    ib.pixel = (0, 0, 0)
    sleep(0.3)

print("Arrancando loop de escapes. BOOT para detener.")

while True:
    if boton_presionado():
        frenar()
        ib.pixel = (0, 0, 0)
        print("Detenido.")
        break

    borde = leer_borde_mejorado()
    if borde is not None:
        if maniobra_escape(borde):
            frenar()
            ib.pixel = (0, 0, 0)
            print("Detenido.")
            break
    else:
        _tiempo_inicio_borde = None
        ib.pixel = (0, 60, 0)  # verde tenue = viendo negro, OK
