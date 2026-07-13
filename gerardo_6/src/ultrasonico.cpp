#include <Arduino.h>
#include "config.h"
#include "ultrasonico.h"

void ultrasonico_inicializar() {
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  digitalWrite(TRIG_PIN, LOW);
}

long medir_distancia_cm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duracion = pulseIn(ECHO_PIN, HIGH, 8000);
  if (duracion == 0) return 999;

  return duracion * 0.0343 / 2;
}

long medir_distancia_mediana_cm() {
  long d1 = medir_distancia_cm();
  delay(5);
  long d2 = medir_distancia_cm();
  delay(5);
  long d3 = medir_distancia_cm();

  if (d1 > d2) { long t = d1; d1 = d2; d2 = t; }
  if (d2 > d3) { long t = d2; d2 = d3; d3 = t; }
  if (d1 > d2) { long t = d1; d1 = d2; d2 = t; }

  return d2;
}

bool rival_detectado() {
  return medir_distancia_mediana_cm() < DISTANCIA_RIVAL_CM;
}
