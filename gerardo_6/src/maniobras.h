#pragma once

#include "sensores_ir.h"
#include "imu.h"

void maniobras_inicializar();
bool maniobra_escape(Borde direccion);
bool escapar_levantamiento();
bool reaccionar_impacto(Impacto impacto);
bool escapar_impactos_repetidos();
bool buscar_y_atacar();
void inicio_ronda(int ronda);
void resetear_estado_busqueda();
void resetear_tiempo_borde();
void invertir_direccion_busqueda();
