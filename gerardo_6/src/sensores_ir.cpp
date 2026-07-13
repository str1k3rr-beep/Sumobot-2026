#include <Arduino.h>
#include "config.h"
#include "sensores_ir.h"

int umbrales[4] = {300, 300, 300, 300};

const char* NOMBRES_BORDE[] = {"NINGUNO", "FRENTE", "ATRAS", "IZQUIERDA", "DERECHA", "FRENTE_IZQ", "EMPUJE_IZQUIERDA", "EMPUJE_DERECHA"};

void sensores_ir_inicializar() {
  pinMode(SEN1, INPUT);
  pinMode(SEN2, INPUT);
  pinMode(SEN3, INPUT);
  pinMode(SEN4, INPUT);
}

void leer_sensores(int lecturas[4]) {
  lecturas[0] = analogRead(SEN1);
  lecturas[1] = analogRead(SEN2);
  lecturas[2] = analogRead(SEN3);
  lecturas[3] = analogRead(SEN4);
}

void leer_sensores_bool(bool detectados[4]) {
  int lecturas[4];
  leer_sensores(lecturas);
  for (int i = 0; i < 4; i++) {
    detectados[i] = lecturas[i] < umbrales[i];
  }
}

Borde leer_borde_mejorado() {
  bool d1[4];
  leer_sensores_bool(d1);
  if (!(d1[0] || d1[1] || d1[2] || d1[3])) return BORDE_NINGUNO;

  bool d2[4];
  leer_sensores_bool(d2);

  bool detectados[4];
  for (int i = 0; i < 4; i++) {
    detectados[i] = d1[i] && d2[i];
  }
  if (!(detectados[0] || detectados[1] || detectados[2] || detectados[3])) return BORDE_NINGUNO;

  if (detectados[1] && detectados[3] && !detectados[0] && !detectados[2]) return BORDE_EMPUJE_IZQUIERDA;
  if (detectados[0] && detectados[2] && !detectados[1] && !detectados[3]) return BORDE_EMPUJE_DERECHA;

  if (!detectados[0] && !detectados[1] && (detectados[2] || detectados[3])) return BORDE_ATRAS;

  if (detectados[0] && detectados[1]) return BORDE_FRENTE;
  if (detectados[0] && detectados[2]) return BORDE_IZQUIERDA;
  if (detectados[0] && !detectados[2]) return BORDE_FRENTE_IZQ;
  if (detectados[1] || detectados[3]) return BORDE_DERECHA;
  if (detectados[2]) return BORDE_IZQUIERDA;

  return BORDE_NINGUNO;
}

bool bordeDespejado() {
  return leer_borde_mejorado() == BORDE_NINGUNO;
}

bool bordeDetectado() {
  return leer_borde_mejorado() != BORDE_NINGUNO;
}
