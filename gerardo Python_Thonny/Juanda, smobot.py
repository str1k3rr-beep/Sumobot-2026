import board
import keypad
from ideaboard import IdeaBoard
from time import sleep, monotonic
from hcsr04 import HCSR04

ib = IdeaBoard()
keys = keypad.Keys((board.IO0,), value_when_pressed=False, pull=True)

sonar = HCSR04(board.IO25, board.IO26)

sen2 = ib.AnalogIn(board.IO39)  # Frontal (unico)
sen3 = ib.AnalogIn(board.IO34)  # Trasero Izquierdo
sen4 = ib.AnalogIn(board.IO35)  # Trasero Derecho
infrarrojos = [sen2, sen3, sen4]

UMBRAL_SEN2 = 21683   # Frontal
UMBRAL_SEN3 = 16253   # Trasero Izquierdo
UMBRAL_SEN4 = 10484   # Trasero Derecho

DIST_MAX_SONAR     = 40
DIST_ATAQUE        = 20
DIST_AVANCE        = 30

TIEMPO_MICRO_GIRO  = 0.09
UMBRAL_CORRECCION  = 6

VEL_ATAQUE         = 1.0
VEL_TRACKING       = 0.90
VEL_CORRECCION_RAP = 0.90
VEL_CORRECCION_LEN = 0.45
VEL_BUSQUEDA       = 0.75

HISTERESIS_CICLOS   = 3
histeresis_contador = 0
ultima_dist_valida  = DIST_MAX_SONAR

DURACION_RAFAGA_ATAQUE   = 0.15
INTERVALO_VERIFICACION   = 0.02
MISSES_PARA_PERDER_RIVAL = 3

busqueda_izquierda = False
ultimo_lado_rival  = "FRENTE"


def detener():
    try:
        ib.motor_1.throttle = 0
        ib.motor_2.throttle = 0
    except Exception:
        pass


def medir_distancia_cm():
    try:
        lecturas = []
        for _ in range(3):
            try:
                d = sonar.dist_cm()
                if d is not None and d <= DIST_MAX_SONAR:
                    lecturas.append(d)
            except Exception:
                pass
        if lecturas:
            return min(lecturas)
        return DIST_MAX_SONAR
    except Exception:
        return DIST_MAX_SONAR


def medir_con_histeresis():
    global histeresis_contador, ultima_dist_valida

    dist = medir_distancia_cm()

    if dist < DIST_MAX_SONAR:
        ultima_dist_valida  = dist
        histeresis_contador = HISTERESIS_CICLOS
        return dist
    elif histeresis_contador > 0:
        histeresis_contador -= 1
        return ultima_dist_valida
    else:
        ultima_dist_valida = DIST_MAX_SONAR
        return DIST_MAX_SONAR


def leer_borde():
    try:
        # Primera lectura
        v2a = sen2.value; v3a = sen3.value; v4a = sen4.value
        # Segunda lectura
        v2b = sen2.value; v3b = sen3.value; v4b = sen4.value

        # Borde = blanco = valor MENOR al umbral (invertido respecto a v5)
        f  = (v2a < UMBRAL_SEN2) and (v2b < UMBRAL_SEN2)   # Frontal
        rl = (v3a < UMBRAL_SEN3) and (v3b < UMBRAL_SEN3)   # Trasero Izq
        rr = (v4a < UMBRAL_SEN4) and (v4b < UMBRAL_SEN4)   # Trasero Der

        if f:               return "FRENTE"
        if rl and rr:       return "TRASERO"
        if rl:              return "IZQUIERDA"
        if rr:              return "DERECHA"
        return None

    except Exception:
        return None


MODO_DIAGNOSTICO = False   # <-- ponlo True para ver valores raw

def diagnostico_sensores():
    print("=== DIAGNOSTICO IR (10 segundos) ===")
    print("Mueve el robot sobre NEGRO y BLANCO para ver los valores.")
    print("sen2=frontal  sen3=trasIzq  sen4=trasDer")
    print("")
    t = monotonic()
    while monotonic() - t < 1.0:
        v2 = sen2.value
        v3 = sen3.value
        v4 = sen4.value
        det2 = "B" if v2 < UMBRAL_SEN2 else "N"
        det3 = "B" if v3 < UMBRAL_SEN3 else "N"
        det4 = "B" if v4 < UMBRAL_SEN4 else "N"
        print("sen2=" + str(v2) + "(" + det2 + ")  "
              "sen3=" + str(v3) + "(" + det3 + ")  "
              "sen4=" + str(v4) + "(" + det4 + ")")
        sleep(0.3)
    print("=== FIN DIAGNOSTICO ===")
    print("")


MUESTRAS_CAL = 15

def leer_promedio():
    s2, s3, s4 = 0, 0, 0
    for _ in range(MUESTRAS_CAL):
        s2 += sen2.value
        s3 += sen3.value
        s4 += sen4.value
        sleep(0.03)
    return s2 / MUESTRAS_CAL, s3 / MUESTRAS_CAL, s4 / MUESTRAS_CAL

def esperar_boton(color):
    ib.pixel = color
    while True:
        event = keys.events.get()
        if event and event.released:
            ib.pixel = (0, 0, 0)
            sleep(0.3)
            return

def calibracion_verificacion():
    if MODO_DIAGNOSTICO:
        diagnostico_sensores()

    print("=== CALIBRACION ===")
    print("PASO 1: Pon los sensores sobre NEGRO y presiona BOOT.")
    esperar_boton((255, 0, 0))
    n2, n3, n4 = leer_promedio()
    print("  Negro -> sen2=" + str(round(n2)) + "  sen3=" + str(round(n3)) + "  sen4=" + str(round(n4)))

    print("PASO 2: Pon los sensores sobre BLANCO y presiona BOOT.")
    esperar_boton((255, 255, 255))
    b2, b3, b4 = leer_promedio()
    print("  Blanco -> sen2=" + str(round(b2)) + "  sen3=" + str(round(b3)) + "  sen4=" + str(round(b4)))

    # Umbral = punto medio entre blanco y negro
    global UMBRAL_SEN2, UMBRAL_SEN3, UMBRAL_SEN4
    UMBRAL_SEN2 = (n2 + b2) / 2
    UMBRAL_SEN3 = (n3 + b3) / 2
    UMBRAL_SEN4 = (n4 + b4) / 2

    print("  Umbrales calculados:")
    print("    UMBRAL_SEN2=" + str(round(UMBRAL_SEN2)))
    print("    UMBRAL_SEN3=" + str(round(UMBRAL_SEN3)))
    print("    UMBRAL_SEN4=" + str(round(UMBRAL_SEN4)))
    print("  (Copia estos valores al codigo para saltarte la calibracion)")
    print("")
    print("Presiona BOOT para iniciar combate.")
    esperar_boton((0, 255, 0))


def maniobra_escape(direccion):
    try:
        ib.pixel = (255, 0, 255)

        if direccion == "TRASERO":
            # Arrastrado hacia atras: avanzar fuerte y girar
            ib.motor_1.throttle = -VEL_ATAQUE
            ib.motor_2.throttle = -VEL_ATAQUE
            sleep(0.10)
            if ultimo_lado_rival == "IZQUIERDA":
                ib.motor_1.throttle =  VEL_ATAQUE
                ib.motor_2.throttle = -VEL_ATAQUE
            else:
                ib.motor_1.throttle = -VEL_ATAQUE
                ib.motor_2.throttle =  VEL_ATAQUE
            sleep(0.70)
            detener()

        elif direccion == "FRENTE":
            # Borde adelante: retroceder y girar hacia el rival
            ib.motor_1.throttle = 1.0
            ib.motor_2.throttle = 1.0
            sleep(0.10)
            detener()
            if ultimo_lado_rival == "IZQUIERDA":
                ib.motor_1.throttle =  VEL_ATAQUE
                ib.motor_2.throttle = -VEL_ATAQUE
            else:
                ib.motor_1.throttle = -VEL_ATAQUE
                ib.motor_2.throttle =  VEL_ATAQUE
            sleep(0.90)
            detener()

        elif direccion == "IZQUIERDA":
            ib.motor_1.throttle = 1.0
            ib.motor_2.throttle = 1.0
            sleep(0.12)
            ib.motor_1.throttle = -VEL_ATAQUE
            ib.motor_2.throttle =  VEL_ATAQUE
            sleep(0.40)
            detener()

        elif direccion == "DERECHA":
            ib.motor_1.throttle = 1.0
            ib.motor_2.throttle = 1.0
            sleep(0.12)
            ib.motor_1.throttle =  VEL_ATAQUE
            ib.motor_2.throttle = -VEL_ATAQUE
            sleep(0.40)
            detener()

        detener()

    except Exception:
        detener()


def barrer_y_localizar():
    try:
        resultados = {}

        d1 = medir_distancia_cm()
        d2 = medir_distancia_cm()
        resultados["FRENTE"] = min(d1, d2)

        ib.motor_1.throttle =  0.6
        ib.motor_2.throttle = -0.6
        sleep(TIEMPO_MICRO_GIRO)
        detener()
        d1 = medir_distancia_cm()
        d2 = medir_distancia_cm()
        resultados["IZQUIERDA"] = min(d1, d2)

        ib.motor_1.throttle = -0.6
        ib.motor_2.throttle =  0.6
        sleep(TIEMPO_MICRO_GIRO)
        detener()

        ib.motor_1.throttle = -0.6
        ib.motor_2.throttle =  0.6
        sleep(TIEMPO_MICRO_GIRO)
        detener()
        d1 = medir_distancia_cm()
        d2 = medir_distancia_cm()
        resultados["DERECHA"] = min(d1, d2)

        ib.motor_1.throttle =  0.6
        ib.motor_2.throttle = -0.6
        sleep(TIEMPO_MICRO_GIRO)
        detener()

        lado_optimo = min(resultados, key=resultados.get)
        dist_optima = resultados[lado_optimo]
        return dist_optima, lado_optimo

    except Exception:
        detener()
        return DIST_MAX_SONAR, "FRENTE"


def corregir_rumbo(lado):
    try:
        if lado == "IZQUIERDA":
            ib.motor_1.throttle =  VEL_CORRECCION_LEN
            ib.motor_2.throttle = -VEL_CORRECCION_RAP
        elif lado == "DERECHA":
            ib.motor_1.throttle = -VEL_CORRECCION_RAP
            ib.motor_2.throttle =  VEL_CORRECCION_LEN
        else:
            ib.motor_1.throttle = -VEL_TRACKING
            ib.motor_2.throttle = -VEL_TRACKING
        sleep(0.07)

    except Exception:
        detener()


def ejecutar_rafaga_ataque():
    fallos_consecutivos = 0
    t_inicio = monotonic()

    while monotonic() - t_inicio < DURACION_RAFAGA_ATAQUE:
        ib.motor_1.throttle = -VEL_ATAQUE
        ib.motor_2.throttle = -VEL_ATAQUE

        borde = leer_borde()
        if borde is not None:
            maniobra_escape(borde)
            return "escape"

        d = medir_distancia_cm()
        if d >= DIST_MAX_SONAR:
            fallos_consecutivos += 1
            if fallos_consecutivos >= MISSES_PARA_PERDER_RIVAL:
                detener()
                return "perdido"
        else:
            fallos_consecutivos = 0

        sleep(INTERVALO_VERIFICACION)

    return "continua"


def comportamiento_ofensivo():
    global ultimo_lado_rival, busqueda_izquierda

    try:
        distancia_frontal = medir_con_histeresis()

        # ── FASE 1: ATAQUE ────────────────────────────
        if distancia_frontal < DIST_ATAQUE:
            ib.pixel = (255, 0, 0)
            ejecutar_rafaga_ataque()

        # ── FASE 2: TRACKING ACTIVO ───────────────────
        elif distancia_frontal < DIST_AVANCE:
            ib.pixel = (255, 165, 0)

            dist_optima, lado_optimo = barrer_y_localizar()

            borde = leer_borde()
            if borde is not None:
                maniobra_escape(borde)
                return

            if lado_optimo != "FRENTE" and abs(dist_optima - distancia_frontal) > UMBRAL_CORRECCION:
                ultimo_lado_rival = lado_optimo
                corregir_rumbo(lado_optimo)
            else:
                ib.motor_1.throttle = -VEL_ATAQUE
                ib.motor_2.throttle = -VEL_ATAQUE
                sleep(0.04)

        # ── FASE 3: BUSQUEDA ──────────────────────────
        else:
            ib.pixel = (0, 0, 255)

            if ultimo_lado_rival == "IZQUIERDA":
                ib.motor_1.throttle =  VEL_BUSQUEDA
                ib.motor_2.throttle = -VEL_BUSQUEDA
            elif ultimo_lado_rival == "DERECHA":
                ib.motor_1.throttle = -VEL_BUSQUEDA
                ib.motor_2.throttle =  VEL_BUSQUEDA
            else:
                if busqueda_izquierda:
                    ib.motor_1.throttle =  VEL_BUSQUEDA
                    ib.motor_2.throttle = -VEL_BUSQUEDA
                else:
                    ib.motor_1.throttle = -VEL_BUSQUEDA
                    ib.motor_2.throttle =  VEL_BUSQUEDA
                busqueda_izquierda = not busqueda_izquierda

            sleep(0.0010)

    except Exception:
        detener()


detener()
calibracion_verificacion()

while True:
    try:
        borde = leer_borde()
        if borde is not None:
            maniobra_escape(borde)
        else:
            comportamiento_ofensivo()

    except Exception:
        detener()
        sleep(0.01)

