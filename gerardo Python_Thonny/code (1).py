# ==========================================
# SUMOBOT – MODO COMBATE
# Universidad CENFOTEC
# ==========================================

import board
import keypad
import time
from ideaboard import IdeaBoard
from hcsr04 import HCSR04

ib = IdeaBoard()

ir2 = ib.AnalogIn(board.IO39)   # sen2 - frontal derecho
ir3 = ib.AnalogIn(board.IO34)   # sen3 - trasero izquierdo
ir4 = ib.AnalogIn(board.IO35)   # sen4 - trasero derecho

sonar = HCSR04(board.IO26, board.IO25)

keys = keypad.Keys((board.IO0,), value_when_pressed=False, pull=True)

BLANCO_MAX = 5000
NEGRO_MAX = {2: 45000, 3: 30000, 4: 15000}
UMBRAL = {2: 0, 3: 0, 4: 0}

DURACION_CALIB = 2.0

VEL_BUSQUEDA = 1.0
VEL_ATAQUE   = 1.0
VEL_EVASION  = 1.0
DISTANCIA_ATAQUE = 30

T_GIRO_90  = 0.4
T_GIRO_180 = 0.8

PAUSA_INICIAL  = "PAUSA_INICIAL"
CALIBRANDO     = "CALIBRANDO"
ESPERA_RONDA   = "ESPERA_RONDA"
INICIO_RONDA   = "INICIO_RONDA"
COMBATE        = "COMBATE"

PAUSA_ARRANQUE = 0.5

estado = PAUSA_INICIAL
ronda  = 1

pausa_fin    = time.monotonic() + PAUSA_ARRANQUE
calib_fin    = 0.0
calib_min    = {}
calib_max    = {}
maniobra_fin = 0.0


def _clamp(v):
    if v > 1:  return 1
    if v < -1: return -1
    return v


def motores(m1, m2):
    """Ambos motores soldados con polaridad invertida: se niegan aquí.
    Para AVANZAR  → motores(1, 1)   → throttle (-1, -1)
    Para RETROCEDER → motores(-1, -1) → throttle (1, 1)
    Para GIRAR DER  → motores(1, -1) → throttle (-1, 1)
    Para GIRAR IZQ  → motores(-1, 1) → throttle (1, -1)
    """
    ib.motor_1.throttle = -_clamp(m1)
    ib.motor_2.throttle = -_clamp(m2)


def boton_soltado():
    evento = keys.events.get()
    return bool(evento and evento.released)


print("Pausa inicial de 0.5 s antes de calibrar...")
ib.pixel = (255, 0, 0)

while True:
    ahora = time.monotonic()

    # -------- 1. Pausa de arranque --------
    if estado == PAUSA_INICIAL:
        if ahora >= pausa_fin:
            estado    = CALIBRANDO
            calib_fin = ahora + DURACION_CALIB
            calib_min = {2: NEGRO_MAX[2], 3: NEGRO_MAX[3], 4: NEGRO_MAX[4]}
            calib_max = {2: 0, 3: 0, 4: 0}
            ib.pixel  = (255, 255, 0)
            print("Calibrando el fondo del dojo (no mover el robot)...")

    # -------- 2. Calibración automática --------
    elif estado == CALIBRANDO:
        for s, sensor in ((2, ir2), (3, ir3), (4, ir4)):
            v = sensor.value
            if v < calib_min[s]: calib_min[s] = v
            if v > calib_max[s]: calib_max[s] = v

        if ahora >= calib_fin:
            for s in (2, 3, 4):
                UMBRAL[s] = max((BLANCO_MAX + calib_min[s]) / 2, BLANCO_MAX + 200)
            print("Umbrales calculados:", UMBRAL)
            estado = ESPERA_RONDA
            ronda  = 1

    # -------- 3. Esperar BOOT --------
    elif estado == ESPERA_RONDA:
        if ronda == 1: ib.pixel = (0, 255, 0)
        elif ronda == 2: ib.pixel = (0, 100, 255)
        else: ib.pixel = (180, 0, 255)

        if boton_soltado():
            estado = INICIO_RONDA
            if ronda == 1:
                maniobra_fin = ahora
            elif ronda == 2:
                maniobra_fin = ahora + T_GIRO_90
            else:
                maniobra_fin = ahora + T_GIRO_180
            print("Iniciando combate", ronda)

    # -------- 4. Maniobra de arranque --------
    elif estado == INICIO_RONDA:
        if ronda == 1:
            motores(0, 0)
        else:
            ib.pixel = (255, 140, 0)
            motores(VEL_EVASION, -VEL_EVASION)  # pivote para quedar de frente

        if ahora >= maniobra_fin:
            motores(0, 0)
            estado = COMBATE

    # -------- 5. Combate --------
    else:
        if boton_soltado():
            motores(0, 0)
            ronda  = 1 if ronda == 3 else ronda + 1
            estado = ESPERA_RONDA
            continue

        blanco_frente = ir2.value < UMBRAL[2]
        blanco_atras  = (ir3.value < UMBRAL[3]) or (ir4.value < UMBRAL[4])

        if blanco_frente:
            # Borde al frente → retroceder
            ib.pixel = (255, 100, 0)
            motores(-VEL_EVASION, -VEL_EVASION)

        elif blanco_atras:
            # Borde atrás → avanzar
            ib.pixel = (0, 150, 255)
            motores(VEL_EVASION, VEL_EVASION)

        else:
            # Leer sonar con reintentos para evitar fallos RuntimeError
            dist = 999
            for _ in range(3):
                try:
                    d = sonar.dist_cm()
                    if d is not None and d > 0:
                        dist = d
                        break
                except RuntimeError:
                    pass

            if dist < DISTANCIA_ATAQUE:
                # Rival detectado → avanzar a atacar
                ib.pixel = (255, 0, 255)
                motores(VEL_ATAQUE, VEL_ATAQUE)
            else:
                # Sin rival → girar buscando (pivote sobre el eje)
                ib.pixel = (0, 255, 0)
                motores(VEL_BUSQUEDA, -VEL_BUSQUEDA)
