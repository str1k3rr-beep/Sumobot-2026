# Universidad CENFOTEC - SumoBot (CenfoBot)
# Código de combate: calibración automática + inicio por combate + evasión/ataque
#
# Basado en la librería "ideaboard" y "hcsr04" del repositorio oficial:
# https://github.com/Universidad-Cenfotec/Sumobot
#
# FLUJO DEL PROGRAMA:
#   1) Al encender, el robot queda esperando que se presione el botón BOOT (IO0).
#   2) Al presionarlo, calibra automáticamente los 4 sensores infrarrojos.
#   3) Terminada la calibración, vuelve a esperar BOOT para iniciar el Combate 1.
#   4) Cada combate tiene una maniobra de inicio distinta (cara a cara / lado / espalda),
#      y luego corre el ciclo de combate: evade bordes blancos (prioridad máxima) y,
#      mientras esté sobre negro, busca y ataca al rival.
#   5) Al terminar el Combate 3, el NeoPixel queda parpadeando en blanco.
#
# Para usarlo: renombra (o copia el contenido) a "code.py" en el IdeaBoard usando Thonny.

import board
import random
from time import sleep, monotonic
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

# Umbrales de calibración (se sobreescriben al calibrar). Valores de respaldo
# tomados de los ejemplos del repositorio en caso de que no se calibre.
UMBRALES = [2950, 2950, 2950, 2950]

# ----------------------------------------------------------------------------
# MOVIMIENTOS BÁSICOS
# ----------------------------------------------------------------------------
def stop():
    ib.pixel = (0, 0, 0)
    ib.motor_1.throttle = 0
    ib.motor_2.throttle = 0


def forward(t, speed):
    ib.pixel = (0, 255, 0)
    ib.motor_1.throttle = speed
    ib.motor_2.throttle = speed
    sleep(t)


def backward(t, speed):
    ib.pixel = (150, 255, 0)
    ib.motor_1.throttle = -speed
    ib.motor_2.throttle = -speed
    sleep(t)


def left(t, speed):
    ib.pixel = (50, 55, 100)
    ib.motor_1.throttle = -speed
    ib.motor_2.throttle = speed
    sleep(t)


def right(t, speed):
    ib.pixel = (50, 55, 100)
    ib.motor_1.throttle = speed
    ib.motor_2.throttle = -speed
    sleep(t)


def randomTurn(t, speed):
    # Gira al azar hacia la izquierda o la derecha
    if random.choice([-1, 1]) > 0:
        right(t, speed)
    else:
        left(t, speed)


# ----------------------------------------------------------------------------
# ESPERA DE BOTÓN BOOT (usado entre cada etapa: calibración y cada combate)
# ----------------------------------------------------------------------------
def esperar_boton(color_espera):
    """Detiene el robot, enciende el NeoPixel con 'color_espera' y bloquea
    el programa hasta que se presione (y suelte) el botón BOOT."""
    stop()
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
    # True si CUALQUIER sensor está viendo el borde blanco
    return 0 in bits


# ----------------------------------------------------------------------------
# CALIBRACIÓN AUTOMÁTICA DE LOS SENSORES IR (al presionar BOOT)
# ----------------------------------------------------------------------------
def calibrar_infrarrojos(t_calibracion=4.0, vel_giro=0.35):
    """
    El robot oscila suavemente sobre su propio eje durante 't_calibracion'
    segundos, registrando el valor mínimo y máximo de cada sensor IR.
    El umbral de cada sensor queda en el punto medio entre "negro" y "blanco".

    Si algún sensor nunca detecta suficiente contraste (porque el robot no
    pasó sobre el borde blanco durante el giro), se usa un umbral de
    respaldo = 1.3 veces su valor de "negro", para no dejarlo sin calibrar.

    NOTA: para una calibración más precisa, coloca el robot cerca del borde
    del dojo antes de presionar BOOT, así los sensores alcanzan a ver tanto
    el negro como el blanco durante la oscilación.
    """
    ib.pixel = (255, 140, 0)  # naranja = calibrando

    minimos = [None, None, None, None]
    maximos = [None, None, None, None]

    inicio = monotonic()
    sentido = 1
    while monotonic() - inicio < t_calibracion:
        ib.motor_1.throttle = -sentido * vel_giro
        ib.motor_2.throttle = sentido * vel_giro

        t0 = monotonic()
        while monotonic() - t0 < 0.25 and monotonic() - inicio < t_calibracion:
            crudos = leer_crudo()
            for i in range(4):
                if minimos[i] is None or crudos[i] < minimos[i]:
                    minimos[i] = crudos[i]
                if maximos[i] is None or crudos[i] > maximos[i]:
                    maximos[i] = crudos[i]
            sleep(0.02)

        sentido *= -1  # cambia de sentido (oscila como un péndulo)

    stop()

    umbrales = []
    for i in range(4):
        rango = maximos[i] - minimos[i]
        if rango < 1500:
            # No se detectó suficiente contraste: respaldo automático
            umbrales.append(minimos[i] * 1.3)
        else:
            umbrales.append((minimos[i] + maximos[i]) / 2)

    print("Calibración IR completa. Umbrales:", umbrales)

    # Parpadeo verde = calibración exitosa
    for _ in range(3):
        ib.pixel = (0, 255, 0)
        sleep(0.15)
        ib.pixel = (0, 0, 0)
        sleep(0.15)

    return umbrales


# ----------------------------------------------------------------------------
# SENSOR ULTRASÓNICO
# ----------------------------------------------------------------------------
def medir_distancia():
    stop()
    d = sonar.dist_cm()
    sleep(0.05)
    return d


# ----------------------------------------------------------------------------
# EVASIÓN DE BORDE BLANCO -> PRIORIDAD MÁXIMA (volver al negro / al dojo)
# ----------------------------------------------------------------------------
def evadir(umbrales):
    """
    bits = [FI, FD, TI, TD]  (1 = negro, 0 = blanco)
    Retrocede o avanza según cuál sensor detectó blanco, y gira para
    reorientarse hacia el centro (negro) del dojo.
    """
    fi, fd, ti, td = leer_sensores(umbrales)

    if fi == 0 and fd == 0:
        backward(0.35, 0.7)
        randomTurn(0.3, 0.6)
    elif fi == 0:
        backward(0.3, 0.7)
        right(0.3, 0.6)
    elif fd == 0:
        backward(0.3, 0.7)
        left(0.3, 0.6)
    elif ti == 0 and td == 0:
        forward(0.35, 0.7)
        randomTurn(0.3, 0.6)
    elif ti == 0:
        forward(0.3, 0.7)
        left(0.3, 0.6)
    elif td == 0:
        forward(0.3, 0.7)
        right(0.3, 0.6)

    stop()


# ----------------------------------------------------------------------------
# BÚSQUEDA Y ATAQUE DEL RIVAL -> SEGUNDA PRIORIDAD (solo si está sobre negro)
# ----------------------------------------------------------------------------
def buscar_rival(umbrales, max_vueltas=40, dist_deteccion=30, vel_busqueda=0.25):
    """Gira buscando al rival con el sensor ultrasónico.
    Se detiene si lo encuentra o si detecta el borde (deja que evadir()
    se encargue de inmediato)."""
    for _ in range(max_vueltas):
        if hay_blanco(leer_sensores(umbrales)):
            return "borde"
        right(0.15, vel_busqueda)
        d = medir_distancia()
        if d > 0 and d < dist_deteccion:
            return "encontrado"
    return "no_encontrado"


def atacar(umbrales, vel=1.0, dist_max=30):
    """Avanza hacia el rival mientras el ultrasónico lo siga viendo cerca.
    Se detiene de inmediato si pisa blanco (prioridad del dojo) o si el
    rival deja de detectarse (porque lo sacó o escapó)."""
    while True:
        if hay_blanco(leer_sensores(umbrales)):
            return
        d = medir_distancia()
        if d <= 0 or d > dist_max:
            return
        forward(0.15, vel)
    stop()


# ----------------------------------------------------------------------------
# INICIO PERSONALIZADO POR COMBATE (según reglamento: cada combate arranca
# con una disposición distinta entre los robots)
# ----------------------------------------------------------------------------
def inicio_combate_1():
    # CARA A CARA: el rival ya está justo enfrente -> no hace falta buscar,
    # entra directo al ciclo de ataque/evasión.
    ib.pixel = (255, 0, 255)
    stop()
    sleep(0.3)


def inicio_combate_2():
    # DE LADO (direcciones opuestas): el rival está aprox. a 90°, así que
    # gira un poco antes de empezar a buscar con el ultrasónico.
    ib.pixel = (255, 0, 255)
    right(0.45, 0.5)
    stop()


def inicio_combate_3():
    # ESPALDA CON ESPALDA: el rival quedó detrás -> gira media vuelta
    # antes de empezar a buscar.
    ib.pixel = (255, 0, 255)
    right(0.9, 0.5)
    stop()


INICIOS = [inicio_combate_1, inicio_combate_2, inicio_combate_3]
NOMBRES = ["Combate 1 (cara a cara)", "Combate 2 (de lado)", "Combate 3 (de espaldas)"]


def correr_combate(numero, umbrales, duracion_max=85):
    """Ejecuta un combate completo. Prioridad: 1) no salirse del dojo,
    2) buscar/atacar al rival. duracion_max en segundos (reglamento: 1:30)."""
    print("Iniciando", NOMBRES[numero])
    INICIOS[numero]()

    inicio = monotonic()
    while monotonic() - inicio < duracion_max:
        # PRIORIDAD 1: cuidar el borde del dojo
        if hay_blanco(leer_sensores(umbrales)):
            evadir(umbrales)
            continue

        # PRIORIDAD 2: atacar si el rival está cerca, si no, buscarlo
        d = medir_distancia()
        if d > 0 and d < 30:
            atacar(umbrales)
        else:
            resultado = buscar_rival(umbrales)
            if resultado == "borde":
                evadir(umbrales)

    stop()
    print(NOMBRES[numero], "terminado (tiempo agotado)")


# ----------------------------------------------------------------------------
# PROGRAMA PRINCIPAL
# ----------------------------------------------------------------------------
esperar_boton((0, 0, 80))                  # azul = listo para calibrar
UMBRALES = calibrar_infrarrojos()

for numero_combate in range(3):
    esperar_boton((0, 80, 80))             # cian = listo para iniciar el combate
    correr_combate(numero_combate, UMBRALES)

# Partida terminada (3 combates) -> parpadeo blanco indefinido
while True:
    ib.pixel = (255, 255, 255)
    sleep(0.3)
    ib.pixel = (0, 0, 0)
    sleep(0.3)
