import board
import keypad
import math
from ideaboard import IdeaBoard
from time import sleep
import time
import digitalio
import random
from adafruit_lsm6ds.lsm6ds3trc import LSM6DS3TRC

ib = IdeaBoard()
sleep(1.0)  # Necesario para que el hardware arranque

i2c = board.I2C()
gyro_sensor = LSM6DS3TRC(i2c, 0x6b)
RAD_A_GRADOS = 180 / math.pi
drift = 0

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

GRADOS_RONDA_2 = 180
GRADOS_RONDA_3 = 180

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


def calibrar_drift(segundos=2):
    suma = 0
    muestras = 0
    t0 = time.monotonic()
    while time.monotonic() - t0 < segundos:
        data = gyro_sensor.gyro[2]
        if abs(data) < 0.008:
            suma += data
            muestras += 1
        time.sleep(0.005)
    return suma / muestras if muestras else 0


def girar_grados(grados, velocidad=0.25):
    sentido = 1 if grados > 0 else -1
    grados = abs(grados) - 2
    acumulado = 0
    t_anterior = time.monotonic()

    arrancar_motores(velocidad * sentido, -velocidad * sentido)

    while acumulado < grados:
        t_actual = time.monotonic()
        dt = t_actual - t_anterior
        t_anterior = t_actual

        vel_angular = gyro_sensor.gyro[2] - drift
        delta_grados = vel_angular * dt * RAD_A_GRADOS
        acumulado += abs(delta_grados)

        if grados - acumulado <= grados / 2:
            arrancar_motores(0.15 * sentido, -0.15 * sentido)

        time.sleep(0.005)

    frenar()


def straight_move(velocidad, duracion, Kp=0.15, Ki=0.8, Kd=0.05):
    t0 = time.monotonic()
    velocidad_base = abs(velocidad)
    direccion = 1 if velocidad > 0 else -1
    error_anterior = 0
    error_integral = 0
    max_correccion = 0.3

    while time.monotonic() - t0 < duracion:
        dt = 1

        error = gyro_sensor.gyro[2] - drift
        error_integral += error * dt
        error_derivativo = (error - error_anterior) / dt

        correccion = Kp * error + Ki * error_integral + Kd * error_derivativo
        correccion = max(-max_correccion, min(max_correccion, correccion))

        v1 = velocidad_base * direccion + correccion
        v2 = velocidad_base * direccion - correccion
        v1 = max(-1, min(1, v1))
        v2 = max(-1, min(1, v2))

        arrancar_motores(v1, v2)
        error_anterior = error
        time.sleep(0.01)

    frenar()


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
# Motor 1 está físicamente invertido → se niega siempre aquí
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
            sleep(0.5)  # Necesario para evitar doble lectura de botón
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

    print("Iniciando...")
    sleep(0.3)  # Pausa reglamentaria mínima


# Lectura con doble confirmación — evita falsos positivos por vibración/reflejos durante ataque
def _leer_sensores():
    return [sen.value < umbrales[i] for i, sen in enumerate(infrarrojos)]

def leer_borde_mejorado():
    detectados = _leer_sensores()
    # Si ninguno detecta blanco, no hay borde (caso más común — salida rápida)
    if not any(detectados):
        return None
    # Confirmación: segunda lectura inmediata para filtrar ruido/vibración
    detectados2 = _leer_sensores()
    # Solo se cuenta si AMBAS lecturas coinciden en ese sensor
    detectados = [detectados[i] and detectados2[i] for i in range(4)]
    if not any(detectados):
        return None
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
        while time.monotonic() - start < 0.35:
            if boton_presionado(): return True
        # Paso 2: girar izquierda para encarar al rival
        arrancar_motores(-1.0, -1.0)
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

    ahora = time.monotonic()

    # Registrar cuándo empezó a ver el borde
    if _tiempo_inicio_borde is None:
        _tiempo_inicio_borde = ahora

    tiempo_en_borde = ahora - _tiempo_inicio_borde

    # Si lleva más de 0.4s en borde y no hay rival → está atascado
    if tiempo_en_borde > 0.4 and not rival_detectado():

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
        girar_grados(GRADOS_RONDA_2)

    elif ronda == 3:
        ib.pixel = COLORES_RONDA[3]
        girar_grados(GRADOS_RONDA_3)

    frenar()
    ib.pixel = (0, 0, 0)


# ============================================================
# EJECUCIÓN PRINCIPAL
# ============================================================

frenar()
drift = calibrar_drift(2)
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
