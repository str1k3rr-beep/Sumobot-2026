# Tomás de Camino Beck / Mod: Evasión Direccional Corregida y Nueva Distribución
# Escuela de Sistemas Inteligentes - Universidad Cenfotec

import board
import keypad
from ideaboard import IdeaBoard
from time import sleep
import time
import random
import digitalio

ib = IdeaBoard()
keys = keypad.Keys((board.IO0,), value_when_pressed=False, pull=True)

# Sensores
sen1 = ib.AnalogIn(board.IO36)
sen2 = ib.AnalogIn(board.IO39)
sen3 = ib.AnalogIn(board.IO34)
sen4 = ib.AnalogIn(board.IO35)

infrarrojos = [sen1, sen2, sen3, sen4]
umbrales = [0, 0, 0, 0]

# Ultrasonido
trigger = digitalio.DigitalInOut(board.IO25)
trigger.direction = digitalio.Direction.OUTPUT
trigger.value = False
echo = digitalio.DigitalInOut(board.IO26)
echo.direction = digitalio.Direction.INPUT

DISTANCIA_RIVAL_CM = 60

# ============================================================
# SISTEMA DE MODOS
# Agrega o quita modos aquí según lo que necesites
# ============================================================
MODOS = ["AGRESIVO", "CONSERVADOR", "EMBOSCADA"]
# Colores LED para saber en qué modo estás de un vistazo
COLORES_MODO = {
    "AGRESIVO":     (255, 0, 0),    # Rojo
    "CONSERVADOR":  (0, 0, 255),    # Azul
    "EMBOSCADA":    (128, 0, 128),  # Morado
}
modo_actual_index = 0  # Empieza siempre en AGRESIVO


def seleccionar_modo():
    """
    Muestra el modo actual con el LED.
    Cada toque de BOOT avanza al siguiente modo.
    Mantén BOOT 1 segundo para confirmar el modo elegido.
    """
    global modo_actual_index

    print("=== SELECCIÓN DE MODO ===")
    print("Toca BOOT para cambiar modo.")
    print("Mantén BOOT 1 segundo para confirmar.")

    tiempo_presionado = None

    while True:
        modo = MODOS[modo_actual_index]
        ib.pixel = COLORES_MODO[modo]
        print(f"Modo actual: {modo}")

        # Esperar evento del botón
        while True:
            event = keys.events.get()

            # Detectar si el botón está siendo mantenido
            if event and not event.pressed:  # pressed=False → fue soltado
                # Fue un toque corto → cambiar modo
                modo_actual_index = (modo_actual_index + 1) % len(MODOS)
                break

            # Revisar si está siendo mantenido (presión larga)
            # keypad no da eventos de "mantenido", así que lo detectamos
            # revisando cuánto tiempo lleva presionado
            import supervisor
            # Alternativa simple: doble parpadeo rápido del LED = confirmar
            # Un toque = siguiente modo
            # Dos toques rápidos = confirmar
            event2 = keys.events.get()
            if event2 and not event2.pressed:
                # Segundo toque = confirmar
                sleep(0.1)
                event3 = keys.events.get()
                if event3 is None:
                    # Solo fue un toque, cambiar modo
                    modo_actual_index = (modo_actual_index + 1) % len(MODOS)
                    break

        # Parpadeo de confirmación: si el LED parpadea 3 veces rápido = confirmado
        # Para confirmar: presiona BOOT dos veces seguidas rápido
        # Lógica más simple abajo:
        break  # Por ahora sale del while, ver versión simplificada abajo


def seleccionar_modo():
    """
    Versión simplificada y confiable:
    - Cada toque corto de BOOT → avanza al siguiente modo
    - El LED muestra el color del modo actual
    - Después de 3 segundos sin tocar BOOT → confirma automáticamente
    """
    global modo_actual_index

    print("=== SELECCIÓN DE MODO ===")
    print("Toca BOOT para cambiar modo.")
    print("Espera 3 segundos para confirmar.")

    ultimo_toque = time.monotonic()

    # Parpadear el modo actual mientras espera
    while True:
        modo = MODOS[modo_actual_index]
        color = COLORES_MODO[modo]

        # Parpadeo suave para indicar que está esperando
        ib.pixel = color
        sleep(0.3)
        ib.pixel = (0, 0, 0)
        sleep(0.2)

        # Revisar si tocaron BOOT
        event = keys.events.get()
        if event and not event.pressed:  # soltaron el botón
            modo_actual_index = (modo_actual_index + 1) % len(MODOS)
            ultimo_toque = time.monotonic()
            print(f"Modo: {MODOS[modo_actual_index]}")

        # Si pasaron 3 segundos sin tocar → confirmar
        if time.monotonic() - ultimo_toque > 3.0:
            modo = MODOS[modo_actual_index]
            print(f"✓ Modo confirmado: {modo}")
            # Parpadeo de confirmación: 3 destellos rápidos
            for _ in range(3):
                ib.pixel = COLORES_MODO[modo]
                sleep(0.1)
                ib.pixel = (0, 0, 0)
                sleep(0.1)
            return modo


# ============================================================
# FUNCIONES BASE
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

    t_fin = time.monotonic()
    return (t_fin - t_inicio) * 34300 / 2


def rival_detectado():
    return medir_distancia_cm() < DISTANCIA_RIVAL_CM


def esperar_boton_y_leer(color_led):
    ib.pixel = color_led
    while True:
        event = keys.events.get()
        if event and not event.pressed:
            lecturas = [sen.value for sen in infrarrojos]
            ib.pixel = (0, 0, 0)
            sleep(0.5)
            return lecturas


def calibracion_por_pasos():
    print("PASO 1: Sensores sobre NEGRO → presiona BOOT.")
    valores_negro = esperar_boton_y_leer((255, 0, 0))

    print("PASO 2: Sensores sobre BLANCO → presiona BOOT.")
    valores_blanco = esperar_boton_y_leer((255, 255, 255))

    for i in range(4):
        umbrales[i] = (valores_negro[i] + valores_blanco[i]) // 2

    print("¡CALIBRACIÓN EXITOSA! Presiona BOOT para combate.")
    esperar_boton_y_leer((0, 255, 0))

    print("Iniciando en 1 segundo...")  # Reducido de 3 a 1 (objetivo del txt)
    for i in range(1, 0, -1):
        ib.pixel = (255, 255, 0)
        sleep(0.5)
        ib.pixel = (0, 0, 0)
        sleep(0.5)


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


def maniobra_escape(direccion):
    ib.pixel = (255, 0, 255)
    ib.motor_1.throttle = 0
    ib.motor_2.throttle = 0
    sleep(0.05)

    start = time.monotonic()
    while time.monotonic() - start < 0.15:
        if leer_borde_mejorado() is not None:
            break
        ib.motor_1.throttle = 1.0
        ib.motor_2.throttle = -1.0
        sleep(0.01)

    ib.motor_1.throttle = 0
    ib.motor_2.throttle = 0
    sleep(0.05)

    if direccion in ("FRENTE", "FRENTE_IZQ"):
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

    else:
        ib.pixel = (0, 0, 255)
        ib.motor_1.throttle = -1.0
        ib.motor_2.throttle = 1.0
        sleep(0.02)

    ib.motor_1.throttle = 0
    ib.motor_2.throttle = 0
    sleep(0.005)


# ============================================================
# MODOS DE COMBATE
# ============================================================

_direccion_giro_busqueda = 1
_tiempo_ultimo_cambio = time.monotonic()
_barridos_sin_rival = 0
_rival_perdido_count = 0
MAX_PERDIDO = 3
INTERVALO_CAMBIO_GIRO = 0.2


def modo_agresivo():
    """Ataca directo, sin dudar. Busca al rival girando rápido."""
    global _direccion_giro_busqueda, _tiempo_ultimo_cambio, _barridos_sin_rival, _rival_perdido_count

    if rival_detectado():
        _rival_perdido_count = 0
        ib.pixel = (255, 0, 0)      # Rojo = atacando
        ib.motor_1.throttle = -1.0
        ib.motor_2.throttle = 1.0
        sleep(0.02)
    else:
        _rival_perdido_count += 1
        if _rival_perdido_count < MAX_PERDIDO:
            ib.motor_1.throttle = -1.0
            ib.motor_2.throttle = 1.0
            sleep(0.02)
            return

        ib.pixel = (255, 50, 0)     # Naranja rojizo = búsqueda agresiva
        ahora = time.monotonic()
        if ahora - _tiempo_ultimo_cambio > INTERVALO_CAMBIO_GIRO:
            _barridos_sin_rival += 1
            if _barridos_sin_rival % 3 == 0:
                _direccion_giro_busqueda *= -1
            _tiempo_ultimo_cambio = ahora

        ib.motor_1.throttle = -0.9 * _direccion_giro_busqueda
        ib.motor_2.throttle =  0.9 * _direccion_giro_busqueda
        sleep(0.02)


def modo_conservador():
    """Busca despacio, ataca cuando está seguro. Menos riesgo de caerse."""
    global _direccion_giro_busqueda, _tiempo_ultimo_cambio, _barridos_sin_rival, _rival_perdido_count

    if rival_detectado():
        _rival_perdido_count = 0
        ib.pixel = (0, 0, 255)      # Azul = atacando conservador
        ib.motor_1.throttle = -0.85
        ib.motor_2.throttle = 0.85
        sleep(0.02)
    else:
        _rival_perdido_count += 1
        if _rival_perdido_count < MAX_PERDIDO:
            ib.motor_1.throttle = -0.85
            ib.motor_2.throttle = 0.85
            sleep(0.02)
            return

        ib.pixel = (0, 100, 255)    # Azul claro = búsqueda lenta
        ahora = time.monotonic()
        if ahora - _tiempo_ultimo_cambio > 0.35:  # Giro más lento que agresivo
            _barridos_sin_rival += 1
            if _barridos_sin_rival % 2 == 0:
                _direccion_giro_busqueda *= -1
            _tiempo_ultimo_cambio = ahora

        ib.motor_1.throttle = -0.6 * _direccion_giro_busqueda
        ib.motor_2.throttle =  0.6 * _direccion_giro_busqueda
        sleep(0.02)


def modo_emboscada():
    """
    Se queda quieto esperando que el rival se acerque,
    luego carga a máxima velocidad por sorpresa.
    """
    global _rival_perdido_count

    if rival_detectado():
        _rival_perdido_count = 0
        ib.pixel = (128, 0, 128)    # Morado = carga sorpresa
        ib.motor_1.throttle = -1.0
        ib.motor_2.throttle = 1.0
        sleep(0.05)                 # Burst más largo que los otros modos
    else:
        _rival_perdido_count += 1
        if _rival_perdido_count < MAX_PERDIDO:
            ib.motor_1.throttle = -1.0
            ib.motor_2.throttle = 1.0
            sleep(0.02)
            return

        # Sin rival → quieto esperando
        ib.pixel = (20, 0, 20)      # Morado muy oscuro = modo espera
        ib.motor_1.throttle = 0
        ib.motor_2.throttle = 0
        sleep(0.02)


# Mapa de modo → función
EJECUTAR_MODO = {
    "AGRESIVO":    modo_agresivo,
    "CONSERVADOR": modo_conservador,
    "EMBOSCADA":   modo_emboscada,
}


# ============================================================
# FUNCIÓN PARA DETECTAR BOOT DURANTE COMBATE
# ============================================================

def revisar_boton_pausa():
    """
    Llama esto en el loop principal.
    Si detecta que soltaron BOOT → para motores y regresa True
    para que el loop principal salga y vuelva a calibrar.
    """
    event = keys.events.get()
    if event and not event.pressed:
        ib.motor_1.throttle = 0
        ib.motor_2.throttle = 0
        print("BOOT presionado → pausando para nueva ronda")
        return True
    return False


# ============================================================
# EJECUCIÓN PRINCIPAL
# ============================================================

ib.motor_1.throttle = 0
ib.motor_2.throttle = 0

while True:  # Loop externo: una iteración = una ronda completa

    # 1. Seleccionar modo para esta ronda
    modo_ronda = seleccionar_modo()

    # 2. Calibrar sensores
    calibracion_por_pasos()

    # 3. Resetear variables de búsqueda para la ronda nueva
    _rival_perdido_count = 0
    _barridos_sin_rival = 0
    _direccion_giro_busqueda = 1
    _tiempo_ultimo_cambio = time.monotonic()

    funcion_modo = EJECUTAR_MODO[modo_ronda]

    # 4. Loop de combate
    while True:
        # Salir si presionan BOOT durante el combate
        if revisar_boton_pausa():
            break  # Vuelve al loop externo → selección de modo + calibración

        # Prioridad 1: borde
        direccion_impacto = leer_borde_mejorado()
        if direccion_impacto is not None:
            maniobra_escape(direccion_impacto)
        else:
            # Prioridad 2: modo de combate elegido
            funcion_modo()