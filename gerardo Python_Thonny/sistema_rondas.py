# ============================================================
# SISTEMA DE RONDAS — agregar al código base
# ============================================================

# COLORES POR RONDA — agregar junto a las otras constantes globales
COLORES_RONDA = {
    1: (255, 100, 0),   # Naranja = Ronda 1
    2: (0, 255, 100),   # Verde   = Ronda 2
    3: (0, 100, 255),   # Celeste = Ronda 3
}


def inicio_ronda(ronda):
    """Movimiento inicial según la ronda antes de entrar al loop de combate."""

    if ronda == 1:
        # Avance corto directo hacia el rival
        ib.pixel = COLORES_RONDA[1]
        ib.motor_1.throttle = -1.0
        ib.motor_2.throttle = 1.0
        sleep(0.3)

    elif ronda == 2:
        # Giro ~90° a la derecha
        ib.pixel = COLORES_RONDA[2]
        ib.motor_1.throttle =  1.0
        ib.motor_2.throttle =  1.0
        sleep(0.35)  # Ajustar en pruebas hasta que quede exacto en 90°

    elif ronda == 3:
        # Giro ~180° de espaldas al rival
        ib.pixel = COLORES_RONDA[3]
        ib.motor_1.throttle =  1.0
        ib.motor_2.throttle =  1.0
        sleep(0.7)   # Ajustar en pruebas hasta que quede exacto en 180°

    ib.motor_1.throttle = 0
    ib.motor_2.throttle = 0
    sleep(0.05)
    ib.pixel = (0, 0, 0)


# ============================================================
# EJECUCIÓN PRINCIPAL — reemplaza tu bloque actual
# ============================================================

ib.motor_1.throttle = 0
ib.motor_2.throttle = 0

ronda = 1  # Siempre arranca en ronda 1 al encender la batería

while ronda <= 3:

    # Parpadea N veces el color de la ronda para confirmar visualmente
    # 1 parpadeo = ronda 1 / 2 parpadeos = ronda 2 / 3 parpadeos = ronda 3
    print(f"=== RONDA {ronda} ===")
    for _ in range(ronda):
        ib.pixel = COLORES_RONDA[ronda]
        sleep(0.3)
        ib.pixel = (0, 0, 0)
        sleep(0.3)

    # Calibración normal
    calibracion_por_pasos()

    # Movimiento de inicio según la ronda
    inicio_ronda(ronda)

    # Resetear variables de búsqueda para cada ronda nueva
    _rival_perdido_count = 0
    _barridos_sin_rival = 0
    _direccion_giro_busqueda = 1
    _tiempo_ultimo_cambio = time.monotonic()

    # Loop de combate — igual que tu while True original
    while True:

        # BOOT durante combate = termina esta ronda, pasa a la siguiente
        event = keys.events.get()
        if event and event.released:
            ib.motor_1.throttle = 0
            ib.motor_2.throttle = 0
            print(f"Ronda {ronda} terminada.")
            break

        # Tu lógica original sin cambios
        direccion_impacto = leer_borde_mejorado()
        if direccion_impacto is not None:
            maniobra_escape(direccion_impacto)
        else:
            buscar_y_atacar()

    ronda += 1
    sleep(0.5)

# Fin de las 3 rondas
ib.motor_1.throttle = 0
ib.motor_2.throttle = 0
ib.pixel = (255, 255, 255)  # Blanco fijo = partida completa
print("Partida completa.")
