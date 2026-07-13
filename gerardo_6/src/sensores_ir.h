#pragma once

enum Borde {
  BORDE_NINGUNO,
  BORDE_FRENTE,
  BORDE_ATRAS,
  BORDE_IZQUIERDA,
  BORDE_DERECHA,
  BORDE_FRENTE_IZQ,
  BORDE_EMPUJE_IZQUIERDA,
  BORDE_EMPUJE_DERECHA
};

extern const char* NOMBRES_BORDE[];

void sensores_ir_inicializar();
void leer_sensores(int lecturas[4]);
Borde leer_borde_mejorado();
bool bordeDespejado();
bool bordeDetectado();
