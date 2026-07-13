# Universidad CENFOTEC - SumoBot (CenfoBot)
# Código de combate: calibración automática + inicio por combate + evasión/ataque
#
# Basado en la librería "ideaboard" y "hcsr04" del repositorio oficial:
# https://github.com/Universidad-Cenfotec/Sumobot
#
# CAMBIOS DE ESTA VERSIÓN:
#   - Una sola primitiva de movimiento: motores(m1, m2). Ya no existen
#     forward/backward/left/right/randomTurn: todo se controla con esa función.
#   - Sin time.sleep() en ningún lado. El tiempo se maneja con time.monotonic(),
#     así el robot NUNCA se queda "congelado": sigue revisando sus sensores
#     en todo momento, incluso mientras ejecuta una maniobra con duración.
#   - Corrección de hardware: los 2 motores quedaron soldados con la polaridad
#     invertida. Se corrige en UN SOLO LUGAR (dentro de motores()), así el
#     resto del código no necesita saber nada sobre el error de soldadura.
#
# FLUJO DEL PROGRAMA:
#   1) Al encender, espera que se presione BOOT (IO0).
#   2) Calibra automáticamente los 4 sensores infrarrojos.
#   3) Vuelve a esperar BOOT para iniciar el Combate 1, luego el 2, luego el 3.
#      Cada combate tiene una maniobra de inicio distinta (cara a cara /
#      lado / espalda) y corre el ciclo de combate (evade bordes con
#      prioridad máxima; mientras esté sobre negro, busca y ataca al rival).
#
# Para usarlo: copia este contenido en "code.py" del IdeaBoard, con Thonny.

import board
from time import monotonic
from ideaboard import IdeaBoard
from hcsr04 import HCSR04
import keypad

# ----------------------------------------------------------------------------
# INICIALIZACIÓN DE HARDWARE
# ----------------------------------------------------------------------------
ib = IdeaBoard()
sonar = HCSR04(board.IO25, board.IO26)  # TRIG=IO25, ECHO=IO26

# Sensores infrarrojos (ver "Conexiones SumoBot.pdf")
sen1 = ib.AnalogIn(board.IO36)  # SENSOR 1 - frontal izquierdo
sen2 = ib.AnalogIn(board.IO39)  # SENSOR 2 - frontal derecho
sen3 = ib.AnalogIn(board.IO34)  # SENSOR 3 - trasero izquierdo
sen4 = ib.AnalogIn(board.IO35)  # SENSOR 4 - trasero derecho
infrarrojos = [sen1, sen2, sen3, sen4]  # orden: [FI, FD, TI, TD]

# Botón BOOT (IO0) - libre una vez que el IdeaBoard ya inició
boton_boot = keypad.Keys((board.IO0,), value_when_pressed=False, pull=True)

# Umbrales de calibración (se sobreescriben al calibrar)
UMBRALES = [2950, 2950, 2950, 2950]

# ----------------------------------------------------------------------------
# MOTORES - ÚNICA PRIMITIVA DE MOVIMIENTO
# ----------------------------------------------------------------------------
def motores(m1, m2):
    """Aplica velocidad a ambos motores (rango -1.0 a 1.0).

    HARDWARE DEFECTUOSO: los 2 motores quedaron soldados con la polaridad
    invertida, así que un throttle "positivo" en realidad los hace girar
    al revés. Se corrige UNA SOLA VEZ aquí, invirtiendo el signo antes de
    mandarlo al hardware. El resto del código puede seguir pensando en
    "positivo = adelante" con total normalidad.
    """
    ib.motor_1.throttle = -m1
    ib.motor_2.throttle = -m2


def detener():
    motores(0, 0)
    ib.pixel = (0, 0, 0)


# ----------------------------------------------------------------------------
# ACCIONES NO BLOQUEANTES (reemplazan a los antiguos forward/backward/etc.
# que usaban sleep). Una "acción" es simplemente: aplicar throttle a los
# motores y recordar EN QUÉ MOMENTO debe considerarse terminada, sin
# detener el resto del programa mientras tanto.
# ----------------------------------------------------------------------------
fin_accion = 0.0  # monotonic() en el que termina la maniobra actual


def accionar(m1, m2, duracion, color=None):
    global fin_accion
    motores(m1, m2)
    if color is not None:
        ib.pixel = color
    fin_accion = monotonic() + duracion


def accion_activa():
    return monotonic() < fin_accion


# ----------------------------------------------------------------------------
# ESPERA DE BOTÓN BOOT (entre calibración y cada combate)
# ----------------------------------------------------------------------------
def esperar_boton(color_espera):
    detener()
    ib.pixel = color_espera
    while True:
        evento = boton_boot.events.get()
        if evento and evento.released:
            return


# ----------------------------------------------------------------------------
# LECTURA DE SENSORES INFRARROJOS
# ----------------------------------------------------------------------------
def leer_crudo():
    return [sen.value for sen in infrarrojos]


def leer_sensores(umbrales):
    # Convención del repositorio: 1 = negro (dojo), 0 = blanco (borde)
    crudos = leer_crudo()
    return [int(crudos[i] < umbrales[i]) for i in range(4)]


def hay_blanco(bits):
    return 0 in bits


# ----------------------------------------------------------------------------
# CALIBRACIÓN AUTOMÁTICA DE LOS SENSORES IR (al presionar BOOT)
# Reescrita sin sleep: usa monotonic() para alternar el giro y para
# muestrear los sensores tan rápido como el CPU lo permita.
# ----------------------------------------------------------------------------
def calibrar_infrarrojos(t_calibracion=4.0, vel_giro=0.35, t_pulso=0.25):
    """
    Oscila sobre su propio eje durante 't_calibracion' segundos,
    registrando el mínimo y máximo de cada sensor IR. El umbral de cada
    sensor queda en el punto medio entre "negro" y "blanco". Si algún
    sensor no detecta suficiente contraste (no pasó sobre blanco), se usa
    un respaldo automático = 1.3 veces su valor de negro.

    NOTA: para mejor precisión, coloca el robot cerca del borde del dojo
    antes de presionar BOOT, así los sensores alcanzan a ver ambos colores.
    """
    minimos = [None, None, None, None]
    maximos = [None, None, None, None]

    inicio = monotonic()
    sentido = 1
    fin_pulso = inicio + t_pulso
    motores(-sentido * vel_giro, sentido * vel_giro)
    ib.pixel = (255, 140, 0)  # naranja = calibrando

    while monotonic() - inicio < t_calibracion:
        ahora = monotonic()

        crudos = leer_crudo()
        for i in range(4):
            if minimos[i] is None or crudos[i] < minimos[i]:
                minimos[i] = crudos[i]
            if maximos[i] is None or crudos[i] > maximos[i]:
                maximos[i] = crudos[i]

        if ahora >= fin_pulso:
            sentido *= -1
            motores(-sentido * vel_giro, sentido * vel_giro)
            fin_pulso = ahora + t_pulso

    detener()

    umbrales = []
    for i in range(4):
        rango = maximos[i] - minimos[i]
        if rango < 1500:
            umbrales.append(minimos[i] * 1.3)  # respaldo: no vio blanco
        else:
            umbrales.append((minimos[i] + maximos[i]) / 2)

    print("Calibración IR completa. Umbrales:", umbrales)

    # Parpadeo verde = éxito (sin sleep: parpadea por tiempo, con monotonic)
    fin_parpadeo = monotonic() + 0.9
    prox_cambio = monotonic()
    encendido = False
    while monotonic() < fin_parpadeo:
        ahora = monotonic()
        if ahora >= prox_cambio:
            encendido = not encendido
            ib.pixel = (0, 255, 0) if encendido else (0, 0, 0)
            prox_cambio = ahora + 0.15
    ib.pixel = (0, 0, 0)

    return umbrales


# ----------------------------------------------------------------------------
# SENSOR ULTRASÓNICO (lectura con límite de frecuencia, sin sleep)
# ----------------------------------------------------------------------------
distancia = -1.0
proxima_medicion = 0.0
INTERVALO_SONAR = 0.08  # segundos mínimos entre lecturas del ultrasónico


def actualizar_distancia():
    global distancia, proxima_medicion
    ahora = monotonic()
    if ahora >= proxima_medicion:
        distancia = sonar.dist_cm()
        proxima_medicion = ahora + INTERVALO_SONAR
    return distancia


# ----------------------------------------------------------------------------
# EVASIÓN DE BORDE BLANCO -> PRIORIDAD MÁXIMA
# Cada caso es UNA sola maniobra (un solo motores()) con duración propia,
# en vez de encadenar "retrocede" + "gira" como antes.
# bits = [FI, FD, TI, TD]  (1 = negro, 0 = blanco)
# ----------------------------------------------------------------------------
def evadir(bits):
    fi, fd, ti, td = bits
    rojo = (255, 0, 0)

    if fi == 0 and fd == 0:
        accionar(-0.7, -0.7, 0.35, rojo)          # retrocede recto
    elif fi == 0:
        accionar(-0.85, -0.25, 0.4, rojo)         # retrocede girando lejos del FI
    elif fd == 0:
        accionar(-0.25, -0.85, 0.4, rojo)         # retrocede girando lejos del FD
    elif ti == 0 and td == 0:
        accionar(0.7, 0.7, 0.35, rojo)            # avanza recto
    elif ti == 0:
        accionar(0.25, 0.85, 0.4, rojo)           # avanza girando lejos del TI
    elif td == 0:
        accionar(0.85, 0.25, 0.4, rojo)           # avanza girando lejos del TD


# ----------------------------------------------------------------------------
# BÚSQUEDA Y ATAQUE -> SEGUNDA PRIORIDAD (solo si está completamente sobre
# negro). Son estados continuos: un solo motores() al entrar al estado,
# y el loop principal decide cuándo cambiar de estado.
# ----------------------------------------------------------------------------
def iniciar_busqueda():
    motores(0.25, -0.25)  # gira en su propio eje buscando al rival
    ib.pixel = (0, 0, 80)


def iniciar_ataque():
    motores(1.0, 1.0)  # embiste a fondo
    ib.pixel = (255, 0, 0)


# ----------------------------------------------------------------------------
# INICIO PERSONALIZADO POR COMBATE (cada combate arranca con una disposición
# distinta entre los robots, según el reglamento)
# ----------------------------------------------------------------------------
def inicio_combate_1():
    # CARA A CARA: el rival ya está enfrente, solo una pausa breve.
    accionar(0, 0, 0.05, (255, 0, 255))


def inicio_combate_2():
    # DE LADO (direcciones opuestas): el rival está a unos 90°.
    accionar(0.5, -0.5, 0.45, (255, 0, 255))


def inicio_combate_3():
    # ESPALDA CON ESPALDA: el rival quedó detrás, media vuelta.
    accionar(0.5, -0.5, 0.9, (255, 0, 255))


INICIOS = [inicio_combate_1, inicio_combate_2, inicio_combate_3]
NOMBRES = ["Combate 1 (cara a cara)", "Combate 2 (de lado)", "Combate 3 (de espaldas)"]


# ----------------------------------------------------------------------------
# CICLO DE UN COMBATE - 100% no bloqueante. El robot revisa sus sensores en
# cada vuelta del while, así que está "vivo" todo el tiempo (24/7), incluso
# mientras una maniobra de evasión o de inicio sigue en curso.
# ----------------------------------------------------------------------------
def correr_combate(numero, duracion_max=85):
    print("Iniciando", NOMBRES[numero])

    INICIOS[numero]()
    estado = "INICIO"

    inicio_combate = monotonic()
    while monotonic() - inicio_combate < duracion_max:
        bits = leer_sensores(UMBRALES)
        d = actualizar_distancia()

        # PRIORIDAD 1: no salirse del dojo. Interrumpe cualquier otro estado,
        # incluso una maniobra de inicio o de ataque que esté en curso.
        if hay_blanco(bits):
            if estado != "EVADIENDO" or not accion_activa():
                evadir(bits)
                estado = "EVADIENDO"
            continue

        # Si seguimos dentro de una maniobra con duración (evasión o
        # inicio de combate) y no hay blanco, la dejamos terminar.
        if estado in ("EVADIENDO", "INICIO") and accion_activa():
            continue

        # PRIORIDAD 2: atacar si el rival está cerca; si no, buscarlo.
        if 0 < d < 30:
            if estado != "ATACANDO":
                iniciar_ataque()
                estado = "ATACANDO"
        else:
            if estado != "BUSCANDO":
                iniciar_busqueda()
                estado = "BUSCANDO"

    detener()
    print(NOMBRES[numero], "terminado (tiempo agotado)")


# ----------------------------------------------------------------------------
# PROGRAMA PRINCIPAL
# ----------------------------------------------------------------------------
esperar_boton((0, 0, 80))                  # azul = listo para calibrar
UMBRALES = calibrar_infrarrojos()

for numero_combate in range(3):
    esperar_boton((0, 80, 80))             # cian = listo para iniciar el combate
    correr_combate(numero_combate)

# Partida terminada (3 combates) -> parpadeo blanco indefinido, sin sleep
prox_cambio = monotonic()
encendido = False
while True:
    ahora = monotonic()
    if ahora >= prox_cambio:
        encendido = not encendido
        ib.pixel = (255, 255, 255) if encendido else (0, 0, 0)
        prox_cambio = ahora + 0.3
